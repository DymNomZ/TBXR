from __future__ import annotations

"""
Back up the TB-XR database and uploaded media assets.

Run from the backend folder:

    python scripts/backup.py

What this script produces (one timestamped directory per run):

    backups/<timestamp>/
        database.sql        # PostgreSQL plain-SQL dump  (or database.sqlite3 for SQLite)
        media.tar.gz        # archive of MEDIA_ROOT (raw/, xray_processed/, heatmaps/)
        manifest.json       # per-file SHA256 checksums + metadata

The database backend is detected from Django settings the same way the app
does: PostgreSQL when DB_NAME is set, otherwise SQLite.

Options:
    python scripts/backup.py --verify backups/<timestamp>   # verify checksums

Configuration (environment variables):
    BACKUP_DIR               output directory (default: backend/backups/)
    BACKUP_RETENTION_COUNT   keep this many most-recent backups (default: 14; 0 keeps all)
"""

import argparse
import errno
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TBXR.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()

DEFAULT_BACKUP_DIR = BASE_DIR / "backups"
DEFAULT_RETENTION_COUNT = 14
CHUNK_SIZE = 1024 * 64


def get_backup_dir() -> Path:
    return Path(os.environ.get("BACKUP_DIR", str(DEFAULT_BACKUP_DIR)))


def get_retention_count() -> int:
    value = int(os.environ.get("BACKUP_RETENTION_COUNT", str(DEFAULT_RETENTION_COUNT)))
    if value < 0:
        raise ValueError("BACKUP_RETENTION_COUNT must be >= 0.")
    return value


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_backend() -> str:
    engine = settings.DATABASES["default"]["ENGINE"]
    if "postgresql" in engine:
        return "postgresql"
    if engine.endswith("sqlite3"):
        return "sqlite3"
    raise RuntimeError(f"Unsupported database engine: {engine}")


def _pg_env(db_config: dict) -> dict:
    env = os.environ.copy()
    password = db_config.get("PASSWORD") or ""
    if password:
        env["PGPASSWORD"] = password
    else:
        env.pop("PGPASSWORD", None)
    return env


def dump_postgresql(db_config: dict, destination: Path) -> None:
    name = db_config.get("NAME") or ""
    if not name:
        raise RuntimeError("PostgreSQL backup requires DB_NAME to be set.")

    command = ["pg_dump", "--clean", "--if-exists", "--no-owner", "--no-privileges", "--format=plain"]
    host = db_config.get("HOST") or ""
    if host:
        command += ["--host", host]
    port = db_config.get("PORT") or ""
    if port:
        command += ["--port", str(port)]
    username = db_config.get("USER") or ""
    if username:
        command += ["--username", username]
    command += ["--file", str(destination), name]

    result = subprocess.run(
        command,
        env=_pg_env(db_config),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "pg_dump failed: " + (result.stderr or result.stdout).strip()
        )


def dump_sqlite3(db_config: dict, destination: Path) -> None:
    source_path = Path(db_config["NAME"])
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {source_path}")
    source = sqlite3.connect(str(source_path))
    target = sqlite3.connect(str(destination))
    try:
        with target:
            source.backup(target)
    finally:
        target.close()
        source.close()


def archive_media(media_root: Path, destination_base: Path) -> Path:
    media_root.mkdir(parents=True, exist_ok=True)
    return Path(
        shutil.make_archive(
            str(destination_base),
            "gztar",
            root_dir=str(media_root),
        )
    )


def write_manifest(backup_dir: Path, metadata: dict) -> Path:
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return manifest_path


def _rename_into_place(staging: Path, backup_root: Path, timestamp: str) -> Path:
    """Atomically publish a fully-built backup dir under a unique timestamped name.

    ``os.rename`` replaces an existing *empty* directory on POSIX but fails with
    EEXIST/ENOTEMPTY on Windows. We rely on that failure to advance the
    zero-padded suffix, so two concurrent runs can never claim (or overwrite) the
    same name. A zero-padded suffix disambiguates multiple runs in the same
    second and keeps lexicographic order chronological.
    """
    counter = 0
    while True:
        suffix = f"-{counter:02d}" if counter else ""
        candidate = backup_root / f"{timestamp}{suffix}"
        try:
            os.rename(staging, candidate)
            return candidate
        except OSError as exc:
            if exc.errno in (errno.EEXIST, errno.ENOTEMPTY):
                counter += 1
                continue
            raise


def _reject_overlapping_backup_media(backup_root: Path, media_root: Path) -> None:
    """Refuse a configuration where the backup output nests inside the media tree
    (or vice versa).

    If BACKUP_DIR lives under MEDIA_ROOT, the media archive would include its own
    output, and a media restore that replaces MEDIA_ROOT would delete the backups.
    The reverse nesting is rejected for the same reason.
    """
    backup_root = backup_root.resolve()
    media_root = media_root.resolve()
    if backup_root.is_relative_to(media_root) or media_root.is_relative_to(backup_root):
        raise RuntimeError(
            "BACKUP_DIR and MEDIA_ROOT must be disjoint so a backup never archives "
            "its own output or is removed by a media restore. "
            f"BACKUP_DIR={backup_root}, MEDIA_ROOT={media_root}"
        )


def create_backup(timestamp: str | None = None) -> dict:
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    backup_root = get_backup_dir()
    _reject_overlapping_backup_media(backup_root, Path(settings.MEDIA_ROOT))
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_root.chmod(0o700)

    # Build the whole backup in a hidden temp directory, then rename it into
    # place atomically. A failed run therefore never leaves a half-written
    # backup directory visible to list_backup_dirs or restore.
    staging = Path(tempfile.mkdtemp(prefix=f".{timestamp}.tmp-", dir=str(backup_root)))
    staging.chmod(0o700)

    try:
        db_config = settings.DATABASES["default"]
        backend = database_backend()

        if backend == "postgresql":
            database_filename = "database.sql"
            dump_postgresql(db_config, staging / database_filename)
        else:
            database_filename = "database.sqlite3"
            dump_sqlite3(db_config, staging / database_filename)

        media_archive = archive_media(
            Path(settings.MEDIA_ROOT),
            staging / "media",
        )

        files = {
            database_filename: (staging / database_filename),
            media_archive.name: media_archive,
        }
        for path in files.values():
            path.chmod(0o600)
        manifest = {
            "created_at": timestamp,
            "database_backend": backend,
            "database_file": database_filename,
            "media_file": media_archive.name,
            "media_root": str(settings.MEDIA_ROOT),
            "files": {
                name: {
                    "sha256": sha256_of(path),
                    "size": path.stat().st_size,
                }
                for name, path in files.items()
            },
        }
        manifest_path = write_manifest(staging, manifest)
        manifest_path.chmod(0o600)

        final_dir = _rename_into_place(staging, backup_root, timestamp)
        staging = None
    except Exception:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        raise

    return {
        "backup_dir": final_dir,
        "manifest_path": final_dir / "manifest.json",
        "files": [str(final_dir / manifest["database_file"]), str(final_dir / manifest["media_file"])],
    }


def _is_backup_dir(path: Path) -> bool:
    return path.is_dir() and (path / "manifest.json").is_file()


def list_backup_dirs(backup_root: Path) -> list[Path]:
    if not backup_root.exists():
        return []
    return sorted(
        (path for path in backup_root.iterdir()
         if not path.name.startswith(".") and _is_backup_dir(path)),
        key=lambda path: path.name,
    )


def prune_backups(backup_root: Path, keep: int) -> list[Path]:
    if keep <= 0:
        # 0 (or less) disables pruning; keep every backup.
        return []
    removed = []
    for stale in list_backup_dirs(backup_root)[:-keep]:
        try:
            shutil.rmtree(stale)
        except FileNotFoundError:
            # A concurrent backup run already pruned this directory.
            continue
        removed.append(stale)
    return removed


def resolve_backup_file(backup_dir: Path, name: str) -> Path:
    """Resolve a manifest file name, refusing paths outside the backup dir."""
    base = backup_dir.resolve()
    candidate = (backup_dir / name).resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError(f"Unsafe backup file path: {name!r}")
    return candidate


def verify_backup(backup_dir: Path, files: list[str] | None = None) -> dict:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest.json in {backup_dir}")

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest is not valid JSON: {manifest_path} ({exc})")
    if not isinstance(manifest, dict):
        raise ValueError(f"Manifest is not a JSON object: {manifest_path}")

    files_meta = manifest.get("files")
    if not isinstance(files_meta, dict) or not files_meta:
        raise ValueError(f"No files listed in {manifest_path}")

    if files is None:
        # Verifying the whole backup: every file listed in the manifest must be
        # present, and the declared database/media restore targets must exist so
        # a truncated manifest can't pass as a complete backup.
        names = list(files_meta)
        for required in (manifest.get("database_file"), manifest.get("media_file")):
            if not required or required not in files_meta:
                raise ValueError(
                    f"Manifest is missing its declared restore target: {required!r}"
                )
    else:
        names = list(files)
        for name in names:
            if name not in files_meta:
                raise ValueError(f"File not listed in manifest: {name!r}")

    results = {}
    ok = True
    for name in names:
        meta = files_meta.get(name)
        if not isinstance(meta, dict):
            results[name] = {"ok": False, "error": "invalid metadata"}
            ok = False
            continue
        try:
            path = resolve_backup_file(backup_dir, name)
        except ValueError as exc:
            results[name] = {"ok": False, "error": str(exc)}
            ok = False
            continue
        if not path.exists():
            results[name] = {"ok": False, "error": "missing"}
            ok = False
            continue
        expected = meta.get("sha256")
        if not isinstance(expected, str):
            results[name] = {"ok": False, "error": "missing checksum"}
            ok = False
            continue
        actual = sha256_of(path)
        results[name] = {"ok": actual == expected, "sha256": actual, "expected": expected}
        ok = ok and actual == expected

    return {"ok": ok, "files": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up the TB-XR database and media.")
    parser.add_argument(
        "--verify",
        metavar="BACKUP_DIR",
        help="Verify the integrity of an existing backup instead of creating one.",
    )
    args = parser.parse_args()

    if args.verify:
        backup_dir = Path(args.verify)
        try:
            result = verify_backup(backup_dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[FAIL] {exc}")
            return 1

        if result["ok"]:
            print(f"[PASS] All files in {backup_dir} match their checksums.")
            return 0

        print(f"[FAIL] Integrity check failed for {backup_dir}:")
        for name, detail in result["files"].items():
            status = detail.get("error") or ("OK" if detail["ok"] else "MISMATCH")
            print(f"- {name}: {status}")
        return 1

    backup_root = get_backup_dir()

    try:
        result = create_backup()
    except Exception as exc:
        print(f"[FAIL] Backup failed: {exc}")
        return 1
    backup_dir = result["backup_dir"]
    print(f"Created backup: {backup_dir}")
    print(f"- Database ({settings.DATABASES['default']['ENGINE']})")
    for path in result["files"]:
        print(f"  - {path}")

    keep = get_retention_count()
    removed = prune_backups(backup_root, keep)
    if removed:
        print(f"Pruned {len(removed)} old backup(s) (retention={keep}):")
        for stale in removed:
            print(f"- {stale.name}")
    else:
        print(f"Retention check: keeping up to {keep} backups; nothing to prune.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

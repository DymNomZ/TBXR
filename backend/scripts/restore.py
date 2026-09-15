from __future__ import annotations

"""
Restore the TB-XR database and uploaded media from a backup.

Run from the backend folder:

    python scripts/restore.py                     # dry-run of the latest backup
    python scripts/restore.py <backup-dir>        # dry-run of a specific backup
    python scripts/restore.py --apply             # actually restore the latest backup

The script verifies checksums before touching anything and defaults to a
dry-run so a mistake cannot silently overwrite data. Restore is destructive:
stop the application server before applying, and keep a fresh backup.

Options:
    --apply          actually perform the restore (default is dry-run)
    --database-only  restore the database, skip media
    --media-only     restore media, skip the database
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TBXR.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from scripts.backup import database_backend, get_backup_dir, resolve_backup_file, verify_backup


def resolve_backup_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)

    backup_root = get_backup_dir()
    if not backup_root.exists():
        raise SystemExit(f"No backups found under {backup_root}.")
    dirs = sorted(
        (path for path in backup_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )
    if not dirs:
        raise SystemExit(f"No backups found under {backup_root}.")
    return dirs[-1]


def load_manifest(backup_dir: Path) -> dict:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest.json in {backup_dir}.")
    return json.loads(manifest_path.read_text())


def _pg_env(db_config: dict) -> dict:
    env = os.environ.copy()
    password = db_config.get("PASSWORD") or ""
    if password:
        env["PGPASSWORD"] = password
    else:
        env.pop("PGPASSWORD", None)
    return env


def restore_postgresql(db_config: dict, dump_path: Path) -> None:
    name = db_config.get("NAME") or ""
    if not name:
        raise SystemExit("PostgreSQL restore requires DB_NAME to be set.")

    command = ["psql", "--set", "ON_ERROR_STOP=1", "--single-transaction"]
    host = db_config.get("HOST") or ""
    if host:
        command += ["--host", host]
    port = db_config.get("PORT") or ""
    if port:
        command += ["--port", str(port)]
    username = db_config.get("USER") or ""
    if username:
        command += ["--username", username]
    command += ["--dbname", name, "--file", str(dump_path)]

    result = subprocess.run(
        command,
        env=_pg_env(db_config),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "psql restore failed: " + (result.stderr or result.stdout).strip()
        )


def restore_sqlite3(db_config: dict, dump_path: Path) -> None:
    live_path = Path(db_config["NAME"])
    live_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = live_path.with_name(live_path.name + ".restore-tmp")
    try:
        shutil.copy2(str(dump_path), str(temp_path))
        os.replace(str(temp_path), str(live_path))
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def stage_media(archive_path: Path, staging_parent: Path) -> Path:
    """Validate a media archive and extract it into a fresh temp directory.

    Extracting into a staging directory first means an unsafe or corrupt
    archive fails before the live database or media is touched.
    """
    staging = Path(tempfile.mkdtemp(prefix=".tbxr-restore-", dir=str(staging_parent)))
    try:
        with tarfile.open(str(archive_path), "r:gz") as tar:
            for member in tar.getmembers():
                if (
                    member.issym()
                    or member.islnk()
                    or member.name.startswith("/")
                    or Path(member.name).is_absolute()
                    or ".." in Path(member.name).parts
                    or not (member.isfile() or member.isdir())
                ):
                    raise RuntimeError(f"Unsafe entry in media archive: {member.name!r}")
            try:
                tar.extractall(str(staging), filter="data")
            except TypeError:
                # Python < 3.11.4 has no filter kwarg; the member check above is the guard.
                tar.extractall(str(staging))
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return staging


def replace_media_tree(staging: Path, media_root: Path) -> None:
    """Swap the staged media into place, replacing the live tree atomically.

    The live ``MEDIA_ROOT`` is renamed aside first, the staging directory is
    renamed to ``MEDIA_ROOT``, and only then is the old tree removed. This means
    restored media replaces (rather than merges with) whatever was there before,
    and a failure mid-swap can restore the previous tree rather than leaving the
    media directory missing.
    """
    parent = media_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    old = Path(tempfile.mkdtemp(prefix=".tbxr-media-old-", dir=str(parent)))
    os.rmdir(old)
    if media_root.exists():
        os.rename(media_root, old)
    try:
        os.rename(staging, media_root)
    except Exception:
        if not media_root.exists() and old.exists():
            os.rename(old, media_root)
        raise
    else:
        if old.is_dir() and not old.is_symlink():
            shutil.rmtree(old, ignore_errors=True)
        else:
            old.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the TB-XR database and media.")
    parser.add_argument("backup_dir", nargs="?", default=None)
    parser.add_argument("--apply", action="store_true", help="Actually restore (default is dry-run).")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--database-only", action="store_true", help="Restore only the database.")
    scope.add_argument("--media-only", action="store_true", help="Restore only media assets.")
    args = parser.parse_args()

    backup_dir = resolve_backup_dir(args.backup_dir)
    manifest = load_manifest(backup_dir)
    restore_db = not args.media_only
    restore_assets = not args.database_only

    # Verify only the components this run will actually restore, so a corrupt
    # media archive does not block a --database-only restore (and vice versa).
    verify_files = []
    if restore_db:
        verify_files.append(manifest["database_file"])
    if restore_assets:
        verify_files.append(manifest["media_file"])

    try:
        verification = verify_backup(backup_dir, files=verify_files)
        dump_path = resolve_backup_file(backup_dir, manifest["database_file"]) if restore_db else None
        media_path = resolve_backup_file(backup_dir, manifest["media_file"]) if restore_assets else None
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    if not verification["ok"]:
        print(f"[FAIL] Integrity check failed for {backup_dir}; refusing to restore.")
        for name, detail in verification["files"].items():
            status = detail.get("error") or ("OK" if detail["ok"] else "MISMATCH")
            print(f"- {name}: {status}")
        return 1

    backend = manifest["database_backend"]
    current_backend = database_backend()
    if restore_db and backend != current_backend:
        print(
            f"[FAIL] Backup was created for '{backend}' but the active database is "
            f"'{current_backend}'. Refusing to restore across database backends."
        )
        return 1

    print(f"[{'APPLY' if args.apply else 'DRY-RUN'}] Restoring from {backup_dir}")
    print(f"- Database ({backend}): {manifest['database_file']} -> {'restore' if restore_db else 'skip'}")
    print(f"- Media: {manifest['media_file']} -> {'restore' if restore_assets else 'skip'} (MEDIA_ROOT={settings.MEDIA_ROOT})")

    if not args.apply:
        print("Dry-run complete. Re-run with --apply to perform the restore.")
        return 0

    media_root = Path(settings.MEDIA_ROOT)
    staging = None
    try:
        if restore_assets:
            # Validate and stage media before touching the database so a bad
            # archive cannot leave the live database restored over a failed
            # media restore.
            staging = stage_media(media_path, media_root.parent)

        if restore_db:
            db_config = settings.DATABASES["default"]
            if backend == "postgresql":
                restore_postgresql(db_config, dump_path)
            elif backend == "sqlite3":
                restore_sqlite3(db_config, dump_path)
            else:
                raise SystemExit(f"Unsupported database backend in manifest: {backend}")

        if restore_assets:
            replace_media_tree(staging, media_root)
            staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)

    print("Restore complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

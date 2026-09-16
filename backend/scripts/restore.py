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

A full restore is not atomic across the database and media: the database is
restored first, then media is swapped into place. If the media swap fails after
the database has been restored, the database is restored but media may remain
unchanged. Re-run the media restore (or use --media-only) to retry.

Options:
    --apply          actually perform the restore (default is dry-run)
    --database-only  restore the database, skip media
    --media-only     restore media, skip the database
"""

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TBXR.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from scripts import backup_lock

from scripts.backup import (
    database_backend,
    get_backup_dir,
    list_backup_dirs,
    resolve_backup_file,
    verify_backup,
)

RESTORE_STAGING_MAX_AGE_SECONDS = 24 * 60 * 60


def resolve_backup_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)

    backup_root = get_backup_dir()
    dirs = list_backup_dirs(backup_root)
    if not dirs:
        raise SystemExit(f"No backups found under {backup_root}.")
    return dirs[-1]


def load_manifest(backup_dir: Path) -> dict:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest.json in {backup_dir}.")
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest is not valid JSON: {manifest_path} ({exc})")
    if not isinstance(manifest, dict):
        raise SystemExit(f"Manifest is not a JSON object: {manifest_path}")
    return manifest


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

    command = ["psql", "--no-password", "--set", "ON_ERROR_STOP=1", "--single-transaction"]
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

    token = secrets.token_hex(8)
    temp_path = live_path.with_name(f"{live_path.name}.restore-tmp-{token}")
    old_path = live_path.with_name(f"{live_path.name}.restore-old-{token}")

    # A crashed restore can leave a parked database or sidecars behind under
    # fixed names. Refuse to run if any such leftover state exists so we never
    # guess which file is the live database; the operator must resolve it first.
    stale = []
    for pattern in ("restore-tmp-", "restore-old-"):
        stale.extend(live_path.parent.glob(f"{live_path.name}*{pattern}*"))
    if stale:
        names = ", ".join(sorted(p.name for p in stale))
        raise RuntimeError(
            f"Stale restore files present for {live_path.name}; resolve them "
            f"before restoring: {names}"
        )

    moved = []  # (original, parked) pairs, for rollback and cleanup
    if live_path.exists():
        owner_stat = live_path.stat()
    else:
        owner_stat = live_path.parent.stat()

    try:
        shutil.copy2(str(dump_path), str(temp_path))
        # Park the live database and its WAL/rollback sidecars aside rather than
        # deleting them up front, so a failure mid-swap can put them back instead
        # of leaving the database missing or its journal state lost.
        if live_path.exists():
            # Preserve the live database's permissions on the replacement so the
            # restored file stays writable by whatever account owns it.
            shutil.copymode(str(live_path), str(temp_path))
            moved.append((live_path, old_path))
            os.replace(str(live_path), str(old_path))
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = live_path.with_name(live_path.name + suffix)
            if sidecar.exists():
                parked = sidecar.with_name(f"{sidecar.name}.restore-old-{token}")
                os.replace(str(sidecar), str(parked))
                moved.append((sidecar, parked))
        os.chown(str(temp_path), owner_stat.st_uid, owner_stat.st_gid)
        os.replace(str(temp_path), str(live_path))
    except Exception:
        temp_path.unlink(missing_ok=True)
        for original, parked in reversed(moved):
            if not original.exists() and parked.exists():
                os.replace(str(parked), str(original))
        raise
    else:
        for _, parked in moved:
            parked.unlink(missing_ok=True)


def _unsafe_archive_member(member: tarfile.TarInfo) -> bool:
    """Return True if a tar member could escape the staging directory or is unsafe.

    The pre-extraction check is a defense-in-depth layer on top of Python's
    ``filter="data"``. It rejects links, non-regular/non-directory entries, and
    names that are absolute, contain ``..``, use backslash separators, or are
    drive-rooted (e.g. ``C:\\evil``) so Windows-style traversal cannot slip past
    a POSIX ``PurePosixPath`` check.
    """
    if member.issym() or member.islnk():
        return True
    if not (member.isfile() or member.isdir()):
        return True
    name = member.name
    posix = PurePosixPath(name)
    if posix.is_absolute() or ".." in posix.parts:
        return True
    if "\\" in name:
        return True
    if len(name) >= 2 and name[1] == ":" and name[0].isalpha():
        return True
    return False


def stage_media(archive_path: Path, staging_parent: Path) -> Path:
    """Validate a media archive and extract it into a fresh temp directory.

    Extracting into a staging directory first means an unsafe or corrupt
    archive fails before the live database or media is touched.
    """
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".tbxr-restore-", dir=str(staging_parent)))
    try:
        with tarfile.open(str(archive_path), "r:gz") as tar:
            for member in tar.getmembers():
                if _unsafe_archive_member(member):
                    raise RuntimeError(f"Unsafe entry in media archive: {member.name!r}")
            try:
                tar.extractall(str(staging), filter="data")
            except TypeError as exc:
                # `filter="data"` is the only safe extraction mode; a TypeError
                # means the interpreter predates Python 3.11.4 and cannot safely
                # sanitize modes/ownership. Refuse rather than fall back to an
                # unfiltered extraction.
                raise RuntimeError(
                    "Media extraction requires Python 3.11.4+ for safe tar filtering."
                ) from exc
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return staging


def cleanup_stale_restore_staging(staging_parent: Path) -> list[Path]:
    if not staging_parent.exists():
        return []

    cutoff = time.time() - RESTORE_STAGING_MAX_AGE_SECONDS
    removed = []
    for path in staging_parent.iterdir():
        if not (path.name.startswith(".tbxr-restore-") and path.is_dir()):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff:
            continue
        try:
            shutil.rmtree(path)
        except OSError:
            continue
        removed.append(path)
    return removed


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
    old_mode = None
    owner_stat = None
    if media_root.is_dir() and not media_root.is_symlink():
        owner_stat = media_root.stat()
        old_mode = owner_stat.st_mode
    if media_root.exists():
        os.rename(media_root, old)
    try:
        os.rename(staging, media_root)
    except Exception:
        if not media_root.exists() and old.exists():
            os.rename(old, media_root)
        raise
    else:
        # mkdtemp creates the staging tree 0700; preserve the previous
        # MEDIA_ROOT permissions so the restored tree stays accessible to
        # whatever account the web server runs as.
        if owner_stat is not None:
            for root, dirs, files in os.walk(media_root):
                os.chown(root, owner_stat.st_uid, owner_stat.st_gid)
                for name in dirs:
                    os.chown(os.path.join(root, name), owner_stat.st_uid, owner_stat.st_gid)
                for name in files:
                    os.chown(os.path.join(root, name), owner_stat.st_uid, owner_stat.st_gid)
        else:
            parent_stat = parent.stat()
            os.chown(media_root, parent_stat.st_uid, parent_stat.st_gid)
            os.chmod(media_root, 0o755)
        if old_mode is not None:
            os.chmod(media_root, old_mode)
        if old.is_dir() and not old.is_symlink():
            shutil.rmtree(old)
        else:
            old.unlink(missing_ok=True)


def _paths_overlap(a: Path, b: Path) -> bool:
    """Return True if either path contains the other (after resolving symlinks)."""
    a = a.resolve()
    b = b.resolve()
    return a.is_relative_to(b) or b.is_relative_to(a)


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

    database_file = manifest.get("database_file")
    media_file = manifest.get("media_file")
    backend = manifest.get("database_backend")
    if restore_db and not isinstance(backend, str):
        print(f"[FAIL] Manifest in {backup_dir} has an invalid 'database_backend'.")
        return 1
    if restore_db and not isinstance(database_file, str):
        print(f"[FAIL] Manifest in {backup_dir} has an invalid 'database_file'.")
        return 1
    if restore_assets and not isinstance(media_file, str):
        print(f"[FAIL] Manifest in {backup_dir} has an invalid 'media_file'.")
        return 1

    # Bind each restore target to the backend that produced it. Without this, a
    # tampered manifest could name the media archive as the database file (or
    # vice versa) and cause the wrong artifact to be installed.
    if restore_db:
        expected_database_file = {
            "postgresql": "database.sql",
            "sqlite3": "database.sqlite3",
        }.get(backend)
        if database_file != expected_database_file:
            print(
                f"[FAIL] Manifest in {backup_dir} declares database_file "
                f"{database_file!r}, inconsistent with backend {backend!r}."
            )
            return 1
    if restore_assets and media_file != "media.tar.gz":
        print(
            f"[FAIL] Manifest in {backup_dir} declares media_file "
            f"{media_file!r}, expected 'media.tar.gz'."
        )
        return 1

    # Verify only the components this run will actually restore, so a corrupt
    # media archive does not block a --database-only restore (and vice versa).
    verify_files = []
    if restore_db:
        verify_files.append(database_file)
    if restore_assets:
        verify_files.append(media_file)

    try:
        verification = verify_backup(backup_dir, files=verify_files)
        dump_path = resolve_backup_file(backup_dir, database_file) if restore_db else None
        media_path = resolve_backup_file(backup_dir, media_file) if restore_assets else None
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    if not verification["ok"]:
        print(f"[FAIL] Integrity check failed for {backup_dir}; refusing to restore.")
        for name, detail in verification["files"].items():
            status = detail.get("error") or ("OK" if detail["ok"] else "MISMATCH")
            print(f"- {name}: {status}")
        return 1

    current_backend = database_backend()
    if restore_db and backend != current_backend:
        print(
            f"[FAIL] Backup was created for '{backend}' but the active database is "
            f"'{current_backend}'. Refusing to restore across database backends."
        )
        return 1

    print(f"[{'APPLY' if args.apply else 'DRY-RUN'}] Restoring from {backup_dir}")
    print(f"- Database ({backend}): {database_file} -> {'restore' if restore_db else 'skip'}")
    print(f"- Media: {media_file} -> {'restore' if restore_assets else 'skip'} (MEDIA_ROOT={settings.MEDIA_ROOT})")

    if not args.apply:
        print("Dry-run complete. Re-run with --apply to perform the restore.")
        return 0

    media_root = Path(settings.MEDIA_ROOT)
    if restore_assets and _paths_overlap(backup_dir, media_root):
        print(
            f"[FAIL] The backup directory {backup_dir} and MEDIA_ROOT {media_root} "
            "must be disjoint, otherwise a media restore would delete the very "
            "backup it is restoring from."
        )
        return 1

    backup_root = get_backup_dir()
    staging = None
    with backup_lock.backup_operation_lock(backup_root):
        if restore_assets:
            cleanup_stale_restore_staging(media_root.parent)
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
                    raise RuntimeError(f"Unsupported database backend in manifest: {backend}")

            if restore_assets:
                replace_media_tree(staging, media_root)
                staging = None
        except Exception as exc:
            print(f"[FAIL] Restore failed: {exc}")
            return 1
        finally:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)

    print("Restore complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

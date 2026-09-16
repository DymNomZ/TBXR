from __future__ import annotations

import contextlib
import os
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

LOCK_FILENAME = ".tbxr-backup.lock"


@contextlib.contextmanager
def backup_operation_lock(backup_root: Path):
    """
    Acquire an exclusive advisory lock on the backup directory.
    Blocks if another backup or restore operation is in progress.
    """
    if fcntl is None:
        raise RuntimeError("backup_operation_lock requires a POSIX environment supporting fcntl.")

    backup_root = Path(backup_root)
backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
backup_root.chmod(0o700)
    lock_path = backup_root / LOCK_FILENAME

    is_new = not lock_path.exists()
    with open(lock_path, "a+") as lock_file:
        if is_new:
            try:
                root_stat = backup_root.stat()
                os.chown(lock_path, root_stat.st_uid, root_stat.st_gid)
            except (OSError, AttributeError):
                pass
            try:
                lock_path.chmod(0o660)
            except OSError:
                pass

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
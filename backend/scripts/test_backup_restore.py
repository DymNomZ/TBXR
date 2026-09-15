"""Tests for the backup and restore scripts.

These tests exercise the SQLite path (the CI database backend) and the
media-archive validation / atomic-swap logic. PostgreSQL-specific code paths
are guarded by subprocess calls and are not covered here because CI has no
PostgreSQL server.
"""

import io
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase, override_settings

from scripts import backup, restore


def _make_sqlite_db(path, rows=("hello",)):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    for row in rows:
        conn.execute("INSERT INTO t (v) VALUES (?)", (row,))
    conn.commit()
    conn.close()


def _read_rows(path):
    conn = sqlite3.connect(str(path))
    rows = [row[0] for row in conn.execute("SELECT v FROM t ORDER BY id")]
    conn.close()
    return rows


def _overwrite_sqlite(path):
    conn = sqlite3.connect(str(path))
    conn.execute("DELETE FROM t")
    conn.commit()
    conn.close()


def _tar_with_regular_file(path, name, data):
    with tarfile.open(str(path), "w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


@contextmanager
def _override_db_settings(media_root, db_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with override_settings(
            MEDIA_ROOT=str(media_root),
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": str(db_path),
                }
            },
        ):
            yield


class BackupScriptTests(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.backup_root = self.tmp / "backups"
        self.backup_root.mkdir()
        self.media_root = self.tmp / "media"
        self.media_root.mkdir()
        self.db_path = self.tmp / "db.sqlite3"
        _make_sqlite_db(self.db_path)

    def _settings(self):
        return _override_db_settings(self.media_root, self.db_path)

    def _create_backup(self, timestamp="2026-01-01T000000Z"):
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                return backup.create_backup(timestamp=timestamp)

    def test_create_backup_produces_manifest_and_verifiable_files(self):
        (self.media_root / "raw").mkdir()
        (self.media_root / "raw" / "img.png").write_bytes(b"png-bytes")

        result = self._create_backup()

        backup_dir = result["backup_dir"]
        self.assertTrue((backup_dir / "database.sqlite3").exists())
        self.assertTrue((backup_dir / "media.tar.gz").exists())
        self.assertTrue((backup_dir / "manifest.json").exists())
        self.assertEqual(backup_dir.name, "2026-01-01T000000Z")

        verification = backup.verify_backup(backup_dir)
        self.assertTrue(verification["ok"])
        self.assertEqual(set(verification["files"]), {"database.sqlite3", "media.tar.gz"})

    def test_create_backup_removes_staging_on_failure(self):
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                with mock.patch.object(backup, "dump_sqlite3", side_effect=RuntimeError("boom")):
                    with self.assertRaises(RuntimeError):
                        backup.create_backup(timestamp="2026-01-01T000000Z")

        self.assertEqual(list(self.backup_root.iterdir()), [])
        self.assertEqual(backup.list_backup_dirs(self.backup_root), [])

    def test_list_backup_dirs_skips_hidden_temp_dirs(self):
        (self.backup_root / "2026-01-01T000000Z").mkdir()
        (self.backup_root / ".2026-01-02T000000Z.tmp-abc").mkdir()
        (self.backup_root / "notes.txt").write_text("x")

        self.assertEqual(
            [p.name for p in backup.list_backup_dirs(self.backup_root)],
            ["2026-01-01T000000Z"],
        )

    def test_rename_into_place_disambiguates_with_zero_padded_suffix(self):
        first = self.backup_root / "2026-01-01T000000Z"
        first.mkdir()
        second_staging = self.backup_root / ".staging2"
        second_staging.mkdir()

        second = backup._rename_into_place(second_staging, self.backup_root, "2026-01-01T000000Z")
        self.assertEqual(second.name, "2026-01-01T000000Z-01")

        third_staging = self.backup_root / ".staging3"
        third_staging.mkdir()
        third = backup._rename_into_place(third_staging, self.backup_root, "2026-01-01T000000Z")
        self.assertEqual(third.name, "2026-01-01T000000Z-02")

    def test_prune_backups_keeps_most_recent(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z", "2026-01-03T000000Z"):
            (self.backup_root / name).mkdir()

        removed = backup.prune_backups(self.backup_root, keep=2)

        self.assertEqual([p.name for p in removed], ["2026-01-01T000000Z"])
        self.assertEqual(
            [p.name for p in backup.list_backup_dirs(self.backup_root)],
            ["2026-01-02T000000Z", "2026-01-03T000000Z"],
        )

    def test_prune_backups_keep_zero_disables_pruning(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z"):
            (self.backup_root / name).mkdir()

        removed = backup.prune_backups(self.backup_root, keep=0)

        self.assertEqual(removed, [])
        self.assertEqual(len(backup.list_backup_dirs(self.backup_root)), 2)

    def test_verify_backup_requires_declared_restore_targets(self):
        result = self._create_backup()
        backup_dir = result["backup_dir"]
        manifest_path = backup_dir / "manifest.json"

        manifest = json.loads(manifest_path.read_text())
        manifest.pop("database_file")
        manifest_path.write_text(json.dumps(manifest))

        with self.assertRaises(ValueError):
            backup.verify_backup(backup_dir)

    def test_verify_backup_detects_tampering(self):
        result = self._create_backup()
        backup_dir = result["backup_dir"]
        with (backup_dir / "database.sqlite3").open("ab") as handle:
            handle.write(b"tampered")

        verification = backup.verify_backup(backup_dir)

        self.assertFalse(verification["ok"])
        self.assertFalse(verification["files"]["database.sqlite3"]["ok"])

    def test_verify_backup_scoped_files(self):
        result = self._create_backup()
        backup_dir = result["backup_dir"]
        with (backup_dir / "media.tar.gz").open("ab") as handle:
            handle.write(b"tampered")

        db_only = backup.verify_backup(backup_dir, files=["database.sqlite3"])
        media_only = backup.verify_backup(backup_dir, files=["media.tar.gz"])

        self.assertTrue(db_only["ok"])
        self.assertFalse(media_only["ok"])

        with self.assertRaises(ValueError):
            backup.verify_backup(backup_dir, files=["not-in-manifest"])

    def test_resolve_backup_file_rejects_traversal(self):
        backup_dir = self.backup_root / "2026-01-01T000000Z"
        backup_dir.mkdir()

        with self.assertRaises(ValueError):
            backup.resolve_backup_file(backup_dir, "../outside")


class RestoreScriptTests(SimpleTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.media_root = self.tmp / "media"
        self.media_root.mkdir()
        self.db_path = self.tmp / "db.sqlite3"
        _make_sqlite_db(self.db_path, rows=("live",))

    def _settings(self):
        return _override_db_settings(self.media_root, self.db_path)

    def test_stage_media_rejects_symlink(self):
        archive = self.tmp / "symlink.tar.gz"
        with tarfile.open(str(archive), "w:gz") as tar:
            info = tarfile.TarInfo("link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)

        with self.assertRaises(RuntimeError):
            restore.stage_media(archive, self.tmp)

    def test_stage_media_rejects_absolute_and_parent_paths(self):
        for name in ("/etc/evil", "../evil"):
            archive = self.tmp / f"unsafe-{name.replace('/', '_')}.tar.gz"
            with tarfile.open(str(archive), "w:gz") as tar:
                info = tarfile.TarInfo(name)
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))

            with self.subTest(name=name):
                with self.assertRaises(RuntimeError):
                    restore.stage_media(archive, self.tmp)

    def test_stage_media_rejects_non_regular_member(self):
        archive = self.tmp / "fifo.tar.gz"
        with tarfile.open(str(archive), "w:gz") as tar:
            info = tarfile.TarInfo("fifo")
            info.type = tarfile.FIFOTYPE
            tar.addfile(info)

        with self.assertRaises(RuntimeError):
            restore.stage_media(archive, self.tmp)

    def test_stage_media_extracts_clean_archive(self):
        archive = self.tmp / "clean.tar.gz"
        _tar_with_regular_file(archive, "raw/img.png", b"png-bytes")

        staging = restore.stage_media(archive, self.tmp)

        self.assertTrue(staging.is_dir())
        self.assertEqual((staging / "raw" / "img.png").read_bytes(), b"png-bytes")
        shutil.rmtree(staging, ignore_errors=True)

    def test_replace_media_tree_replaces_not_merges(self):
        (self.media_root / "old.txt").write_text("old")
        staging = self.tmp / "staging"
        staging.mkdir()
        (staging / "new.txt").write_text("new")

        restore.replace_media_tree(staging, self.media_root)

        self.assertEqual(set(p.name for p in self.media_root.iterdir()), {"new.txt"})
        self.assertFalse(staging.exists())

    def test_replace_media_tree_rolls_back_on_failure(self):
        (self.media_root / "old.txt").write_text("old")
        staging = self.tmp / "staging"
        staging.mkdir()
        (staging / "new.txt").write_text("new")

        real_rename = os.rename
        calls = []

        def fake_rename(src, dst):
            calls.append((src, dst))
            if len(calls) == 2:
                raise OSError("simulated failure")
            return real_rename(src, dst)

        with mock.patch.object(os, "rename", side_effect=fake_rename):
            with self.assertRaises(OSError):
                restore.replace_media_tree(staging, self.media_root)

        self.assertTrue(self.media_root.exists())
        self.assertEqual(set(p.name for p in self.media_root.iterdir()), {"old.txt"})
        self.assertTrue(staging.exists())

    def test_restore_sqlite3_replaces_live_db(self):
        dump_path = self.tmp / "dump.sqlite3"
        _make_sqlite_db(dump_path, rows=("restored",))

        with self._settings():
            restore.restore_sqlite3(settings_db_config(), dump_path)

        self.assertEqual(_read_rows(self.db_path), ["restored"])

    def test_restore_main_database_only_applies(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            _overwrite_sqlite(self.db_path)

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--apply", "--database-only"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)
            self.assertEqual(_read_rows(self.db_path), ["live"])

    def test_restore_main_refuses_backend_mismatch(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["database_backend"] = "postgresql"
            manifest_path.write_text(json.dumps(manifest))

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--apply"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)


def settings_db_config():
    from django.conf import settings
    return settings.DATABASES["default"]

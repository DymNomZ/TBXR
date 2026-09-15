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

    def test_create_backup_rejects_backup_dir_under_media_root(self):
        overlapping_backup_root = self.media_root / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=overlapping_backup_root):
                with self.assertRaises(RuntimeError):
                    backup.create_backup(timestamp="2026-01-01T000000Z")

    def test_create_backup_rejects_media_root_under_backup_dir(self):
        nested_media = self.backup_root / "media"
        with _override_db_settings(nested_media, self.db_path):
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                with self.assertRaises(RuntimeError):
                    backup.create_backup(timestamp="2026-01-01T000000Z")

    def test_list_backup_dirs_skips_hidden_temp_dirs(self):
        (self.backup_root / "2026-01-01T000000Z").mkdir()
        (self.backup_root / "2026-01-01T000000Z" / "manifest.json").write_text("{}")
        (self.backup_root / ".2026-01-02T000000Z.tmp-abc").mkdir()
        (self.backup_root / "notes.txt").write_text("x")

        self.assertEqual(
            [p.name for p in backup.list_backup_dirs(self.backup_root)],
            ["2026-01-01T000000Z"],
        )

    def test_rename_into_place_disambiguates_with_zero_padded_suffix(self):
        first = self.backup_root / "2026-01-01T000000Z"
        first.mkdir()
        (first / "manifest.json").write_text("{}")
        second_staging = self.backup_root / ".staging2"
        second_staging.mkdir()
        (second_staging / "manifest.json").write_text("{}")

        second = backup._rename_into_place(second_staging, self.backup_root, "2026-01-01T000000Z")
        self.assertEqual(second.name, "2026-01-01T000000Z-01")

        third_staging = self.backup_root / ".staging3"
        third_staging.mkdir()
        (third_staging / "manifest.json").write_text("{}")
        third = backup._rename_into_place(third_staging, self.backup_root, "2026-01-01T000000Z")
        self.assertEqual(third.name, "2026-01-01T000000Z-02")

    def test_rename_into_place_propagates_unexpected_failure(self):
        staging = self.tmp / "staging"
        staging.mkdir()
        (staging / "manifest.json").write_text("{}")

        with mock.patch.object(os, "rename", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                backup._rename_into_place(staging, self.backup_root, "2026-01-01T000000Z")

        self.assertEqual(list(self.backup_root.iterdir()), [])
        self.assertTrue(staging.exists())

    def test_prune_backups_keeps_most_recent(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z", "2026-01-03T000000Z"):
            d = self.backup_root / name
            d.mkdir()
            (d / "manifest.json").write_text("{}")

        removed = backup.prune_backups(self.backup_root, keep=2)

        self.assertEqual([p.name for p in removed], ["2026-01-01T000000Z"])
        self.assertEqual(
            [p.name for p in backup.list_backup_dirs(self.backup_root)],
            ["2026-01-02T000000Z", "2026-01-03T000000Z"],
        )

    def test_prune_backups_keep_zero_disables_pruning(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z"):
            d = self.backup_root / name
            d.mkdir()
            (d / "manifest.json").write_text("{}")

        removed = backup.prune_backups(self.backup_root, keep=0)

        self.assertEqual(removed, [])
        self.assertEqual(len(backup.list_backup_dirs(self.backup_root)), 2)

    def test_prune_backups_ignores_unrelated_directories(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z"):
            d = self.backup_root / name
            d.mkdir()
            (d / "manifest.json").write_text("{}")
        unrelated = self.backup_root / "not-a-backup"
        unrelated.mkdir()
        (unrelated / "notes.txt").write_text("x")

        removed = backup.prune_backups(self.backup_root, keep=1)

        self.assertEqual([p.name for p in removed], ["2026-01-01T000000Z"])
        self.assertTrue(unrelated.exists())
        self.assertEqual(
            [p.name for p in backup.list_backup_dirs(self.backup_root)],
            ["2026-01-02T000000Z"],
        )

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

    def test_verify_backup_malformed_metadata_is_reported_not_raised(self):
        result = self._create_backup()
        backup_dir = result["backup_dir"]
        manifest_path = backup_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["database.sqlite3"] = "not-a-dict"
        manifest_path.write_text(json.dumps(manifest))

        verification = backup.verify_backup(backup_dir)

        self.assertFalse(verification["ok"])
        self.assertEqual(
            verification["files"]["database.sqlite3"]["error"],
            "invalid metadata",
        )

    def test_verify_backup_non_object_manifest_raises(self):
        result = self._create_backup()
        backup_dir = result["backup_dir"]
        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(json.dumps(["not", "an", "object"]))

        with self.assertRaises(ValueError):
            backup.verify_backup(backup_dir)

    def test_main_does_not_create_backup_dir_on_overlap(self):
        overlapping_backup_root = self.media_root / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=overlapping_backup_root):
                old_argv = sys.argv
                sys.argv = ["backup.py"]
                try:
                    rc = backup.main()
                finally:
                    sys.argv = old_argv

        self.assertEqual(rc, 1)
        self.assertFalse(overlapping_backup_root.exists())

    def test_prune_backups_ignores_directory_already_removed(self):
        for name in ("2026-01-01T000000Z", "2026-01-02T000000Z"):
            d = self.backup_root / name
            d.mkdir()
            (d / "manifest.json").write_text("{}")

        with mock.patch.object(shutil, "rmtree", side_effect=FileNotFoundError("already gone")):
            removed = backup.prune_backups(self.backup_root, keep=1)

        self.assertEqual(removed, [])
        # The concurrent-deletion race was tolerated: neither directory was
        # actually removed by the mocked rmtree.
        self.assertEqual(len(backup.list_backup_dirs(self.backup_root)), 2)


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

            # Rewrite the backup as a PostgreSQL backup so the manifest stays
            # internally consistent and this test reaches the backend-mismatch
            # refusal instead of the earlier target-binding validation.
            database_path = backup_dir / "database.sqlite3"
            renamed_database_path = backup_dir / "database.sql"
            database_path.rename(renamed_database_path)

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["database_backend"] = "postgresql"
            manifest["database_file"] = "database.sql"
            manifest["files"]["database.sql"] = manifest["files"].pop("database.sqlite3")
            manifest_path.write_text(json.dumps(manifest))

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--apply"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)

    def test_resolve_backup_dir_skips_hidden_staging_dirs(self):
        backup_root = self.tmp / "backups"
        backup_root.mkdir()
        (backup_root / "2026-01-01T000000Z").mkdir()
        (backup_root / "2026-01-01T000000Z" / "manifest.json").write_text("{}")
        (backup_root / ".2026-01-02T000000Z.tmp-abc").mkdir()

        with mock.patch.object(restore, "get_backup_dir", return_value=backup_root):
            resolved = restore.resolve_backup_dir(None)

        self.assertEqual(resolved.name, "2026-01-01T000000Z")

    def test_restore_sqlite3_removes_stale_sidecars(self):
        dump_path = self.tmp / "dump.sqlite3"
        _make_sqlite_db(dump_path, rows=("restored",))

        for suffix in ("-wal", "-shm", "-journal"):
            Path(str(self.db_path) + suffix).write_bytes(b"stale")

        with self._settings():
            restore.restore_sqlite3(settings_db_config(), dump_path)

        self.assertEqual(_read_rows(self.db_path), ["restored"])
        for suffix in ("-wal", "-shm", "-journal"):
            self.assertFalse(Path(str(self.db_path) + suffix).exists())

    def test_load_manifest_rejects_invalid_json(self):
        backup_dir = self.tmp / "backup"
        backup_dir.mkdir()
        (backup_dir / "manifest.json").write_text("{not valid json")

        with self.assertRaises(SystemExit):
            restore.load_manifest(backup_dir)

    def test_restore_main_handles_missing_manifest_field(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest.pop("database_file")
            manifest_path.write_text(json.dumps(manifest))

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--database-only"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)

    def test_load_manifest_rejects_non_object_json(self):
        backup_dir = self.tmp / "backup"
        backup_dir.mkdir()
        (backup_dir / "manifest.json").write_text("[1, 2, 3]")

        with self.assertRaises(SystemExit):
            restore.load_manifest(backup_dir)

    def test_stage_media_rejects_windows_rooted_paths(self):
        for idx, name in enumerate(("\\\\outside", "C:outside")):
            archive = self.tmp / f"unsafe-win-{idx}.tar.gz"
            _tar_with_regular_file(archive, name, b"x")

            with self.subTest(name=name):
                with self.assertRaises(RuntimeError):
                    restore.stage_media(archive, self.tmp)

    def test_stage_media_refuses_unfiltered_extraction(self):
        archive = self.tmp / "clean.tar.gz"
        _tar_with_regular_file(archive, "raw/img.png", b"png-bytes")

        with mock.patch.object(
            tarfile.TarFile, "extractall", side_effect=TypeError("no filter kwarg")
        ):
            with self.assertRaises(RuntimeError):
                restore.stage_media(archive, self.tmp)

    def test_stage_media_creates_missing_staging_parent(self):
        archive = self.tmp / "clean.tar.gz"
        _tar_with_regular_file(archive, "raw/img.png", b"png-bytes")

        missing_parent = self.tmp / "does" / "not" / "exist"
        staging = restore.stage_media(archive, missing_parent)

        self.assertTrue(staging.is_dir())
        self.assertTrue(missing_parent.exists())
        self.assertEqual((staging / "raw" / "img.png").read_bytes(), b"png-bytes")
        shutil.rmtree(staging, ignore_errors=True)

    def test_restore_sqlite3_preserves_old_db_and_sidecars_on_failure(self):
        dump_path = self.tmp / "dump.sqlite3"
        _make_sqlite_db(dump_path, rows=("restored",))

        sidecar = Path(str(self.db_path) + "-wal")
        sidecar.write_bytes(b"live-wal")

        real_replace = os.replace
        calls = []

        def fake_replace(src, dst):
            calls.append((src, dst))
            # Fail when installing the freshly copied snapshot (the last replace),
            # after the live DB and sidecar have already been parked aside.
            if len(calls) == 3:
                raise OSError("simulated failure")
            return real_replace(src, dst)

        with self._settings():
            with mock.patch.object(os, "replace", side_effect=fake_replace):
                with self.assertRaises(OSError):
                    restore.restore_sqlite3(settings_db_config(), dump_path)

        # Assert the sidecar survived before opening the database via sqlite3,
        # since a later connection would recover/reset the (intentionally
        # non-sqlite) WAL sidecar and mask the rollback we are testing.
        self.assertEqual(sidecar.read_bytes(), b"live-wal")
        self.assertEqual(_read_rows(self.db_path), ["live"])

    def test_restore_main_full_apply_restores_db_and_media(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            (self.media_root / "raw").mkdir()
            (self.media_root / "raw" / "img.png").write_bytes(b"png-bytes")

            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            _overwrite_sqlite(self.db_path)
            shutil.rmtree(self.media_root)
            self.media_root.mkdir()

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--apply"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)
            self.assertEqual(_read_rows(self.db_path), ["live"])
            self.assertEqual(
                (self.media_root / "raw" / "img.png").read_bytes(), b"png-bytes"
            )

    def test_restore_main_stages_media_before_restoring_database(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            _overwrite_sqlite(self.db_path)

            with mock.patch.object(restore, "stage_media", side_effect=RuntimeError("bad archive")):
                old_argv = sys.argv
                sys.argv = ["restore.py", str(backup_dir), "--apply"]
                try:
                    rc = restore.main()
                finally:
                    sys.argv = old_argv

            self.assertEqual(rc, 1)
            # Media staging failed first, so the database was never restored.
            self.assertEqual(_read_rows(self.db_path), [])

    def test_restore_main_refuses_database_file_not_matching_backend(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["database_file"] = "media.tar.gz"
            manifest_path.write_text(json.dumps(manifest))

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--database-only"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)

    def test_restore_main_refuses_unexpected_media_file(self):
        self.backup_root = self.tmp / "backups"
        with self._settings():
            with mock.patch.object(backup, "get_backup_dir", return_value=self.backup_root):
                result = backup.create_backup(timestamp="2026-01-01T000000Z")
            backup_dir = result["backup_dir"]

            manifest_path = backup_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["media_file"] = "database.sqlite3"
            manifest_path.write_text(json.dumps(manifest))

            old_argv = sys.argv
            sys.argv = ["restore.py", str(backup_dir), "--media-only"]
            try:
                rc = restore.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)


def settings_db_config():
    from django.conf import settings
    return settings.DATABASES["default"]

# Backup & Restore

Automated backups for the TB-XR PostgreSQL (or SQLite) database and the
uploaded media assets (X-ray raw images, processed images, and AI heatmaps).

## What gets backed up

| Asset | Source | Backup file |
|-------|--------|-------------|
| Database | PostgreSQL (`DB_NAME` set) or SQLite fallback | `database.sql` / `database.sqlite3` |
| Uploaded media | `backend/media/` (`raw/`, `xray_processed/`, `heatmaps/`) | `media.tar.gz` |
| Integrity manifest | Generated each run | `manifest.json` (SHA256 of the two files above) |

Each run writes a timestamped directory under the backup root:

```
backend/backups/2026-09-15T020000Z/
    database.sql
    media.tar.gz
    manifest.json
```

## Configuration

| Environment variable | Default | Purpose |
|----------------------|---------|---------|
| `BACKUP_DIR` | `backend/backups/` | Where backups are written. Git-ignored. |
| `BACKUP_RETENTION_COUNT` | `14` | Number of most-recent backups to keep (`0` keeps all). |

The database backend is detected the same way the app detects it: PostgreSQL
when `DB_NAME` is set, otherwise SQLite at `backend/db.sqlite3`. PostgreSQL
backups use `pg_dump` (plain SQL), which must be on `PATH`. The password is
read from `backend/.env` and passed via `PGPASSWORD`; it is never written to
disk.

Backups contain PHI, so the script creates the backup root and each per-run
directory with mode `0700`, and the database dump, media archive, and manifest
with mode `0600`. Keep `BACKUP_DIR` on storage you control and ensure it is
not world-readable.

`BACKUP_DIR` and `MEDIA_ROOT` must be disjoint: neither path may contain the
other. If `BACKUP_DIR` were nested under `MEDIA_ROOT`, the media archive would
include its own output, and a media restore that replaces `MEDIA_ROOT` would
delete the backups. The backup script refuses to run when the two paths overlap.

## Running a backup

```bash
cd backend
python scripts/backup.py
```

Expected output confirms the created directory, the database and media files,
and any retention pruning.

Verify an existing backup's integrity:

```bash
python scripts/backup.py --verify backups/2026-09-15T020000Z
```

## Scheduling

Run daily (or as often as your data changes). Example crontab entry for a
daily backup at 02:00:

```cron
0 2 * * * mkdir -p /srv/tbxr/backend/backups && cd /srv/tbxr/backend && /srv/tbxr/backend/venv/bin/python scripts/backup.py >> backups/backup.log 2>&1
```

A `systemd` timer is equally valid. Point `BACKUP_DIR` at a location that is
itself backed up or replicated off-host (see Assumptions).

## Retention

`BACKUP_RETENTION_COUNT` controls how many of the most-recent backups are kept.
After a successful backup the script deletes the oldest directories beyond that
limit. The default of `14` retains roughly two weeks of daily backups. Set it
to `0` to disable pruning and keep every backup. Adjust per your recovery-point
objective and available storage.

## Restore procedure

> Restore overwrites the live database and media. Stop the application server
> first and take a fresh backup before proceeding.

1. Stop the Django application server.

2. Dry-run first (this verifies checksums and prints the plan without writing):

   ```bash
   cd backend
   python scripts/restore.py                     # latest backup
   python scripts/restore.py backups/2026-09-15T020000Z   # a specific backup
   ```

3. Apply the restore:

   ```bash
   python scripts/restore.py backups/2026-09-15T020000Z --apply
   ```

   Use `--database-only` or `--media-only` to restore a single component.

4. Run migrations to confirm the schema matches the code, then restart the app:

   ```bash
   python manage.py migrate
   ```

The restore script refuses to run if the manifest checksums do not match.

The PostgreSQL restore runs inside a single transaction (`--single-transaction`),
so a failed restore rolls back rather than leaving a half-restored database.
Media is staged to a temporary directory and validated before the database is
touched, then written into the active `MEDIA_ROOT` (the path recorded in the
manifest is informational only).

A full restore is not atomic across the database and media: the database is
restored first, then media is swapped into place. If the media swap fails after
the database restore succeeds, the database is restored but media may remain
unchanged. Re-run the media restore (or use `--media-only`) to retry.

## Verification / operational checklist

- After each backup, run `python scripts/backup.py --verify <dir>` and confirm
  `[PASS]`.
- Confirm files exist in `backend/backups/<timestamp>/` (database dump, media
  archive, manifest).
- Periodically (e.g. monthly) run a restore drill into a scratch database to
  prove the backups are restorable, not just present.
- Confirm `BACKUP_DIR` is on storage that is replicated or copied off-host.

## Assumptions

- Backups are stored **locally** under `BACKUP_DIR` by default. Off-host
  replication (object storage, NFS, tape, cloud snapshot) is **out of scope**
  and must be provided by the deployment environment.
- PostgreSQL uses a **plain-SQL** `pg_dump` (`--clean --if-exists`), restored
  with `psql --single-transaction`, so restore drops and re-creates existing
  objects and rolls back on any failure. Both tools must be available on
  `PATH`.
- SQLite backups use SQLite's online backup API, producing a consistent copy of
  the live database file.
- Media assets are the only critical uploaded content; the archive captures
  everything under `MEDIA_ROOT`.
- Backups are **crash-consistent, not transactionally consistent** across the
  database and media. The database dump and media archive are captured
  sequentially, so a record written after its upload finished (or an upload
  that lands while the archive is being built) may not line up perfectly
  between the two. For point-in-time consistency across both, schedule backups
  during a low-activity window or quiesce writes first.

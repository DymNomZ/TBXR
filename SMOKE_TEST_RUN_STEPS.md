# Smoke Test Run Guide

**What this is:** a 2-minute regression net for the two riskiest backend paths —
the **logout** route and the **PDF report** endpoint. Anyone on the team can run
it in under two minutes; CI runs the exact same tests on every push/PR.

**Skip to:** [Quick start](#quick-start--read-this-first) · [What the tests check](#what-the-tests-actually-check) · [Troubleshooting](#troubleshooting)

---

## Quick start (read this first)

Prerequisite: you have the repo cloned and the backend virtualenv created
(`.venv` at the repo root — the one used for normal backend work).

```bash
cd backend
source ../.venv/bin/activate          # skip if your venv is already active
DB_NAME= python manage.py test apps.accounts.test_smoke apps.imaging.test_smoke -v 2
```

That is the whole run. The `DB_NAME=` prefix forces SQLite so the tests never
touch your local Postgres database — this is exactly how CI runs them too.

Expect 6 tests, all green:

```
Found 6 test(s).
...
test_get_logout_returns_405 ... ok
test_post_logout_returns_200_and_clears_session ... ok
test_completed_record_returns_pdf ... ok
test_missing_record_returns_404 ... ok
test_non_radiologist_returns_403 ... ok
test_pending_record_returns_400 ... ok

Ran 6 tests in ~1s

OK
```

`OK` at the end = everything works. If you see `FAILED` instead, jump to
[Troubleshooting](#troubleshooting).

> **Windows:** if your venv is a Windows environment, activate it with
> `..\venv\Scripts\activate` instead of `source ../.venv/bin/activate`.

---

## What the tests actually check

Two small test files, each targeting one at-risk route. Both follow the same
pattern: set up a fake user + fake data, call the endpoint, assert the response
is exactly what a real user would get.

### 1. Logout route — `apps/accounts/test_smoke.py`

Target: `POST /accounts/logout/` (the `accounts:logout` route).

| Test | What it does | Expected result |
|------|--------------|-----------------|
| `test_post_logout_returns_200_and_clears_session` | Logs a user in, then POSTs to `/logout/` | HTTP **200**, body `{"detail": "Logged out."}`, and the session is actually cleared (the `_auth_user_id` marker is gone) |
| `test_get_logout_returns_405` | Hits the logout route with a GET request (wrong method) | HTTP **405 Method Not Allowed** — the route only accepts POST |

### 2. PDF report endpoint — `apps/imaging/test_smoke.py`

Target: `GET /api/imaging/xray/<scan-id>/report/` (the `imaging:generate_report`
route). A radiologist requests a generated PDF for an X-ray. The actual
node/Puppeteer/Chromium rendering step is **mocked** — tests verify the backend's
decisions, not the PDF renderer's output.

| Test | What it does | Expected result |
|------|--------------|-----------------|
| `test_completed_record_returns_pdf` | Radiologist asks for a PDF of a scan whose status is **COMPLETED** | HTTP **200**, `Content-Type: application/pdf`, download filename `tbxr_report_<scan-id>.pdf`, and the body starts with `%PDF`. Also proves the renderer was invoked with `node` + `capture_output=True` + `check=True` |
| `test_pending_record_returns_400` | Radiologist asks for a PDF of a scan still **PENDING** | HTTP **400** — reports only exist once a scan is COMPLETED |
| `test_non_radiologist_returns_403` | A **technician** (not a radiologist) asks for a PDF | HTTP **403 Forbidden** — report generation is radiologist-only |
| `test_missing_record_returns_404` | Radiologist asks for a PDF of a **random/nonexistent** scan ID | HTTP **404 Not Found** |

### Why these six tests matter

Each one pins down a regression that has already bitten this project:

- Logout silently breaking (wrong route, wrong method handling, session not cleared).
- Report generation silently breaking (status guard, role check, missing records, wrong file output).

If any of those slip, the corresponding test turns red — locally or in CI — before
anyone ships the bug.

---

## Full suite (optional regression check)

The smoke tests are the fast gate. To also confirm nothing else in the backend
regressed, run the entire test suite the same way:

```bash
DB_NAME= python manage.py test -v 2
```

---

## CI

`.github/workflows/ci.yml` runs the identical smoke command on every push and PR:

- Python 3.12, fresh Ubuntu runner
- Installs `backend/requirements.txt`
- Runs `python manage.py test apps.accounts.test_smoke apps.imaging.test_smoke -v 2`
- No `.env` exists in CI ⇒ SQLite is used automatically (the same as the `DB_NAME=` prefix locally)

You can watch it live in the **Actions** tab of the repo.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Got an error creating the test database: permission denied to create database` | You ran **without** the `DB_NAME=` prefix, so the test runner tried to create a database on your local Postgres, and your Postgres user isn't allowed to create databases | Rerun with the prefix: `DB_NAME= python manage.py test ...` (recommended). Or, if you specifically want Postgres-based runs, grant the privilege once: `sudo -u postgres psql -c "ALTER USER <your_db_user> CREATEDB;"` |
| `Command 'python' not found` / missing packages | Venv not activated or dependencies not installed | Activate your venv, then `pip install -r requirements.txt` and run again |
| `No module named ...` at import time | Same as above — the imaging views import `cv2`, `numpy`, etc. at import time | Install `requirements.txt`; the venv must be active |
| One or more tests report `FAILED` | This is the net working — a real regression in logout or report generation | Read the failing assertion (`-v 2` shows exactly which check and what value broke), fix the source code, re-run. If you just want to sanity-check locally, tweak e.g. the logout message or the `"COMPLETED"` guard and watch the matching test fail, then revert |
| Worried you need `node` / Puppeteer / Chromium installed | You don't | The report tests mock the `subprocess.run` call — the real renderer is never invoked in tests or CI |

---

## Files & references

| Purpose | File |
|---------|------|
| This guide | `SMOKE_TEST_RUN_STEPS.md` |
| Source plan (design decisions) | `SMOKE_TEST_CI_PLAN.md` |
| Logout tests | `backend/apps/accounts/test_smoke.py` |
| Report tests | `backend/apps/imaging/test_smoke.py` |
| CI pipeline | `.github/workflows/ci.yml` |
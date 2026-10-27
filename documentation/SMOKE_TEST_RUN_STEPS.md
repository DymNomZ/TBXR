# Smoke Test Run Guide

**What this is:** a fast regression net for the riskiest backend paths — the
**logout** route, the **report workflow** (draft → finalize → PDF), the
**physician dashboard**, and **AI failure recovery**. Anyone on the team can run
it in a couple of minutes; CI runs these same suites on every push/PR.

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
touch your local Postgres database — this is exactly how CI runs them too. A
convenience runner with readable output and failure hints is also available:
`python scripts/run_smoke.py` (from `backend/`, venv active).

Expect 22 tests, all green:

```
Found 18 test(s).
...
test_post_logout_returns_200_and_clears_session ... ok
test_get_logout_returns_405 ... ok
test_completed_record_returns_pdf ... ok
test_pending_record_returns_400 ... ok
test_non_radiologist_returns_403 ... ok
test_missing_record_returns_404 ... ok
test_create_report_draft ... ok
test_create_report_draft_allows_empty_fields ... ok
test_retrieve_report ... ok
test_update_report_draft ... ok
test_cannot_update_finalized_report ... ok
test_final_submit_rejects_missing_fields ... ok
test_final_submit_succeeds_with_all_fields ... ok
test_draft_then_finalize_workflow ... ok
test_tech_cannot_create_report ... ok
test_generate_report_uses_persisted_report_data ... ok
test_patient_role_can_access_dashboard_summary ... ok
test_patient_role_has_read_only_report_access ... ok
test_patient_role_cannot_generate_pdf ... ok
test_patient_role_can_view_xray_detail ... ok
test_physician_dashboard_smoke_flow ... ok
test_ai_failure_then_retry_succeeds ... ok

Ran 22 tests

OK
```

`OK` at the end = everything works. If you see `FAILED` instead, jump to
[Troubleshooting](#troubleshooting).

> **Windows:** if your venv is a Windows environment, activate it with
> `..\venv\Scripts\activate` instead of `source ../.venv/bin/activate`.

---

## What the tests actually check

Two test files cover the at-risk routes. Both follow the same pattern: set up
a fake user + fake data, call the endpoint, assert the response is exactly
what a real user would get.

### 1. Logout route — `apps/accounts/test_smoke.py`

Target: `POST /accounts/logout/` (the `accounts:logout` route).

| Test | What it does | Expected result |
|------|--------------|-----------------|
| `test_post_logout_returns_200_and_clears_session` | Logs a user in, then POSTs to `/logout/` | HTTP **200**, body `{"detail": "Logged out."}`, and the session is actually cleared (the `_auth_user_id` marker is gone) |
| `test_get_logout_returns_405` | Hits the logout route with a GET request (wrong method) | HTTP **405 Method Not Allowed** — the route only accepts POST |

### 2. Report workflow — `apps/imaging/test_smoke.py`

Target: `GET/POST/PATCH /api/imaging/xray/<scan-id>/report/` (the
`imaging:report_detail` route) and `GET /api/imaging/xray/<scan-id>/report/generate/`
(the `imaging:generate_report` route). The actual node/Puppeteer/Chromium
rendering step is **mocked** — tests verify the backend's decisions, not the
PDF renderer's output.

| Test | What it does | Expected result |
|------|--------------|-----------------|
| `test_completed_record_returns_pdf` | Radiologist asks for a PDF of a scan whose status is **COMPLETED** | HTTP **200**, `Content-Type: application/pdf`, download filename `tbxr_report_<scan-id>.pdf`, and the body starts with `%PDF`. Also proves the renderer was invoked with `node` + `capture_output=True` + `check=True` |
| `test_pending_record_returns_400` | Radiologist asks for a PDF of a scan still **PENDING** | HTTP **400** — reports only exist once a scan is COMPLETED |
| `test_non_radiologist_returns_403` | A **technician** (not a radiologist) asks for a PDF | HTTP **403 Forbidden** — report generation is radiologist-only |
| `test_missing_record_returns_404` | Radiologist asks for a PDF of a **random/nonexistent** scan ID | HTTP **404 Not Found** |
| `test_create_report_draft` / `test_create_report_draft_allows_empty_fields` | Radiologist saves a draft | Draft persisted with `status=DRAFT`; empty fields allowed while drafting |
| `test_retrieve_report` / `test_update_report_draft` | Read and update a draft | HTTP 200 with the report payload |
| `test_cannot_update_finalized_report` | PATCH a **SUBMITTED** report | HTTP **400** — finalized reports are immutable |
| `test_final_submit_rejects_missing_fields` / `test_final_submit_succeeds_with_all_fields` | Finalize with missing / complete fields | **400** with field errors vs. successful submission |
| `test_draft_then_finalize_workflow` | Full draft → finalize chain | Workflow transitions end-to-end, including the physician notification trigger |
| `test_tech_cannot_create_report` | Technician tries to write a report | HTTP **403** — report writing is radiologist-only |
| `test_generate_report_uses_persisted_report_data` | Generate the PDF | The rendered context uses the persisted report fields, not placeholder data |

### 3. Physician dashboard & AI failure-retry — `apps/imaging/test_smoke.py`

| Test | What it does | Expected result |
|------|--------------|-----------------|
| `test_physician_dashboard_smoke_flow` | Physician logs in and opens the dashboard | HTTP **200** with the summary payload (finalized cases, alerts, patient progress) |
| `test_patient_role_can_access_dashboard_summary` | PATIENT respondent opens the same finalized-case dashboard endpoint | HTTP **200** with read-only summary payload |
| `test_patient_role_has_read_only_report_access` | PATIENT respondent attempts report read and write actions | `GET` succeeds, `POST/PATCH` return **403** |
| `test_patient_role_cannot_generate_pdf` | PATIENT respondent tries PDF generation | HTTP **403** |
| `test_patient_role_can_view_xray_detail` | PATIENT respondent opens X-ray details | HTTP **200** |
| `test_ai_failure_then_retry_succeeds` | AI inference fails, then the case is re-analysed | Failure routes the case to **MANUAL_REVIEW**; re-running `POST .../analyse/` recovers with a stored AI result |

### Why these tests matter

Each one pins down a regression that has already bitten this project:

- Logout silently breaking (wrong route, wrong method handling, session not cleared).
- Report generation silently breaking (status guard, role check, missing records, wrong file output).
- The draft → finalize workflow regressing (validation gaps, finalized-report edits, role leaks).
- Physician dashboard or AI-failure handling breaking unnoticed.

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

`.github/workflows/ci.yml` runs two jobs on every push and PR:

**smoke-tests** (Python 3.12, fresh Ubuntu runner):
- Installs `backend/requirements.txt`
- Runs `coverage run --rcfile=.coveragerc manage.py test apps.accounts.test_smoke apps.imaging.test_smoke apps.imaging.test_report scripts.test_backup_restore -v 2` — the smoke suites plus the report workflow and backup/restore suites
- Enforces a coverage gate on `apps.imaging` (`fail_under = 40`)
- No `.env` exists in CI ⇒ SQLite is used automatically (the same as the `DB_NAME=` prefix locally)

**frontend-test** (Node 22):
- `npm ci`, `npm run test`, `npm run lint`

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
| This guide | `documentation/SMOKE_TEST_RUN_STEPS.md` |
| Logout tests | `backend/apps/accounts/test_smoke.py` |
| Report tests | `backend/apps/imaging/test_smoke.py` |
| CI pipeline | `.github/workflows/ci.yml` |
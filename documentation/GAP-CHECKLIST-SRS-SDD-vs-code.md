# TB-XR Gap Checklist

Status: **Closure pass completed 2026-09-25.** All items were re-verified against the codebase (as-built reference: `documentation/refactored-SRS.md`; delivery evidence: sprint PRs #166–#203, 2026-08-19 → 2026-09-21). Remaining open items are tracked in the refactored SRS §7 (Known Limitations).

Comparison basis:
- Planned design and requirements from SRS and SDD
- Current implementation state from the 2026-08-13 codebase audit (snapshot removed 2026-09-25; recoverable from git history) and the as-built `documentation/refactored-SRS.md`

Legend:
- [x] Closed / implemented (verified in code)
- [~] Partial (known limitation, tracked in refactored SRS §7)
- [ ] Missing

## 1) Module 2: Annotation and Diagnostic Review

- [x] Rich annotation tools are implemented.
  - Planned: rectangle, freehand, circle, delete selected annotation, undo.
  - Current: all five tools implemented in `frontend/src/components/imaging/AnnotationCanvas.jsx` (rectangle/circle/freehand tool set, `deleteSelected`, `undoLastAction`).

- [x] Structured diagnostic submission form is implemented.
  - Planned: Findings, Impression, Recommendation, Severity Classification.
  - Current: `Report` model carries `findings`, `impression`, `recommendation`, `severity` (NORMAL/MILD/MODERATE/SEVERE/CRITICAL); structured form in `frontend/src/pages/ReportWritePage.jsx`.

- [x] Save-draft workflow for diagnostic report is implemented.
  - `POST /api/imaging/xray/<id>/report/` persists reports as `status=DRAFT`; Save Draft button wired in the report form.

- [x] Validation flow for required submission fields is implemented.
  - Final submission (`status=SUBMITTED`) is rejected with field errors when any of the four required fields is empty; covered by `test_final_submit_rejects_missing_fields`.

- [x] Physician notification after report submission is implemented.
  - Notification created for the physician on successful final submit; notification center UI (bell, unread badge, mark-read) in the app header.
  - Caveat (refactored SRS limitation #5): no physician-assignment model — the notification targets the first physician by ID.

- [x] Concurrency conflict handling on review is implemented.
  - `active_reviewer`/`lock_timestamp` lock with a 60-minute timeout; conflicting radiologists receive HTTP 409 and a read-only review mode with disabled annotation tools.

- [~] Review display controls are partially complete.
  - Planned: brightness/contrast/zoom view controls.
  - Current: zoom/pan present; no brightness/contrast controls — tracked as refactored SRS limitation #14.

## 2) Module 3: AI Engine and Longitudinal Monitoring

- [~] AI failure-handling path is partial.
  - Implemented: structured error types (`TIMEOUT`/`UNREACHABLE`/`FAILED`) from `ai/scripts/inference.py`, `MANUAL_REVIEW` record status plus radiologist notification on failure, and manual re-run via `POST /api/imaging/xray/<id>/analyse/`.
  - Still missing: an automatic retry loop — tracked as refactored SRS limitation #1.

- [x] Standardization failure handling is implemented.
  - Image quality gate (`ai/scripts/quality.py`, threshold 0.6) returns `quality_check_failed` with a blocking confirm-or-re-upload prompt (`force_proceed` to continue).

- [x] Comparative progression tracking module is implemented.
  - `ProgressionService` delta rules (improvement/stable/deterioration with configurable threshold), `ProgressionStatus` snapshots, case/patient progression history endpoints, and the trend chart in `LongitudinalPanel.jsx`. Rules documented in `documentation/progression-service.md`.

- [x] Radiologist manual override of progression status is implemented.
  - `POST /api/imaging/cases/<id>/progression/override/` requires a non-empty clinical note and writes a `ProgressionOverrideAuditLog` entry; override dropdown + note modal + history in the UI.

## 3) Module 4: Clinical Dashboards and Reporting

- [x] Physician dashboard endpoint and complete physician role experience are implemented.
  - `GET /api/physician/dashboard` (plus imaging-scoped alias) with severity/date filters; role-gated `PhysicianDashboardPage.jsx`.

- [x] Notification center for in-system alerts is implemented.
  - `GET /api/imaging/notifications/`, `POST /api/imaging/notifications/<id>/mark-read/`, bell + panel + unread badge in the header.

- [x] Consolidated reporting analytics is implemented.
  - `GET /api/analytics/summary/` with date/severity filters; analytics dashboard page with charts.

- [x] Consolidated export endpoint for PDF/CSV is implemented.
  - `POST /api/analytics/export/` producing CSV and PDF (Node/Puppeteer) exports.

- [x] Logout flow fixed.
  - Frontend calls `/accounts/logout/`, matching the backend route; covered by logout smoke tests.

## 4) Data/Model and Report Output Gaps

- [x] Report patient sex field mapping fixed.
  - Report pipeline reads `patient.sex`; the PDF renders `patient_sex`.

- [x] Risk-filtering in dashboard reached parity.
  - Both dashboard tables expose LOW, MODERATE, HIGH filters and pass `risk_label` to the API.
  - Nuance (refactored SRS limitation #2): the shipped binary model never emits MODERATE.

## 5) SRS Constraint / Non-Functional Compliance Gaps

- [x] Ethical AI disclaimer is implemented.
  - Reusable `AIDisclaimer.jsx` rendered globally via the app layout, plus the disclaimer in the PDF report template and the low-quality upload modal. Canonical text frozen in `documentation/W1-CONTRACT-FREEZE-2026-08-22.md`.

- [x] Production security hardening is implemented.
  - Env-driven settings with production guards (enforced `DEBUG=false`, ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS validation, secure cookies, HSTS), `.env.production.example` profile; see `documentation/SECURITY-ENV-PROFILE.md`.

- [x] Reliability backup requirement is implemented.
  - `backend/scripts/backup.py` / `restore.py` with SHA256 manifest verification, retention pruning, advisory locking, and a 56-test suite; runbook in `documentation/backup-restore.md`.

## 6) Navigation / UX Scope Drift

- [x] Sidebar placeholder modules removed.
  - Appointments/Doctor/Messages/Settings links removed (PR #195); the sidebar keeps Dashboard, role-gated Analytics, and Patients only.

## 7) CI / Regression Safety Net

- [x] Automated smoke tests cover the auth/logout, report workflow, physician dashboard, and AI failure-retry paths and run in CI on push/PR.
  - Tests: `backend/apps/accounts/test_smoke.py` (2), `backend/apps/imaging/test_smoke.py` (16)
  - Pipeline: `.github/workflows/ci.yml` (also runs the report and backup/restore suites with a coverage gate, plus frontend test/lint)

## Remaining open items

All remaining gaps are tracked in `documentation/refactored-SRS.md` §7 (Known Limitations), notably:
- #1 No automatic AI retry (manual re-run only)
- #2 MODERATE risk label never produced by the binary model
- #5 No physician-assignment model for notifications
- #14 No brightness/contrast display controls

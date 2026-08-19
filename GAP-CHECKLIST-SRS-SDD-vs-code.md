# TB-XR Gap Checklist

Comparison basis:
- Planned design and requirements from SRS and SDD
- Current implementation state from SUMMARY-AS-OF-2026-08-13.md

Legend:
- [ ] Missing
- [~] Partial / half-baked

## 1) Module 2: Annotation and Diagnostic Review

- [~] Rich annotation tools beyond bounding boxes are incomplete.
  - Planned: rectangle, freehand, circle, delete selected annotation, undo.
  - Current: interactive annotation exists, but advanced toolset completeness is not evidenced in the summary.

- [~] Structured diagnostic submission form is incomplete.
  - Planned: Findings, Impression, Recommendation, Severity Classification.
  - Current: annotation notes and completion workflow exist, but full structured report fields are not confirmed.

- [ ] Save-draft workflow for diagnostic report is missing.
  - Planned: draft save with status remaining in progress.
  - Current: not listed as implemented.

- [ ] Validation flow for required submission fields is missing.
  - Planned: block submission when required fields are empty.
  - Current: not listed as implemented for structured report fields.

- [ ] Physician notification after report submission is missing.
  - Planned: automatic in-system notification to assigned physician with patient and report link.
  - Current: no notifications module/endpoints shown as implemented.

- [ ] Concurrency conflict handling on review is missing.
  - Planned: if another radiologist is reviewing, show warning and open read-only mode.
  - Current: not listed as implemented.

- [~] Review display controls are partially complete.
  - Planned: brightness/contrast/zoom view controls.
  - Current: zoom/pan and viewing are present; brightness/contrast controls are not confirmed.

## 2) Module 3: AI Engine and Longitudinal Monitoring

- [~] AI failure-handling path is partial.
  - Planned: retries on timeout/unreachable AI engine, explicit unavailable status, and queue alert for manual-only review.
  - Current: AI scoring and persistence are implemented; explicit retry-and-alert behavior is not fully confirmed.

- [~] Standardization failure handling is partial.
  - Planned: quality failure flow with user-facing prompt for low-quality images.
  - Current: upload validation and preprocessing are implemented, but low-quality confirmation flow is not listed.

- [ ] Comparative progression tracking module is missing.
  - Planned: delta computation (improvement/stable/deterioration), trend graph, and progression status.
  - Current: longitudinal history and compare UI exist, but no explicit progression computation service/log endpoint is listed.

- [ ] Radiologist manual override of progression status is missing.
  - Planned: override dropdown plus required clinical note.
  - Current: not listed as implemented.

## 3) Module 4: Clinical Dashboards and Reporting

- [ ] Physician dashboard endpoint and complete physician role experience are missing.
  - Planned: role-specific physician dashboard with reviewed cases, alerts, and report access.
  - Current: tech/radiologist dashboards are implemented; physician dashboard implementation is not confirmed.

- [ ] Notification center for in-system alerts is missing.
  - Planned: physician-directed report-ready notifications.
  - Current: no notification endpoints/module in implemented list.

- [ ] Consolidated reporting analytics is missing.
  - Planned: date/severity parameterized aggregate report with charts/tables.
  - Current: single-case PDF report generation exists; aggregate reporting is not listed.

- [ ] Consolidated export endpoint for PDF/CSV is missing.
  - Planned: export aggregated report artifacts.
  - Current: no aggregate export endpoint in summary.

- [~] Logout flow is half-baked due to route mismatch.
  - Planned: secure and reliable logout.
  - Current: frontend calls /api/accounts/logout while backend route is /accounts/logout.

## 4) Data/Model and Report Output Gaps

- [~] Report patient sex field mapping is half-baked.
  - Planned: accurate patient demographic output.
  - Current: report references patient.gender while model field is patient.sex.

- [~] Risk-filtering in dashboard is partial.
  - Planned/Designed model choices include LOW, MODERATE, HIGH.
  - Current: UI filter exposes LOW and HIGH only.

## 5) SRS Constraint / Non-Functional Compliance Gaps

- [~] Ethical AI disclaimer appears partial or unverified in all required dashboard views.
  - Planned: visible, non-dismissible disclaimer across dashboard analytics.
  - Current: this is not confirmed as universally implemented in the summary.

- [~] Production security hardening is partial.
  - Planned: robust security posture (privacy-oriented controls).
  - Current: DEBUG true and minimal CSRF trusted origins are noted; acceptable for dev but incomplete for deployment-grade posture.

- [ ] Reliability backup requirement is missing from evidenced implementation.
  - Planned: regular automated backups for longitudinal records.
  - Current: no backup mechanism listed in summary.

## 6) Navigation / UX Scope Drift

- [~] Sidebar modules are half-baked placeholders.
  - Planned product clarity requires implemented or intentionally removed modules.
  - Current: Appointments, Doctor, Messages, Settings links exist without routed pages.

## 7) CI / Regression Safety Net

- [x] Automated smoke tests cover the auth/logout and report-generation routes and run in CI on push/PR.
  - Tests: backend/apps/accounts/test_smoke.py, backend/apps/imaging/test_smoke.py
  - Pipeline: .github/workflows/ci.yml
  - Verified: host run 2026-08-19 — 6/6 smoke tests pass

## Prioritized Fix Order (suggested)

1. Fix logout route mismatch and report demographic mapping (high impact, low effort).
2. Implement structured diagnostic report model/workflow (Findings, Impression, Recommendation, Severity, validation, draft).
3. Add physician notification pipeline and physician dashboard surface.
4. Implement progression summary service + trend UI + manual override logging.
5. Build consolidated analytics and export endpoints (module 4.3 scope).
6. Close non-functional gaps: dashboard disclaimer consistency, security hardening profile, and automated backup plan.

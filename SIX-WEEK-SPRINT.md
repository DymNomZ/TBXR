# TB-XR: 6-Week Sprint Board

## Team Mapping
1. **Dymes** (Tech Lead + Frontend)
2. **Seth** (AI Engineer)
3. **Lance** (Backend Developer)
4. **Raimar** (Backend Developer)
5. **Brent** (DevOps Engineer)

## Sprint Structure
- **Sprint Length:** 1 week each, for 6 weeks total
- **Cadence:** Monday planning, daily 15-min standup, Friday demo + retro
- **Definition of Done per ticket:**
  1. Code merged to develop
  2. Endpoint or UI behavior verified
  3. Basic test added or updated
  4. Gap checklist item status updated

---

# WEEK 1: Stability Fixes and Baseline Alignment
**Goal:** Remove high-impact low-effort defects and lock API contracts.

## W1-T1: Logout route fix
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 2 |
| **Coding Block** | Align frontend logout call path with backend route and update auth service constants. |
| **Acceptance Criteria** | <ul><li>Frontend axios call uses correct backend logout route</li><li>Auth service constants updated</li><li>Logout flow tested end-to-end</li><li>No 404 errors on logout</li></ul> |
| **Output** | Reliable logout flow end-to-end |
| **Gap Covered** | Logout route mismatch |

## W1-T2: Report demographic mapping fix
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 2 |
| **Coding Block** | Replace report field usage from `gender` to `sex` in report serializer/template pipeline. |
| **Acceptance Criteria** | <ul><li>Report model references patient.sex</li><li>Serializer outputs correct sex field</li><li>Generated PDF report displays correct sex value</li><li>No template rendering errors</li></ul> |
| **Output** | Correct patient sex in generated reports |
| **Gap Covered** | Patient sex field mapping |

## W1-T3: Risk filter options parity
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 3 |
| **Coding Block** | Update dashboard filter UI and API query params to support LOW, MODERATE, HIGH. |
| **Acceptance Criteria** | <ul><li>Dashboard filter UI shows all three severity options</li><li>API endpoint accepts LOW, MODERATE, HIGH params</li><li>Filter logic correctly returns matching cases</li><li>UI reflects filtered results accurately</li></ul> |
| **Output** | Full severity filtering in UI |
| **Gap Covered** | Partial risk filtering |

## W1-T4: Global disclaimer injection
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 3 |
| **Coding Block** | Add reusable disclaimer component and render in all required dashboard/report views. |
| **Acceptance Criteria** | <ul><li>Disclaimer component created and reusable</li><li>Visible on all dashboard pages</li><li>Visible in PDF reports</li><li>Non-dismissible, always present</li><li>Clear messaging about AI non-definitive nature</li></ul> |
| **Output** | Consistent visible non-definitive AI disclaimer |
| **Gap Covered** | Ethical AI disclaimer consistency |

## W1-T5: CI smoke tests for auth/report paths
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Add backend API smoke tests and frontend flow checklist for logout/report generation. |
| **Acceptance Criteria** | <ul><li>Smoke test suite includes auth and report endpoints</li><li>CI pipeline runs tests on every push</li><li>Frontend logout flow tested</li><li>Report generation tested</li><li>Test results logged and visible</li></ul> |
| **Output** | Quick regression safety net |
| **Gap Covered** | Prevent re-breakage |
| **Status** | Done — smoke tests (accounts/test_smoke.py, imaging/test_smoke.py) + CI (.github/workflows/ci.yml); verified locally 2026-08-19 (6/6 OK) |

## W1-T6: Contract freeze note
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 2 |
| **Coding Block** | Publish short API contract notes for all updated endpoints and fields. |
| **Acceptance Criteria** | <ul><li>API contract document created/updated</li><li>All modified endpoints documented with request/response schemas</li><li>Field mappings documented</li><li>Shared with team in repo or wiki</li></ul> |
| **Output** | Team alignment before Week 2 feature work |
| **Gap Covered** | Coordination risk |

---

# WEEK 2: Structured Diagnostic Report v1
**Goal:** Deliver complete report data model and submission validation.

## W2-T1: Diagnostic report schema extension
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 5 |
| **Coding Block** | Add required fields `Findings`, `Impression`, `Recommendation`, `Severity Classification` in model and migration. |
| **Acceptance Criteria** | <ul><li>Report model includes all four new fields</li><li>Database migration created and applied</li><li>Field types appropriately chosen (text, choices)</li><li>Model can be instantiated with new fields</li><li>Backwards compatible migration (nullable initially)</li></ul> |
| **Output** | Persisted structured report data |
| **Gap Covered** | Structured report missing |

## W2-T2: Report serializer validation rules
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 3 |
| **Coding Block** | Enforce required fields for final submission in serializer/form validation. |
| **Acceptance Criteria** | <ul><li>Serializer validates all four fields as required on submit</li><li>Validation error messages are clear</li><li>Draft saves allow empty fields</li><li>Final submit rejects empty required fields</li><li>Validation tested with unit tests</li></ul> |
| **Output** | Submission blocked on empty required fields |
| **Gap Covered** | Validation flow missing |

## W2-T3: Draft status workflow
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 3 |
| **Coding Block** | Add draft status state and save-draft endpoint behavior. |
| **Acceptance Criteria** | <ul><li>Report model has status field (draft/submitted)</li><li>Save-draft endpoint persists report in draft status</li><li>Draft reports do not trigger notifications</li><li>Submitted reports transition correctly</li><li>Status transitions validated and tested</li></ul> |
| **Output** | Reports can remain in progress |
| **Gap Covered** | Save draft missing |

## W2-T4: Frontend report form UX
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Build structured form sections with inline validation messages and save draft button. |
| **Acceptance Criteria** | <ul><li>Form displays four separate structured sections</li><li>Inline validation feedback shown in real-time</li><li>Save Draft button saves and shows success message</li><li>Submit button enforces required fields</li><li>Form UX tested for usability</li></ul> |
| **Output** | Usable report-writing interface |
| **Gap Covered** | Structured diagnostic submission UI |

## W2-T5: Annotation tool audit and backlog closure
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Confirm rectangle, freehand, circle, delete selected, undo; implement missing tools. |
| **Acceptance Criteria** | <ul><li>All five annotation tools implemented and functional</li><li>Rectangle tool draws boxes on canvas</li><li>Freehand tool draws strokes</li><li>Circle tool draws circles</li><li>Delete selected removes annotation</li><li>Undo restores last action</li><li>Tools tested with multiple annotations</li></ul> |
| **Output** | Complete annotation toolkit |
| **Gap Covered** | Annotation toolset incomplete |

## W2-T6: Test coverage for report flow
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Add backend tests for draft and submit paths; add frontend validation checks. |
| **Acceptance Criteria** | <ul><li>Backend tests for draft save endpoint</li><li>Backend tests for submit endpoint</li><li>Frontend tests for form validation</li><li>Coverage >= 80% for report-related code</li><li>All tests passing in CI</li></ul> |
| **Output** | Confidence for Week 3 integrations |
| **Gap Covered** | Regression prevention |

---

# WEEK 3: Review Workflow Safety and Notifications
**Goal:** Prevent reviewer conflicts and notify physicians after report submission.

## W3-T1: Review lock and concurrency check
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 5 |
| **Coding Block** | Add review session lock or active reviewer flag with timeout policy. |
| **Acceptance Criteria** | <ul><li>Review model includes active_reviewer and lock_timestamp fields</li><li>When radiologist opens case, lock is acquired</li><li>Lock expires after configurable timeout (e.g., 1 hour)</li><li>Concurrent review attempts detected and rejected</li><li>Lock behavior tested with concurrent access</li></ul> |
| **Output** | One active radiologist editor at a time |
| **Gap Covered** | Concurrency handling missing |

## W3-T2: Read-only fallback mode
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 3 |
| **Coding Block** | Display warning banner and open read-only review UI when conflict detected. |
| **Acceptance Criteria** | <ul><li>Warning banner appears when lock conflict detected</li><li>Warning includes active reviewer name and lock time</li><li>All annotation tools disabled in read-only mode</li><li>User can still view case and export</li><li>Read-only mode tested and confirmed</li></ul> |
| **Output** | Safe collaborative behavior |
| **Gap Covered** | Concurrency read-only UX missing |

## W3-T3: Notification model and endpoints
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 5 |
| **Coding Block** | Create notification entity, list endpoint, mark-read endpoint. |
| **Acceptance Criteria** | <ul><li>Notification model created with recipient, message, read_status fields</li><li>GET /api/notifications endpoint returns user's notifications</li><li>POST /api/notifications/{id}/mark-read updates status</li><li>Notifications persist and query correctly</li><li>Endpoints tested with postman/curl</li></ul> |
| **Output** | Notification backend foundation |
| **Gap Covered** | Notification center missing |

## W3-T4: Trigger on final report submission
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 3 |
| **Coding Block** | Emit physician-directed notification with patient and report link after successful submit. |
| **Acceptance Criteria** | <ul><li>On submit success, notification created for assigned physician</li><li>Notification includes patient name and case link</li><li>Notification persisted to DB</li><li>Physician can query and see notification</li><li>Behavior tested end-to-end</li></ul> |
| **Output** | Automatic report-ready alerts |
| **Gap Covered** | Physician notification missing |

## W3-T5: Notification center UI
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Add notification bell/list panel with unread badge and deep links. |
| **Acceptance Criteria** | <ul><li>Notification bell icon in header with unread count</li><li>Click bell opens notification list panel</li><li>List shows unread notifications with timestamps</li><li>Click notification navigates to case</li><li>Mark-as-read functionality works</li><li>Panel tested on desktop and mobile</li></ul> |
| **Output** | In-system alert surface |
| **Gap Covered** | Notification center |

## W3-T6: Integration tests for lock + notify
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Add tests for lock conflict and notification emission. |
| **Acceptance Criteria** | <ul><li>Test concurrent access to same case</li><li>Test lock conflict rejection</li><li>Test notification creation on submit</li><li>Test notification retrieval by physician</li><li>Tests cover race conditions</li><li>All tests passing</li></ul> |
| **Output** | Verified behavior under race conditions |
| **Gap Covered** | Reliability of new workflow |

---

# WEEK 4: AI and Image Quality Robustness + Physician Dashboard
**Goal:** Improve failure handling and complete physician role experience.

## W4-T1: AI failure state standardization
| Field | Value |
|-------|-------|
| **Owner** | Seth |
| **Story Points** | 5 |
| **Coding Block** | Define error states (timeout, unreachable, failed) and output contract consumed by backend. |
| **Acceptance Criteria** | <ul><li>AI service returns structured error objects with error_type and message</li><li>Error types: TIMEOUT, UNREACHABLE, FAILED clearly defined</li><li>Backend can parse and handle each error type</li><li>Error output documented and shared with team</li><li>Contract validated with backend developer</li></ul> |
| **Output** | Explicit AI failure semantics |
| **Gap Covered** | AI failure handling partial |

## W4-T2: Backend retry wrapper
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 5 |
| **Coding Block** | Add retry logic with capped attempts and fallback manual-only status update. |
| **Acceptance Criteria** | <ul><li>Retry wrapper retries AI calls up to 3 times on transient failures</li><li>Exponential backoff between retries</li><li>After max retries, mark case as manual-only</li><li>Logging captures all retry attempts</li><li>Retry behavior tested with mock AI failures</li></ul> |
| **Output** | More resilient inference pipeline |
| **Gap Covered** | Retry and unavailable path |

## W4-T3: Manual-review queue flagging
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Coding block** | Add queue status and alert marker when AI unavailable. |
| **Story Points** | 3 |
| **Acceptance Criteria** | <ul><li>Case shows "Manual Review Required" status when AI fails</li><li>Dashboard filter shows manual-only queue</li><li>Alert notification sent to radiologist team</li><li>Clear visual indicator in case list</li><li>Status correctly persisted and queryable</li></ul> |
| **Output** | Clear manual-only triage visibility |
| **Gap Covered** | Queue alert for manual review |

## W4-T4: Low-quality image confirmation flow
| Field | Value |
|-------|-------|
| **Owner** | Seth + Raimar |
| **Story Points** | 5 |
| **Coding Block** | Expose image quality signal and backend response requiring user confirmation or re-upload. |
| **Acceptance Criteria** | <ul><li>AI preprocessing returns quality score/signal</li><li>Backend detects low quality and returns explicit quality_check_failed response</li><li>Frontend prompts user to confirm or re-upload</li><li>Confirmed low-quality cases proceed with flag</li><li>Re-upload restarts preprocessing</li><li>Flow tested with edge-case images</li></ul> |
| **Output** | Standardization failure prompt path |
| **Gap Covered** | Low-quality prompt missing |

## W4-T5: Physician dashboard endpoint set
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 5 |
| **Coding Block** | Implement physician-specific summary endpoints for reviewed cases and alerts. |
| **Acceptance Criteria** | <ul><li>GET /api/physician/dashboard returns reviewed cases summary</li><li>Endpoint includes pending alerts and recent reports</li><li>Filtering by date/severity supported</li><li>Response schema documented</li><li>Endpoint tested with multiple data scenarios</li></ul> |
| **Output** | Role-specific data API |
| **Gap Covered** | Physician dashboard endpoint missing |

## W4-T6: Physician dashboard page
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Build physician dashboard UI with report access and alert cards. |
| **Acceptance Criteria** | <ul><li>Physician dashboard page created and routed</li><li>Display reviewed cases with status cards</li><li>Show alerts with patient name and report link</li><li>Filter/search by patient or date</li><li>Deep link to full case report</li><li>Dashboard accessible only to physician role</li></ul> |
| **Output** | Complete physician role surface |
| **Gap Covered** | Missing physician experience |

## W4-T7: Dev smoke script update
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Extend seed and smoke scripts to include physician flows and AI failure scenarios. |
| **Acceptance Criteria** | <ul><li>Seed script creates test physicians with sample cases</li><li>Smoke script tests physician dashboard endpoint</li><li>Smoke script simulates AI failure and retry</li><li>Script output clear and actionable</li><li>Script runs without errors on fresh environment</li></ul> |
| **Output** | Repeatable QA setup |
| **Gap Covered** | Demo reliability |

---

# WEEK 5: Longitudinal Progression Engine
**Goal:** Implement progression computation, trends, and manual override.

## W5-T1: Progression service core logic
| Field | Value |
|-------|-------|
| **Owner** | Seth |
| **Story Points** | 8 |
| **Coding Block** | Define delta rules for improvement, stable, deterioration from longitudinal records. |
| **Acceptance Criteria** | <ul><li>Progression service compares consecutive AI scores</li><li>Rules: improvement (score decrease), stable (within threshold), deterioration (score increase)</li><li>Threshold values documented and configurable</li><li>Service handles edge cases (no prior image, single image)</li><li>Logic documented and shared with team</li></ul> |
| **Output** | Deterministic progression classification |
| **Gap Covered** | Comparative progression tracking missing |

## W5-T2: Progression persistence and API
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 5 |
| **Coding Block** | Save progression status snapshots and expose trend endpoint. |
| **Acceptance Criteria** | <ul><li>ProgressionStatus model saves status snapshots per case</li><li>GET /api/cases/{id}/progression returns trend history</li><li>Response includes timestamps and status transitions</li><li>Endpoint pagination supported for long histories</li><li>Endpoint tested with multiple progression scenarios</li></ul> |
| **Output** | Queryable progression history |
| **Gap Covered** | No progression computation endpoint |

## W5-T3: Trend graph visualization
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Build patient trend chart component and status timeline tags. |
| **Acceptance Criteria** | <ul><li>Chart displays AI score trend over time</li><li>Timeline shows improvement/stable/deterioration status</li><li>Color coding: green (improvement), gray (stable), red (deterioration)</li><li>Hover tooltips show dates and scores</li><li>Responsive and readable on mobile</li></ul> |
| **Output** | Clinically readable progression UI |
| **Gap Covered** | Trend graph missing |

## W5-T4: Manual override workflow
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 5 |
| **Coding Block** | Add override endpoint with required clinical note and audit log entry. |
| **Acceptance Criteria** | <ul><li>POST /api/cases/{id}/progression/override accepts new status and clinical_note</li><li>clinical_note is required field, not empty</li><li>Override persisted with timestamp and radiologist ID</li><li>Audit log entry created automatically</li><li>Endpoint returns 400 if note empty</li></ul> |
| **Output** | Radiologist override with accountability |
| **Gap Covered** | Manual override missing |

## W5-T5: Override controls in UI
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 3 |
| **Coding Block** | Add override dropdown, required-note modal, and audit display. |
| **Acceptance Criteria** | <ul><li>Override dropdown shown in progression view</li><li>Click triggers modal with note input field</li><li>Note field marked as required with validation</li><li>Submit button calls override endpoint</li><li>Override history displayed below chart</li><li>User tested for clarity and ease-of-use</li></ul> |
| **Output** | End-to-end override function |
| **Gap Covered** | Manual override UI missing |

## W5-T6: Validation and edge-case tests
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Add tests for no-prior-image cases, conflicting deltas, override note requirement. |
| **Acceptance Criteria** | <ul><li>Test case with single image (no prior)</li><li>Test case with conflicting score changes</li><li>Test override submission without note (rejected)</li><li>Test override audit log creation</li><li>Test progression classification edge cases</li><li>Coverage >= 85% for progression module</li></ul> |
| **Output** | Safer progression feature rollout |
| **Gap Covered** | Reliability and correctness |

---

# WEEK 6: Consolidated Analytics, Export, and Hardening
**Goal:** Close reporting and non-functional gaps, then freeze for defense/demo stability.

## W6-T1: Consolidated analytics endpoint
| Field | Value |
|-------|-------|
| **Owner** | Lance |
| **Story Points** | 5 |
| **Coding Block** | Build date and severity parameterized aggregate endpoint. |
| **Acceptance Criteria** | <ul><li>GET /api/analytics/summary accepts date_from, date_to, severity params</li><li>Returns total cases, by severity, by status</li><li>Aggregate counts verified against raw data</li><li>Endpoint performance acceptable for large datasets</li><li>Schema documented and tested</li></ul> |
| **Output** | Aggregated counts and trend-ready payload |
| **Gap Covered** | Consolidated analytics missing |

## W6-T2: CSV and PDF aggregate export
| Field | Value |
|-------|-------|
| **Owner** | Raimar |
| **Story Points** | 5 |
| **Coding Block** | Implement export endpoints for consolidated report artifacts. |
| **Acceptance Criteria** | <ul><li>POST /api/analytics/export accepts format (csv/pdf) and filters</li><li>CSV includes headers and all relevant aggregate fields</li><li>PDF includes charts and summary tables</li><li>Exports are downloadable and correctly formatted</li><li>Export tested with various filter combinations</li></ul> |
| **Output** | Downloadable aggregate outputs |
| **Gap Covered** | Consolidated export endpoint missing |

## W6-T3: Analytics dashboard page
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 5 |
| **Coding Block** | Create charts/tables view for consolidated metrics with filter controls. |
| **Acceptance Criteria** | <ul><li>Analytics page displays aggregate counts with charts</li><li>Date range and severity filters functional</li><li>Charts include pie/bar graphs for case distribution</li><li>Export buttons for CSV and PDF</li><li>Page title and navigation clear</li><li>Mobile responsive design</li></ul> |
| **Output** | Module 4.3 visible and usable |
| **Gap Covered** | Reporting analytics UI |

## W6-T4: Security profile pass
| Field | Value |
|-------|-------|
| **Owner** | Brent + Dymes |
| **Story Points** | 5 |
| **Coding Block** | Add production-ready env profile checklist, DEBUG handling, CSRF trusted origins matrix, secrets hygiene checks. |
| **Acceptance Criteria** | <ul><li>Production .env profile created with DEBUG=False</li><li>CSRF_TRUSTED_ORIGINS configured appropriately</li><li>Secrets (API keys, DB passwords) never committed</li><li>.env.example created with placeholders</li><li>Security checklist document completed</li><li>No hardcoded secrets in codebase</li></ul> |
| **Output** | Deployment-grade baseline settings |
| **Gap Covered** | Security hardening partial |

## W6-T5: Automated backup script
| Field | Value |
|-------|-------|
| **Owner** | Brent |
| **Story Points** | 3 |
| **Coding Block** | Create scheduled backup script for DB and critical longitudinal records with restore test notes. |
| **Acceptance Criteria** | <ul><li>Backup script backs up PostgreSQL database</li><li>Backup script backs up uploaded images</li><li>Scheduling documented (daily/weekly recommended)</li><li>Restore procedure tested and documented</li><li>Backup integrity verified</li><li>Storage location and retention policy defined</li></ul> |
| **Output** | Evidence of backup reliability control |
| **Gap Covered** | Backup requirement missing |

## W6-T6: Placeholder module decision
| Field | Value |
|-------|-------|
| **Owner** | Dymes |
| **Story Points** | 2 |
| **Coding Block** | Either implement minimal pages for Appointments/Doctor/Messages/Settings or remove links to prevent dead navigation. |
| **Acceptance Criteria** | <ul><li>Decision made: implement or remove</li><li>If implement: minimal placeholder pages created</li><li>If remove: links removed from sidebar</li><li>Navigation tested for no dead links</li><li>Decision documented in PR</li></ul> |
| **Output** | Clean, intentional UX scope |
| **Gap Covered** | Sidebar scope drift |

## W6-T7: Final integration and release candidate
| Field | Value |
|-------|-------|
| **Owner** | All, coordinated by Dymes |
| **Story Points** | 8 |
| **Coding Block** | Full regression pass, demo data refresh, final bug bash, release tag. |
| **Acceptance Criteria** | <ul><li>All Week 1-5 features integrated and tested</li><li>Smoke script runs without errors</li><li>Demo data fresh and represents all user roles</li><li>No console errors or warnings</li><li>Final bug bash completed with no blockers</li><li>v1.0.0 release tag created on develop</li><li>Deployment ready</li></ul> |
| **Output** | Stable thesis demo candidate |
| **Gap Covered** | All gaps closed |

---

# Suggested Workload Per Week
1. **Dymes:** 2 frontend feature + 1 integration = ~12-15 story points/week
2. **Seth:** 1-2 AI critical = ~5-8 story points/week
3. **Lance:** 2 backend API = ~10-12 story points/week
4. **Raimar:** 2 backend API/integration = ~10-12 story points/week
5. **Brent:** 1 QA/CI + 1 reliability = ~6-8 story points/week

---

# Milestone Checkpoints
| Milestone | Target Completion | Status | Notes |
|-----------|------------------|--------|-------|
| **Week 2** | Structured diagnostic workflow fully operational | — | Report model, validation, draft save working |
| **Week 4** | Physician role and notification pipeline complete | — | Notifications, physician dashboard, AI failure handling verified |
| **Week 5** | Longitudinal progression engine complete | — | Progression service, trends, override working end-to-end |
| **Week 6** | Analytics/export and non-functional requirements complete | — | Security, backups, exports deployed; all gaps closed |
# TB-XR Codebase Summary (As of 2026-08-13)

## 1. High-Level Architecture (Plain English)

TB-XR is a role-based web platform for TB chest X-ray screening that runs as a local full-stack app:

- Backend: Django + Django REST Framework serves authentication, patient APIs, imaging workflows, AI integration, and report generation.
- Frontend: React (Vite) provides separate dashboard experiences for Radiologic Technologists and Radiologists.
- Data layer: Django models store users, patients, X-ray transactions, processed images, annotations, and AI outputs.
- AI layer: A PyTorch MobileNetV3-based inference script is loaded by backend imaging views at runtime for risk scoring and heatmap generation.
- Reporting layer: Django renders report HTML and calls a Node/Puppeteer script to export PDF reports.

In short: technologists upload and triage images, AI generates risk outputs, radiologists annotate/review, and completed cases can be exported as PDF.

## 2. Implemented System Flow

### End-to-end operational flow currently working in code

1. User logs in with session authentication and is redirected by role.
2. Technologist can register/search/select patients.
3. Technologist uploads JPG/PNG/DCM X-ray for a selected patient.
4. Backend validates upload, handles DICOM conversion/anonymization, applies preprocessing, and stores processed data.
5. Backend triggers AI inference immediately after upload and stores risk score + risk label + model version (+ heatmap when available).
6. Technologist sees uploaded records in patient history and dashboard queue.
7. Radiologist opens review queue, inspects image/heatmap, adds bounding boxes + diagnostic notes.
8. Annotation submission marks transaction as COMPLETED.
9. Completed cases can generate downloadable PDF reports.
10. Longitudinal panel supports viewing and comparing patient scan history.

## 3. Features That Look Fully Implemented

### Authentication and role control

- Session login/logout endpoints exist and are used by frontend login flow.
- Custom user role field and role-based access decorator are in place.
- Role-gated pages exist for technologist and radiologist dashboard routes.

### Patient management

- Register patient (technologist-only).
- List all patients.
- Search patients by name.
- Retrieve patient detail.

### Imaging pipeline and AI integration

- Upload endpoint supports .jpg/.jpeg/.png/.dcm and size validation.
- DICOM path includes anonymization and conversion handling.
- CLAHE enhancement and tensor preprocessing logic exist.
- AI inference is invoked from backend and persisted to AIResult model.
- Heatmap generation path exists via Grad-CAM script.
- Record status transitions are implemented (PENDING -> AI_REVIEWED -> COMPLETED).

### Radiologist workflow

- Queue endpoint with filters and pagination.
- Review page with interactive annotation canvas.
- Annotation create/update behavior exists.
- Existing annotation display for completed records exists.

### Historical review and reporting

- Patient history endpoint with chronological ordering.
- Longitudinal compare UI with dual-slot side-by-side viewing.
- PDF report endpoint implemented using template + Puppeteer script.

### Test coverage (backend)

- Accounts, patients, and imaging apps include meaningful tests (not empty placeholders).
- Tests cover access control, patient registration, dashboard visibility, annotation permission, AI result constraints, upload-triggered AI, and chronological history ordering.

## 4. Endpoints/Modules That Look Incomplete or Partially Complete

## A. Frontend navigation contains placeholder sections without routed pages

Sidebar includes links for:

- Appointments
- Doctor
- Messages
- Settings

But these routes are not defined in the main router, so those links currently lead to fallback behavior rather than real pages.

## B. Account dashboard placeholders exist in backend but are not core app pages

There are backend HTML placeholder dashboard view functions in the accounts app, but the real UI dashboards are React pages. These backend placeholders look like transitional scaffolding.

## C. Logout URL mismatch between frontend and backend

- Frontend logout calls: /api/accounts/logout/
- Backend logout route is: /accounts/logout/

This mismatch means server-side logout can fail while local frontend state still clears. Functional impact: user appears logged out in UI, but session invalidation may not be guaranteed.

## D. Report context has a likely field mismatch

Report generation code reads patient.gender, while patient model uses sex. This can cause sex value to appear as N/A in generated PDFs.

## E. Risk label filtering in UI is narrower than backend model choices

- Backend supports LOW, MODERATE, HIGH.
- Dashboard filter options currently expose only LOW and HIGH.

MODERATE records can exist but are not directly filterable in current table filters.

## F. Documentation drift

At least one implemented endpoint is not reflected consistently in endpoint docs (for example, report generation route visibility differs across docs vs code). The source code appears ahead of written endpoint documentation.

## G. Security/deployment maturity indicators

- DEBUG is hardcoded true in settings.
- CSRF trusted origins appear minimal for production scenarios.

This is acceptable for academic/dev stage but not production hardening.

## 5. Capability Map (Matrix)

### Legend

- Implemented: present and wired in code.
- Partial: exists but has known limitation or mismatch.
- Missing: no substantial implementation found.

| Capability | Primary Role | Frontend Module/Page | Backend Endpoint(s) | Status | Notes |
|---|---|---|---|---|---|
| Login with role redirect | Tech, Radiologist | src/components/login/LoginForm.jsx | POST /accounts/login/ | Implemented | Uses session auth + role redirect |
| Logout | Tech, Radiologist | src/context/AuthContext.jsx | POST /accounts/logout/ | Partial | Frontend currently calls /api/accounts/logout/ |
| CSRF bootstrap | All | src/components/login/LoginForm.jsx | GET /accounts/csrf-token/ | Implemented | Cookie-based CSRF flow |
| Role route protection | All | src/components/auth/RoleGuard.jsx | N/A (frontend guard) | Implemented | Enforces role page access client-side |
| Register patient | Technologist | src/components/patients/PatientForm.jsx | POST /api/patients/register/ | Implemented | Role restricted |
| List patients | Tech, Radiologist | src/components/patients/PatientTable.jsx | GET /api/patients/ | Implemented | Rendered in patient table |
| Search patients | Tech, Radiologist | src/components/patients/PatientTable.jsx | GET /api/patients/search/ | Implemented | Name query supported |
| Patient detail view | Tech, Radiologist | src/pages/PatientDetailPage.jsx | GET /api/patients/<id>/ | Implemented | Feeds profile + records |
| Upload X-ray | Technologist | src/components/upload/XrayUploadForm.jsx | POST /api/imaging/patients/<id>/xray/upload/ | Implemented | Accepts JPG/PNG/DCM |
| DICOM anonymization | Technologist workflow | N/A (server-side) | upload pipeline internals | Implemented | Sensitive DICOM tags stripped |
| Image preprocessing | Technologist workflow | N/A (server-side) | preprocess_xray + CLAHE path | Implemented | Produces normalized tensor |
| Auto AI inference on upload | Technologist workflow | Indirect in upload result views | Triggered by upload endpoint | Implemented | Stores AIResult and updates status |
| Re-run AI analysis | Technologist | Not prominent in UI | POST /api/imaging/xray/<id>/analyse/ | Implemented | Endpoint exists and tested |
| Technologist dashboard queue | Technologist | src/pages/dashboard/TechnologistDashboardPage.jsx | GET /api/imaging/dashboard/technologist/ | Implemented | Pagination + filters |
| Radiologist review queue | Radiologist | src/pages/dashboard/RadiologistDashboardPage.jsx | GET /api/imaging/queue/ | Implemented | Pagination + filters |
| X-ray detail retrieval | Tech, Radiologist | Multiple viewers and panels | GET /api/imaging/xray/<id>/ | Implemented | Includes annotations + AI |
| Patient X-ray record list | Tech, Radiologist | src/components/patients/XrayRecordList.jsx | GET /api/imaging/patients/<id>/xray/ | Implemented | Patient transaction history list |
| Longitudinal history feed | Tech, Radiologist | src/components/imaging/LongitudinalPanel.jsx | GET /api/imaging/patients/<id>/history/ | Implemented | Chronological ordering in API |
| Submit annotation | Radiologist | src/components/imaging/AnnotationPanel.jsx | POST /api/imaging/xray/<id>/annotate/ | Implemented | Creates/updates annotation |
| Completed status transition | Radiologist workflow | Indirect in UI | annotate endpoint logic | Implemented | Sets status to COMPLETED |
| Heatmap visualization | Tech, Radiologist | HeatmapViewer consumers | Included via AIResult heatmap_url | Implemented | Grad-CAM generation path exists |
| Static annotation overlay | Tech, Radiologist | StaticAnnotationOverlay components | Uses xray detail payload | Implemented | Works for completed records |
| PDF report generation | Radiologist (and tech view in some UI paths) | Window open actions in UI | GET /api/imaging/xray/<id>/report/ | Implemented | Only for COMPLETED records |
| Swagger/OpenAPI docs | Dev/Admin | Browser to /api/docs/ | GET /api/schema/, GET /api/docs/ | Implemented | Guarded by DEBUG/staff logic |
| Appointments module | Unknown | Sidebar link only | None found | Missing | Navigation placeholder |
| Doctor module | Unknown | Sidebar link only | None found | Missing | Navigation placeholder |
| Messages module | Unknown | Sidebar link only | None found | Missing | Navigation placeholder |
| Settings module | Unknown | Sidebar link only | None found | Missing | Navigation placeholder |

## 6. Suggested “Back from Break” Priority List

1. Fix frontend logout URL mismatch to guarantee server session invalidation.
2. Align report context field from patient.gender to patient.sex.
3. Add MODERATE option to dashboard risk filters.
4. Decide whether to remove or implement placeholder sidebar modules (Appointments/Doctor/Messages/Settings).
5. Reconcile endpoint documentation with current code (especially report endpoint and any newer query params).
6. Prepare a production-ready settings profile (DEBUG=false path, stricter allowed hosts/origins, secrets handling) for defense/demo hardening.

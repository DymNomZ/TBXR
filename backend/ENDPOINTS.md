# TBXR Backend Endpoints

Base URL (local dev): http://127.0.0.1:8000

## Auth and Roles
- Role access is enforced by the `role_required` decorator.
- Unauthorized roles receive HTTP 403.
- Session-based auth is supported (Django admin login + cookies).
- For session auth, include `sessionid` and matching `csrftoken`.

Required headers for session-authenticated POST requests:
- Cookie: csrftoken=<token>; sessionid=<token>
- X-CSRFToken: <token>
- Origin: http://127.0.0.1:8000
- Referer: http://127.0.0.1:8000/

## Admin
### GET /admin/login/
- Purpose: Admin login page to obtain session cookies.
- Auth: None
- Response: HTML

### POST /admin/login/
- Purpose: Login and obtain session cookie.
- Auth: None
- Headers:
  - Referer: http://127.0.0.1:8000/admin/login/
  - Cookie: csrftoken=<token>
- Body (x-www-form-urlencoded):
  - username
  - password
  - csrfmiddlewaretoken
- Response: 302 redirect to /admin/

## Accounts
### GET /accounts/csrf-token/
- Purpose: Set CSRF cookie for session-authenticated requests.
- Auth: None
- Response: 200 JSON

### POST /accounts/login/
- Purpose: Login and obtain session cookie.
- Auth: None
- Headers:
  - Content-Type: application/json
- Body (JSON):
  - username
  - password
- Response: 200 JSON

### POST /accounts/logout/
- Purpose: Logout and clear session.
- Auth: Session
- Response: 200 JSON

## Patients
### GET /api/patients/
- Purpose: List all patients.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Response: 200 JSON list

### POST /api/patients/register/
- Purpose: Create a patient.
- Roles: RADIOLOGIC_TECH
- Headers:
  - Content-Type: application/json
- Body (JSON):
  - first_name
  - last_name
  - date_of_birth (YYYY-MM-DD)
  - sex (M|F|O)
  - country_code (optional, ISO-3166-1 alpha-2; defaults to PH)
  - contact_number (accepts local or international input; stored as E.164)
- Response: 201 JSON (patient record), Location header points to detail URL

Example:
```
POST /api/patients/register/
Content-Type: application/json

{
  "first_name": "Test",
  "last_name": "Patient",
  "date_of_birth": "1990-01-01",
  "sex": "M",
  "country_code": "PH",
  "contact_number": "09171234567"
}
```

Notes:
- API responses format contact numbers using international display format (example: +63 917 123 4567).
- If contact input starts with `+`, parsing is country-agnostic.
- Invalid or too-short numbers (for example: `123`) are rejected with HTTP 400 validation errors.

### GET /api/patients/search/
- Purpose: Search patients by name or patient ID.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Query params:
  - name (optional, searches first or last name; a purely numeric value also matches the patient ID)
- Response: 200 JSON list

Examples:
```
GET /api/patients/search/?name=smith
GET /api/patients/search/?name=10
```

### GET /api/patients/<patient_id>/
- Purpose: Retrieve patient detail.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Response: 200 JSON

## Imaging
### POST /api/imaging/patients/<patient_id>/xray/upload/
- Purpose: Upload a raw X-ray file and create an XrayRecord.
- Roles: RADIOLOGIC_TECH
- Headers:
  - Content-Type: multipart/form-data
  - Cookie + X-CSRFToken (session auth)
- Body (multipart):
  - raw_image (file)
  - force_proceed (boolean, optional, default: false) - Bypass quality check
- Response: 200 JSON
- Side effects:
  - File saved to media/raw/
  - XrayRecord created with status PENDING (Pending Review)
  - AI inference runs automatically. If quality check fails and force_proceed is false, AI Result is not created and it returns a quality_check_failed response.
  - If successful, XrayRecord status updated to AI_REVIEWED

Example of quality check failed response:
```json
{
  "status": "quality_check_failed",
  "message": "Uploaded image may be too low quality for reliable AI interpretation.",
  "quality_score": 0.41,
  "requires_confirmation": true,
  "can_proceed": true,
  "transaction_id": "uuid"
}
```
*Note: To continue with a low quality image, the frontend should prompt the user and make a request to `POST /api/imaging/xray/<transaction_id>/analyse/` with `{"force_proceed": true}`.*

Example:
```
POST /api/imaging/patients/1/xray/upload/
Content-Type: multipart/form-data

raw_image=@/path/to/file.png
```

### GET /api/imaging/patients/<patient_id>/xray/
- Purpose: Get all uploaded xrays (transactions) of the patient.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Response: JSON

### GET /api/imaging/patients/<patient_id>/history/
- Purpose: Patient X-ray history ordered by upload timestamp (ascending), including AI result and annotations.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Response: 200 JSON list

### GET /api/imaging/patients/<patient_id>/xray/upload/confirm/<transaction_id>/
- Purpose: Confirm upload and return XrayRecord details.
- Roles: RADIOLOGIC_TECH
- Response: 200 JSON

### POST /api/imaging/xray/<transaction_id>/annotate/
- Purpose: Create or update a radiologist annotation for an X-ray.
- Roles: RADIOLOGIST
- Headers:
  - Content-Type: application/json
  - Cookie + X-CSRFToken (session auth)
- Body (JSON):
  - bounding_boxes (array, required)
  - notes (string, optional)
- Response: 200/201 JSON

### POST /api/imaging/xray/<transaction_id>/analyse/
- Purpose: Run AI inference on the processed image and store the AI result.
- Roles: RADIOLOGIC_TECH
- Notes: This runs automatically after upload, but can be called again to re-run. To bypass quality check failure on a previous upload, use `force_proceed`.
- Headers:
  - Content-Type: application/json
  - Cookie + X-CSRFToken (session auth)
- Body (JSON):
  - force_proceed (boolean, optional, default: false)
- Response: 200/201 JSON (AIResult)
- Side effects:
  - AIResult created/updated
  - XrayRecord status updated to AI_REVIEWED

Example response:
```
{
  "risk_score": 0.9231,
  "risk_label": "HIGH",
  "heatmap_url": "http://127.0.0.1:8000/media/heatmaps/TXN-2026-0041_heatmap.jpg",
  "model_version": "v1.0.0",
  "generated_at": "2026-04-19T10:22:00Z"
}
```

### GET /api/imaging/dashboard/technologist/
- Purpose: Paginated list of X-rays uploaded by the current technologist.
- Roles: RADIOLOGIC_TECH
- Query params (optional):
  - page
  - search (patient first/last name or transaction ID)
  - status (PENDING|IN_REVIEW|AI_REVIEWED|MANUAL_REVIEW|COMPLETED)
  - risk_label (LOW|MODERATE|HIGH)
- Response: 200 JSON (paginated)
```
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "transaction_id": "...",
      "patient": {
        "patient_id": "...",
        "first_name": "Juan",
        "last_name": "Dela Cruz"
      },
      "upload_timestamp": "...",
      "status": "PENDING",
      "file_format": "jpg"
    }
  ]
}
```

### GET /api/imaging/queue/
- Purpose: Radiologist queue of uploaded X-rays.
- Roles: RADIOLOGIST
- Query params (optional):
  - page
  - search (patient first/last name or transaction ID)
  - status (PENDING|IN_REVIEW|AI_REVIEWED|MANUAL_REVIEW|COMPLETED)
  - risk_label (LOW|MODERATE|HIGH)
- Response: 200 JSON (paginated)

### GET /api/physician/dashboard
- Purpose: Physician read-only clinical summary for finalized reports, pending alerts, and patient progress.
- Roles: PHYSICIAN
- Query params (optional):
  - severity (NORMAL|MILD|MODERATE|SEVERE|CRITICAL)
  - date_from (YYYY-MM-DD; filters finalized reports by report updated date)
  - date_to (YYYY-MM-DD; filters finalized reports by report updated date)
- Notes:
  - Source of truth is finalized radiologist outputs only (`Report.status=SUBMITTED`).
  - Pending alerts include only unread notifications for the authenticated physician.
- Response: 200 JSON
```json
{
  "filters": {
    "severity": "CRITICAL",
    "date_from": "2026-09-01",
    "date_to": "2026-09-06"
  },
  "summary": {
    "finalized_report_count": 3,
    "recent_report_count": 3,
    "pending_alert_count": 2,
    "report_ready_count": 3,
    "patient_progress_count": 2
  },
  "finalized_cases": [
    {
      "report_id": 41,
      "transaction_id": "uuid",
      "reported_at": "2026-09-06T07:21:00Z",
      "severity": "CRITICAL",
      "patient": {
        "patient_id": 12,
        "first_name": "Juan",
        "last_name": "Dela Cruz"
      },
      "radiologist": {
        "id": 3,
        "username": "rad.one",
        "first_name": "Maria",
        "last_name": "Santos"
      },
      "ai_result": {
        "risk_label": "HIGH",
        "risk_score": 0.92
      },
      "status": "COMPLETED"
    }
  ],
  "recent_reports": [],
  "report_ready_items": [],
  "pending_alerts": [
    {
      "id": 91,
      "message": "Report ready for Juan Dela Cruz (case uuid).",
      "read_status": false,
      "created_at": "2026-09-06T07:22:00Z",
      "updated_at": "2026-09-06T07:22:00Z"
    }
  ],
  "patient_progress": [
    {
      "patient": {
        "patient_id": 12,
        "first_name": "Juan",
        "last_name": "Dela Cruz"
      },
      "total_finalized_reports": 2,
      "latest_transaction_id": "uuid",
      "latest_reported_at": "2026-09-06T07:21:00Z",
      "latest_severity": "CRITICAL",
      "latest_status": "COMPLETED"
    }
  ]
}
```
- Error responses:
  - 400 when `severity` is invalid.
  - 400 when `date_from` or `date_to` format is invalid.
  - 400 when `date_from > date_to`.
  - 403 for non-physician roles.

### GET /api/imaging/physician/dashboard/
- Purpose: Imaging-scoped alias of physician dashboard endpoint for clients already using `/api/imaging` routes.
- Roles: PHYSICIAN
- Response: Same as `/api/physician/dashboard`.

### GET /api/imaging/xray/<transaction_id>/
- Purpose: Returns the xray details with annotations
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Notes: If another radiologist holds the review lock, returns 409 with the active reviewer and lock timestamp — clients should render read-only mode.
- Response: 200 JSON
```
{
  "transaction_id": "...",
  "patient": {
    "patient_id": "...",
    "first_name": "Juan",
    "last_name": "Dela Cruz"
  },
  "raw_image": "/media/raw/TXN-2026-0041.jpg",
  "upload_timestamp": "2026-04-18T08:14:00Z",
  "status": "PENDING",
  "file_format": "jpg",
  "annotations": [
    {
      "id": 1,
      "radiologist": {
        "id": 3,
        "first_name": "Maria",
        "last_name": "Santos",
        "username": "dr.santos"
      },
      "bounding_boxes": [
        { "x": 120, "y": 340, "width": 60, "height": 80, "label": "nodule" }
      ],
      "notes": "Suspicious opacity in right upper lobe.",
      "submitted_at": "2026-04-19T10:22:00Z"
    }
  ]
}
```

## Notifications
### GET /api/imaging/notifications/
- Purpose: List the authenticated user's notifications, newest first.
- Auth: Session (any role; returns only the caller's notifications)
- Response: 200 JSON list
```json
{
  "id": 91,
  "recipient": 4,
  "message": "Report ready for Juan Dela Cruz (case uuid).",
  "read_status": false,
  "created_at": "2026-09-06T07:22:00Z",
  "updated_at": "2026-09-06T07:22:00Z"
}
```

### POST /api/imaging/notifications/<notification_id>/mark-read/
- Purpose: Mark a notification as read.
- Auth: Session
- Headers: Cookie + X-CSRFToken (session auth)
- Response: 200 JSON (updated notification)

## Reports
### GET/POST/PATCH /api/imaging/xray/<transaction_id>/report/
- Purpose: Structured diagnostic report — read, save draft, or finalize.
- Roles: RADIOLOGIST
- Headers (POST/PATCH): Content-Type: application/json, Cookie + X-CSRFToken (session auth)
- Body (JSON):
  - findings (string)
  - impression (string)
  - recommendation (string)
  - severity (NORMAL|MILD|MODERATE|SEVERE|CRITICAL)
  - status (DRAFT|SUBMITTED)
- Notes:
  - POST always creates the report with status=DRAFT (empty fields allowed while drafting).
  - PATCH with status=SUBMITTED finalizes; all four fields are then required (400 with field errors otherwise).
  - Finalized (SUBMITTED) reports are immutable.
  - Final submission triggers a notification to the assigned physician.
- Response: 200/201 JSON (report record)

### GET /api/imaging/xray/<transaction_id>/report/generate/
- Purpose: Generate the PDF report for a COMPLETED X-ray.
- Roles: RADIOLOGIST
- Response: 200 PDF (attachment; filename tbxr_report_<transaction_id>.pdf)
- Side effects: Creates a minimal DRAFT report if none exists yet (see `documentation/refactored-SRS.md` limitation #16).
- Errors: 400 if the X-ray is not COMPLETED; 403 for non-radiologists; 404 if the record is missing.

## Progression
### GET /api/imaging/cases/<case_id>/progression/
- Purpose: Progression history for the case's patient (snapshots are refreshed first; paginated).
- Auth: Session (any role)
- Response: 200 JSON (paginated ProgressionStatus snapshots)

### GET /api/imaging/patients/<patient_id>/progression/
- Purpose: Progression history for a patient (snapshots are refreshed first; paginated).
- Auth: Session (any role)
- Response: 200 JSON (paginated)

### POST /api/imaging/cases/<case_id>/progression/override/
- Purpose: Radiologist manual override of the latest progression status.
- Roles: RADIOLOGIST
- Headers: Content-Type: application/json, Cookie + X-CSRFToken (session auth)
- Body (JSON):
  - status (no_prior|stable|decreased_risk|increased_risk)
  - clinical_note (required, non-empty)
- Side effects: Writes a ProgressionOverrideAuditLog entry.
- Response: 201 JSON (updated snapshot + audit_log_id)
- Errors: 400 if the clinical note is empty or the status is invalid; 404 if the case is missing.

## Analytics
### GET /api/analytics/summary/
- Purpose: Aggregate metrics — case totals by status and AI risk label, report totals by severity and status.
- Roles: RADIOLOGIST, PHYSICIAN
- Query params (optional):
  - date_from (YYYY-MM-DD, filters cases by upload date)
  - date_to (YYYY-MM-DD)
  - severity (NORMAL|MILD|MODERATE|SEVERE|CRITICAL, filters reports)
- Response: 200 JSON
- Errors: 400 for invalid dates/severity or date_from > date_to.

### GET /api/imaging/analytics/summary/
- Imaging-scoped alias of the analytics summary endpoint (same roles/params).

### POST /api/analytics/export/
- Purpose: Export the analytics summary as CSV or PDF.
- Roles: RADIOLOGIST, PHYSICIAN
- Headers: Content-Type: application/json, Cookie + X-CSRFToken (session auth)
- Body (JSON):
  - format (csv|pdf)
  - filters (optional: date_from, date_to, severity)
- Response: 200 file download (text/csv or application/pdf)

### POST /api/imaging/analytics/export/
- Imaging-scoped alias of the analytics export endpoint (same roles/body).

## API Docs
### GET /api/schema/
- Purpose: OpenAPI schema
- Access: Public in DEBUG, staff-only (HTTP 403 JSON) otherwise
- Response: JSON

### GET /api/docs/
- Purpose: Swagger UI
- Access: Public in DEBUG, staff-only (HTTP 403 JSON) otherwise
- Response: HTML

## Media Files (dev only)
- When DEBUG is true, uploaded files are served from:
  - /media/<path>
- Example: /media/raw/00000001_000.png

# TB-XR Week 1 Contract Freeze Notes

- Version: `W1-freeze-v1`
- Freeze Date: `2026-08-22`
- Scope: Week 1 tickets `W1-T1`, `W1-T2`, `W1-T3`, `W1-T4`
- Purpose: Lock API and field behavior before Week 2 feature expansion.

## 1) Auth Contract (W1-T1)

### Endpoint
- `POST /accounts/logout/`

### Request
- Auth: session cookie
- Header: `X-CSRFToken: <csrftoken>`
- Body: none

### Response
- `200 OK`
```json
{
  "detail": "Logged out."
}
```

### Notes
- `GET /accounts/logout/` is not supported and returns `405`.
- Frontend source uses this route constant: `frontend/src/context/AuthContext.jsx`.

## 2) Dashboard Severity Filter Contract (W1-T3)

### Endpoints
- `GET /api/imaging/dashboard/technologist/`
- `GET /api/imaging/queue/`

### Query Params
- `page` (optional)
- `search` (optional)
- `status` (optional): `PENDING | IN_REVIEW | AI_REVIEWED | COMPLETED`
- `risk_label` (optional): `LOW | MODERATE | HIGH`

### Example Requests
```http
GET /api/imaging/dashboard/technologist/?risk_label=MODERATE&page=1
```

```http
GET /api/imaging/queue/?risk_label=HIGH&status=AI_REVIEWED
```

### Response Shape (both endpoints)
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "transaction_id": "uuid",
      "patient": {
        "patient_id": 12,
        "first_name": "Juan",
        "last_name": "Dela Cruz"
      },
      "upload_timestamp": "2026-08-22T09:12:00Z",
      "status": "AI_REVIEWED",
      "file_format": "png",
      "ai_result": {
        "risk_score": 0.55,
        "risk_label": "MODERATE",
        "model_version": "v-test"
      }
    }
  ]
}
```

### Frontend Mapping
- Filter options must stay exactly: `LOW`, `MODERATE`, `HIGH`.
- Current sources:
  - `frontend/src/components/dashboard/TechnologistDashboardTable.jsx`
  - `frontend/src/components/dashboard/RadiologistDashboardTable.jsx`

## 3) Report Field Mapping Contract (W1-T2)

### Endpoint
- `GET /api/imaging/xray/<transaction_id>/report/`

### Field Mapping Freeze
- Report context field `patient_sex` must map from `patient.sex`.
- Deprecated/invalid mapping for report output: `patient.gender`.

### Canonical Behavior
- In report generation context:
```python
"patient_sex": getattr(patient, 'sex', 'N/A')
```

## 4) Clinical Disclaimer Contract (W1-T4)

### Canonical Text (do not drift)
`AI-generated assessments are assistive only and are not a definitive diagnosis. Final clinical decisions remain with licensed medical professionals.`

### Required Locations
- Dashboard/web app: reusable component in `frontend/src/components/ui/AIDisclaimer.jsx`.
- PDF report output: rendered in `backend/templates/reports/xray_report.html`.

### Rules
- Non-dismissible.
- Always visible in dashboard/report contexts.
- Role variants are out of scope for Week 1.

## 5) Week 1 Source-of-Truth Snapshot

- Contract detail index: `backend/ENDPOINTS.md`
- Week 1 freeze note (this file): `documentation/W1-CONTRACT-FREEZE-2026-08-22.md`

## 6) Verification Snapshot

- Logout smoke tests: `backend/apps/accounts/test_smoke.py`
- Severity filter parity test: `backend/apps/imaging/tests.py::ImagingAccessTests.test_radiologist_queue_filters_by_severity_levels`
- Report disclaimer test: `backend/apps/imaging/tests.py::ImagingAccessTests.test_report_template_includes_clinical_disclaimer`

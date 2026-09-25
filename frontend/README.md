# TBXR Frontend

React 19 + Vite 8 + Tailwind CSS v4 single-page app for the TB-XR teleradiology platform (technologist, radiologist, and physician dashboards).

## Development

```bash
npm install
npm run dev        # http://localhost:5173
```

The dev server proxies `/accounts` and `/api` to the backend at `http://localhost:8000` (see `vite.config.js`), so the backend must be running — see [`documentation/SETUP.md`](../documentation/SETUP.md).

## Testing

```bash
npm run test        # Vitest + Testing Library (single run; CI uses this)
npm run test:watch  # watch mode
npm run lint
```

## API Integration

Base URL (local dev): http://127.0.0.1:8000

Session auth (for POST requests):
- Cookie: `csrftoken=<token>; sessionid=<token>`
- X-CSRFToken: `<token>`
- Origin: http://127.0.0.1:8000
- Referer: http://127.0.0.1:8000/

Upload flow (server-triggered):
1. `POST /api/imaging/patients/<patient_id>/xray/upload/` (multipart `raw_image`) — may return `quality_check_failed`, which requires user confirmation via `analyse/` with `force_proceed`
2. `GET /api/imaging/xray/<transaction_id>/` (detail view)

Optional: `POST /api/imaging/xray/<transaction_id>/analyse/` to re-run AI inference.

### Core Endpoints

Auth:
- `GET /accounts/csrf-token/`
- `POST /accounts/login/`
- `POST /accounts/logout/`

Patients:
- `GET /api/patients/`
- `POST /api/patients/register/`
- `GET /api/patients/search/?name=<query>`
- `GET /api/patients/<patient_id>/`

Imaging:
- `POST /api/imaging/patients/<patient_id>/xray/upload/`
- `GET /api/imaging/patients/<patient_id>/xray/upload/confirm/<transaction_id>/`
- `POST /api/imaging/xray/<transaction_id>/analyse/`
- `GET /api/imaging/patients/<patient_id>/xray/`
- `GET /api/imaging/patients/<patient_id>/history/`
- `GET /api/imaging/dashboard/technologist/?page=&search=&status=&risk_label=`
- `GET /api/imaging/queue/?page=&search=&status=&risk_label=`
- `GET /api/imaging/xray/<transaction_id>/`
- `POST /api/imaging/xray/<transaction_id>/annotate/`

Reports & progression:
- `GET/POST/PATCH /api/imaging/xray/<transaction_id>/report/` (draft → submit)
- `GET /api/imaging/xray/<transaction_id>/report/generate/` (PDF)
- `GET /api/imaging/cases/<case_id>/progression/`
- `GET /api/imaging/patients/<patient_id>/progression/`
- `POST /api/imaging/cases/<case_id>/progression/override/` (radiologist; clinical note required)

Notifications:
- `GET /api/imaging/notifications/`
- `POST /api/imaging/notifications/<id>/mark-read/`

Dashboards & analytics:
- `GET /api/physician/dashboard` (physician-only)
- `GET /api/analytics/summary/` (radiologist/physician)
- `POST /api/analytics/export/` (csv/pdf)

Schema & docs:
- `GET /api/schema/`
- `GET /api/docs/`

For full request/response details, see [`backend/ENDPOINTS.md`](../backend/ENDPOINTS.md) and [`documentation/refactored-SRS.md`](../documentation/refactored-SRS.md) (Appendix B: full API catalog).

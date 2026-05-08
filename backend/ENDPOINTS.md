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

## Patients
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
  - contact_number
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
  "contact_number": "123"
}
```

### GET /api//patients/search/
- Purpose: Search patients by name.
- Roles: RADIOLOGIC_TECH, RADIOLOGIST, PHYSICIAN
- Query params:
  - name (optional, searches first or last name)
- Response: 200 JSON list

Example:
```
GET /patients/search/?name=smith
```

### GET /api//patients/<patient_id>/
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
- Response: 200 JSON
- Side effects:
  - File saved to media/raw/
  - XrayRecord created with status PENDING (Pending Review)

Example:
```
POST /api//imaging/patients/1/xray/upload/
Content-Type: multipart/form-data

raw_image=@/path/to/file.png
```

### GET /api/imaging/patients/<patient_id>/xray/
- Purpose: Get all uploaded xrays (transactions) of the patient.
- Roles: ALL
- Response: JSON

### GET /api/imaging/patients/<patient_id>/xray/upload/confirm/<transaction_id>/
- Purpose: Confirm upload and return XrayRecord details.
- Roles: RADIOLOGIC_TECH
- Response: 200 JSON

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

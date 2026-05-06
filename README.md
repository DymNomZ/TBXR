# TB-XR
**A collaborative, AI-integrated teleradiology platform for Pulmonary Tuberculosis screening.**

Team: `2526-sem2-cs342-06`
Members: Borgonia, J.D. · Emia, S.N. · Enario, L.J.L. · Epan, R.S. · Tolentino, B.M.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + Django REST Framework |
| Frontend | React 18+ (via Vite) |
| Database | PostgreSQL |
| AI/ML | PyTorch + MobileNetV3 |
| Image Processing | Pillow, pydicom, opencv-python |
| Auth | Django Session Auth (MVP) |

---

## Week 1 — Increment 1: X-ray Ingestion & Data Management

Track progress by checking off tasks below.

---

### Step 2 — Database Schema & Models

- [x] Create Django apps: `accounts`, `patients`, `imaging`
  ```bash
  python manage.py startapp accounts
  python manage.py startapp patients
  python manage.py startapp imaging
  ```
- [x] `accounts/models.py` — Custom `User` model extending `AbstractUser`
  - Fields: `role` (choices: `RADIOLOGIC_TECH`, `RADIOLOGIST`, `PHYSICIAN`)
- [x] `patients/models.py` — `Patient` model
  - Fields: `patient_id` (auto), `first_name`, `last_name`, `date_of_birth`, `sex`, `contact_number`, `date_created`
- [x] `imaging/models.py` — `XrayRecord` and `ProcessedImage` models
  - `XrayRecord`: `transaction_id` (UUID, auto), `patient` (FK), `raw_image`, `upload_timestamp`, `status` (Pending/In Review/Completed), `uploader` (FK to User), `file_format`
  - `ProcessedImage`: `xray_record` (OneToOne), `processed_image`, `preprocessing_metadata` (JSON)
- [x] Register models in `settings.py` under `INSTALLED_APPS`
- [x] Run `python manage.py makemigrations` and `python manage.py migrate`

---

### Step 3 — Authentication & RBAC

- [x] Configure Django's auth backend in `settings.py`
- [x] Create login view and template/page
- [x] Create logout endpoint
- [x] Implement role-based redirect after login:
  - `RADIOLOGIC_TECH` → Technologist Dashboard
  - `RADIOLOGIST` → Radiologist Dashboard (placeholder for now)
  - `PHYSICIAN` → Physician Dashboard (placeholder for now)
- [x] Add `@login_required` and role permission decorators/mixins to protected views
- [x] Seed test accounts for all three roles via `manage.py createsuperuser` or a seed script

---

### Step 4 — Patient Profile Module

- [x] `patients/views.py` — CRUD views: create patient, search patient, view patient detail
- [x] Patient creation form with field validation
- [x] Patient search by name or patient ID
- [x] Patient detail page showing basic info and (empty) upload history list
- [ ] Wire up URLs in `patients/urls.py` and include in root `urls.py`

---

### Step 5 — X-ray Upload & File Validation

- [ ] `imaging/views.py` — Upload view linked to a selected patient
- [ ] Upload form: file picker + patient selector
- [ ] Backend validation:
  - [ ] Accept: `.jpg`, `.jpeg`, `.png`, `.dcm` only — reject all others with an error response
  - [ ] File size limit: max 20MB
- [ ] For `.dcm` (DICOM) files: use `pydicom` to read and convert pixel data to PNG for storage and display; keep original file
- [ ] Return descriptive error messages for rejected uploads

---

### Step 6 — Image Standardization Pipeline

- [ ] Create `imaging/preprocessing.py` as a standalone utility module
- [ ] Pipeline function that runs on every accepted upload:
  - [ ] Resize to 224×224 (match Seth's model input exactly)
  - [ ] Convert to grayscale then back to 3-channel RGB
  - [ ] Apply CLAHE contrast enhancement (`cv2.createCLAHE` or `PIL.ImageOps.equalize`)
  - [ ] Save processed image to a separate `processed/` media subfolder
- [ ] Link processed image to `ProcessedImage` model and save preprocessing metadata as JSON
- [ ] Call this pipeline automatically inside the upload view after validation passes

---

### Step 7 — Transaction ID & Upload Confirmation

- [x] `transaction_id` auto-generated as UUID on `XrayRecord` creation (use `uuid.uuid4`)
- [x] After successful upload, redirect to a confirmation page showing:
  - Transaction ID
  - Patient name
  - Upload timestamp
  - Current status: "Pending Review"
- [x] Add toast/banner notification on success (or a styled confirmation card)

---

### Step 8 — Technologist Dashboard

- [ ] Dashboard view for `RADIOLOGIC_TECH` role
- [ ] Table listing all `XrayRecord` entries uploaded by the logged-in user
- [ ] Columns: Transaction ID · Patient Name · Upload Date · Status
- [ ] Basic pagination or limit to last 20 records for MVP
- [ ] Each row links to the upload confirmation/detail page

---

## Week 2 — Increment 2: Radiologist Annotation Module
*(Tasks to be added)*

## Week 3 — Increment 3: AI Integration & Longitudinal Monitoring
*(Tasks to be added)*

## Week 4 — Increment 4: Role-Based Dashboards & Reporting
*(Tasks to be added)*

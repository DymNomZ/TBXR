# TB-XR

## Project Description
TB-XR is a collaborative, AI-integrated teleradiology platform for pulmonary tuberculosis screening. It combines a Django backend, React frontend, and an AI inference pipeline to support chest X-ray upload, analysis, and report workflows for clinical users.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + Django REST Framework |
| Frontend | React 18+ (via Vite) |
| Database | PostgreSQL (production), SQLite (local fallback) |
| AI/ML | PyTorch + MobileNetV3 |
| Image Processing | Pillow, pydicom, opencv-python |
| Authentication | Django Session Authentication |

## Setup / Installation
### 1. Clone Repository
```bash
git clone <repo-url>
cd TBXR
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://localhost:8000`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### 4. AI Environment Setup (Optional for model scripts)
```bash
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables (Names Only)
- DJANGO_ENV
- DEBUG
- SECRET_KEY
- ALLOWED_HOSTS
- CSRF_TRUSTED_ORIGINS
- SESSION_COOKIE_SECURE
- CSRF_COOKIE_SECURE
- SECURE_SSL_REDIRECT
- USE_X_FORWARDED_PROTO
- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_HOST
- DB_PORT
- PROGRESSION_STABLE_THRESHOLD
- REVIEW_LOCK_TIMEOUT_MINUTES
- SESSION_COOKIE_SAMESITE
- CSRF_COOKIE_SAMESITE
- SECURE_REFERRER_POLICY
- X_FRAME_OPTIONS
- SECURE_HSTS_SECONDS
- SECURE_HSTS_INCLUDE_SUBDOMAINS
- SECURE_HSTS_PRELOAD
- BACKUP_DIR
- BACKUP_RETENTION_COUNT
- SEED_DEFAULT_PASSWORD

## Deployed URL
https://tbxrdev.dymierborgonia.com
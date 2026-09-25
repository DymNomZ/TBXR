# TB-XR
**A collaborative, AI-integrated teleradiology platform for Pulmonary Tuberculosis screening.**

Team: `2526-sem2-cs342-06`
Members: Borgonia, J.D. · Emia, S.N. · Enario, L.J.L. · Epan, R.S. · Tolentino, B.M.

---

## Team Roles

### Tech Lead
**Assigned to:** Dymes

Owns the overall technical direction of the project. Works across all layers of the stack — backend, frontend, database, and integration — without being locked to any one area. Reviews and approves all PRs before they merge into `develop`. Makes architectural decisions (folder structure, naming conventions, how modules connect). Writes and maintains shared config: project setup, environment variables, root URL routing, database schema design.

*Without this role, five people make five different structural decisions that don't fit together. The Tech Lead is the single source of truth for how the codebase is organized and how all the pieces connect.*

### AI Engineer
**Assigned to:** Seth

Owns everything inside `ai/`. Responsible for dataset management, model architecture, training pipeline, evaluation metrics, and the final inference script that the rest of the backend calls. Produces the trained model weights and preprocessing spec that the backend consumes.

*The CNN risk score is the core research contribution of the thesis. This role carries the academic weight behind the system's intelligence.*

### Frontend Developer
**Assigned to:** Dymes

Owns everything inside `frontend/`. Responsible for all pages, components, and user-facing flows. Writes the Axios service calls that connect the UI to the backend API. Ensures the interface is intuitive for non-technical medical staff across all three user roles.

*The System Usability Scale (SUS) is one of the project's defined validation metrics. The frontend is what gets evaluated in that test.*

### Backend Developer
**Assigned to:** Lance, Raimar

Owns the Django app-level code inside `backend/`. Responsible for views, API endpoints, form validation, file I/O, and the image preprocessing pipeline. Works from the database schema defined by the Tech Lead and exposes the endpoints consumed by the frontend.

*All data flowing through the system — uploads, patient records, annotations, AI results — passes through this role's code. This role is the connective tissue between the database, the AI layer, and the UI.*

### DevOps Engineer
**Assigned to:** Brent

Owns the development environment, Git workflow, and quality assurance. Maintains `.gitignore`, `requirements.txt`, `.env.example`, and seed scripts. Writes and runs tests. Performs a "fresh machine" walkthrough before every demo to catch integration failures. In later semesters, owns the deployment configuration and the SUS evaluation setup.

*This role exists to ensure the project is reproducible, testable, and presentable on any machine at any time — not just the one it was last developed on.*

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

## Branch Naming Convention

| Branch | Purpose |
|--------|---------|
| `main` | Stable, demo-ready code only. Never commit directly here. |
| `develop` | Integration branch. All feature branches merge here first. |
| `feature/<initials>/<short-description>` | New feature work |
| `fix/<short-description>` | Bug fixes |
| `hotfix/<short-description>` | Urgent fixes on `main` |

**Examples:**
```
feature/jd/database-schema
feature/sn/mobilenetv3-training
feature/ljl/patient-profile-ui
feature/rs/image-validation
feature/bm/auth-login
fix/upload-form-validation
```

**Workflow:**
1. Always branch off `develop`, never off `main`
2. Keep branches focused — one feature per branch
3. Open a Pull Request into `develop` when done
4. Tag the relevant person to review before merging
5. `main` only gets merged into at the end of each week's increment when everything is working

---

## Commit Message Convention
 
```
<type>(<scope>): <short description> #<issue-number>
```
 
| Type | When to use |
|------|------------|
| `feat` | Adding new functionality |
| `fix` | Fixing a bug |
| `chore` | Setup, config, dependencies — no production code change |
| `refactor` | Restructuring existing code without changing behavior |
| `docs` | Documentation changes only |
| `test` | Adding or updating tests |
 
**Scope** is the app or area of the codebase being touched: `accounts`, `patients`, `imaging`, `frontend`, `ai`, `db`, `auth`.
 
**Examples:**
```
feat(imaging): add file type validation on upload #7
feat(patients): implement patient search by name and ID #10
fix(auth): redirect loop on radiologist login #5
chore(db): add ProcessedImage model and run migrations #3
refactor(imaging): extract DICOM conversion into utility function #12
docs(ai): add preprocessing spec document #14
feat(frontend): build static upload confirmation page #17
```
 
> **Note:** The `#issue-number` at the end automatically links the commit to its GitHub issue. The commit will appear in the issue's timeline, making it easy to trace exactly which commits closed which issue.

## Getting Started

Setup instructions for the backend, frontend, AI environment, SUS testing database,
and backup/restore live in [`documentation/SETUP.md`](documentation/SETUP.md).

Quick summary:

```bash
# Backend (Django + DRF)
cd backend
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver                    # http://localhost:8000

# Frontend (React + Vite)
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

---

## Documentation

All project documents live in the [`documentation/`](documentation) directory:

| Document | File |
|----------|------|
| Software Proposal | [`documentation/Software Proposal.md`](documentation/Software%20Proposal.md) |
| Software Requirements Specification | [`documentation/SRS.md`](documentation/SRS.md) · [`documentation/refactored-SRS.md`](documentation/refactored-SRS.md) |
| Software Design Description | [`documentation/SDD.md`](documentation/SDD.md) |
| Setup guide | [`documentation/SETUP.md`](documentation/SETUP.md) |
| Team coding standards | [`documentation/CODING-STANDARDS.md`](documentation/CODING-STANDARDS.md) |
| Week 1 API contract freeze | [`documentation/W1-CONTRACT-FREEZE-2026-08-22.md`](documentation/W1-CONTRACT-FREEZE-2026-08-22.md) |
| Security & environment profile | [`documentation/SECURITY-ENV-PROFILE.md`](documentation/SECURITY-ENV-PROFILE.md) |
| Backup & restore runbook | [`documentation/backup-restore.md`](documentation/backup-restore.md) |
| Smoke test run guide | [`documentation/SMOKE_TEST_RUN_STEPS.md`](documentation/SMOKE_TEST_RUN_STEPS.md) |
| 6-week sprint board | [`documentation/SIX-WEEK-SPRINT.md`](documentation/SIX-WEEK-SPRINT.md) |
| Gap checklist (SRS/SDD vs code) | [`documentation/GAP-CHECKLIST-SRS-SDD-vs-code.md`](documentation/GAP-CHECKLIST-SRS-SDD-vs-code.md) |
| Clinical validation & hospital partnership roadmap | [`documentation/VALIDATION-ROADMAP.md`](documentation/VALIDATION-ROADMAP.md) |
| Progression service spec | [`documentation/progression-service.md`](documentation/progression-service.md) |

Backend API endpoint reference: [`backend/ENDPOINTS.md`](backend/ENDPOINTS.md)
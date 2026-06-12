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
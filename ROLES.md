# TB-XR — Team Roles

---

## Tech Lead
**Assigned to:** Dymes

**What:** Owns the overall technical direction of the project. Works across all layers of the stack — backend, frontend, database, and integration — without being locked to any one area. Reviews and approves all PRs before they merge into `develop`. Makes architectural decisions (folder structure, naming conventions, how modules connect). Writes and maintains shared config: project setup, environment variables, root URL routing, database schema design.

**Why:** Without this role, five people make five different structural decisions that don't fit together. The Tech Lead is the single source of truth for how the codebase is organized and how all the pieces connect. Every module another member builds ultimately gets integrated by or through this role.

---

## AI Engineer
**Assigned to:**

**What:** Owns everything inside `ai/`. Responsible for dataset management, model architecture, training pipeline, evaluation metrics, and the final inference script that the rest of the backend calls. Produces the trained model weights and preprocessing spec that the backend consumes.

**Why:** The CNN risk score is the core research contribution of the thesis. This role carries the academic weight behind the system's intelligence. No other role can substitute for it — the work requires deep familiarity with the training pipeline, the data, and the model's behavior across different inputs.

---

## Frontend Developer
**Assigned to:**

**What:** Owns everything inside `frontend/`. Responsible for all pages, components, and user-facing flows. Writes the Axios service calls that connect the UI to the backend API. Ensures the interface is intuitive for non-technical medical staff across all three user roles.

**Why:** The System Usability Scale (SUS) is one of the project's defined validation metrics. The frontend is what gets evaluated in that test. A functionally correct backend with a confusing interface is a thesis that fails its own usability criteria.

---

## Backend Developer
**What:** Owns the Django app-level code inside `backend/`. Responsible for views, API endpoints, form validation, file I/O, and the image preprocessing pipeline. Works from the database schema defined by the Tech Lead and exposes the endpoints consumed by the frontend.

**Why:** All data flowing through the system — uploads, patient records, annotations, AI results — passes through this role's code. Incorrect preprocessing at this layer corrupts the model's input; broken API contracts block the frontend. This role is the connective tissue between the database, the AI layer, and the UI.

---

## DevOps Engineer
**What:** Owns the development environment, Git workflow, and quality assurance. Maintains `.gitignore`, `requirements.txt`, `.env.example`, and seed scripts. Writes and runs tests. Performs a "fresh machine" walkthrough from `DEMO.md` before every demo to catch integration failures. In later semesters, owns deployment configuration and the SUS evaluation setup.

**Why:** Without this role, "it works on my machine" becomes the team's most common phrase the night before a demo. This role exists to ensure the project is reproducible, testable, and presentable on any machine at any time — not just the one it was last developed on.

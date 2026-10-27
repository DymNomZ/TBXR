# 

## **CEBU INSTITUTE OF TECHNOLOGY**

**UNIVERSITY**

COLLEGE OF COMPUTER STUDIES

# 

# **Software Requirements Specification**

## *for*

## TB-XR

**Change History**

| Version | Date | Authors | Description of Revision |
| :---- | :---- | :---- | :---- |
| 1.0 | April 18, 2026 | Borgonia, J.D.; Emia, S.N.; Enario, L.J.L.; Epan, R.S.; Tolentino, B. | Initial Release SRS for TB-XR |
| 2.0 | September 25, 2026 | Borgonia, J.D.; Emia, S.N.; Enario, L.J.L.; Epan, R.S.; Tolentino, B. | Refactored to describe the as-built system (session auth, quality gate, review locking, structured reports, notifications, progression engine with override, physician/analytics dashboards, backup/restore, security profile). |

> **About this revision.** This document supersedes `documentation/SRS.md` (v1.0). It is grounded in the current source tree of `TBXR/` and reflects implemented behaviour. Where the system specifies a *target* that is not yet measured or built, it is explicitly labelled **Target** or **Planned**. Requirements are traceable to endpoints and files in Section 8.

**Table of Contents**

1. [Introduction](#1-introduction)
   1. [Purpose](#11-purpose)
   2. [Scope](#12-scope)
   3. [Definitions, Acronyms, and Abbreviations](#13-definitions-acronyms-and-abbreviations)
   4. [References](#14-references)
   5. [Document Conventions](#15-document-conventions)
2. [Overall Description](#2-overall-description)
   1. [Product Perspective](#21-product-perspective)
   2. [Product Functions](#22-product-functions)
   3. [User Classes and Characteristics](#23-user-classes-and-characteristics)
   4. [Operating Environment](#24-operating-environment)
   5. [Design and Implementation Constraints](#25-design-and-implementation-constraints)
   6. [Assumptions and Dependencies](#26-assumptions-and-dependencies)
3. [External Interface Requirements](#3-external-interface-requirements)
   1. [User Interfaces](#31-user-interfaces)
   2. [Hardware Interfaces](#32-hardware-interfaces)
   3. [Software Interfaces](#33-software-interfaces)
   4. [Communications Interfaces](#34-communications-interfaces)
4. [System Features (Functional Requirements)](#4-system-features-functional-requirements)
   1. [Module 1: X-ray Ingestion and Data Management](#41-module-1-x-ray-ingestion-and-data-management)
   2. [Module 2: Annotation and Diagnostic Review](#42-module-2-annotation-and-diagnostic-review)
   3. [Module 3: AI Engine and Longitudinal Monitoring](#43-module-3-ai-engine-and-longitudinal-monitoring)
   4. [Module 4: Clinical Dashboards and Reporting](#44-module-4-clinical-dashboards-and-reporting)
   5. [Cross-cutting: Status Lifecycles](#45-cross-cutting-status-lifecycles)
   6. [Cross-cutting: Role-Based Access Control Matrix](#46-cross-cutting-role-based-access-control-matrix)
5. [Data Requirements](#5-data-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
   1. [Performance](#61-performance)
   2. [Security and Privacy](#62-security-and-privacy)
   3. [Reliability and Availability](#63-reliability-and-availability)
   4. [Usability](#64-usability)
   5. [Maintainability and Testability](#65-maintainability-and-testability)
   6. [Regulatory and Ethical Compliance](#66-regulatory-and-ethical-compliance)
7. [Known Limitations and Future Work](#7-known-limitations-and-future-work)
8. [Appendix A: Traceability Matrix](#appendix-a-traceability-matrix)
9. [Appendix B: API Endpoint Catalog](#appendix-b-api-endpoint-catalog)

---

# 1. Introduction

## 1.1 Purpose

This document specifies the functional and non-functional requirements of **TB-XR**, a collaborative, AI-integrated teleradiology platform for pulmonary tuberculosis (TB) screening. It is intended for developers, project managers, clinical stakeholders, and thesis evaluators, and it is written to align with the structure recommended by IEEE Std 830-1998.

Unlike the original specification, this revision describes the system **as currently implemented** in the repository, and distinguishes clearly between implemented behaviour and aspirational targets.

## 1.2 Scope

TB-XR is a role-based, web-based clinical decision support platform that supports an end-to-end TB chest X-ray screening workflow: secure image ingestion, automated standardization, AI-assisted risk triage, human-in-the-loop annotation and structured diagnostic reporting, longitudinal progression monitoring, and role-specific dashboards with consolidated analytics.

The system is organized into four modules:

- **Module 1 — X-ray Ingestion and Data Management**: upload of chest X-rays with patient metadata, DICOM conversion and de-identification, contrast standardization, image quality gating, and centralized patient profiling.
- **Module 2 — Annotation and Diagnostic Review**: remote review queue, concurrency-safe review sessions, interactive annotation, and structured diagnostic report composition/submission.
- **Module 3 — AI Engine and Longitudinal Monitoring**: CNN baseline risk scoring with explainability heatmaps, historical record retrieval, comparative progression tracking, manual progression override, and comprehensive PDF report generation.
- **Module 4 — Clinical Dashboards and Reporting**: authentication and RBAC, role-specific dashboards, in-system notifications, and consolidated analytics with CSV/PDF export.

**In scope (implemented):** secure session-authenticated login and logout; patient registration/search/detail; JPG/PNG/DCM upload with de-identification and preprocessing; automated AI risk scoring and Grad-CAM heatmap generation; radiologist review queue, review locking, and annotation; structured diagnostic reports with draft/submit lifecycle; physician notification and physician dashboard; progression computation with trend data and manual override; per-case and consolidated report export (PDF/CSV); analytics summary; automated backup and restore tooling.

**Out of scope (boundaries):**

- **Direct PACS/DICOM network integration** — images are uploaded manually as files; the system does not route over DICOM network protocols.
- **Autonomous diagnosis / chart signing** — the AI engine emits an informational risk score only; final diagnostic authority remains with authenticated human Radiologists and Physicians.
- **Definitive multi-disease diagnosis** — the AI component is a generalized risk triage tool and does not issue differentiated diagnoses for non-TB pathologies.
- **Pharmaceutical or treatment workflows** — no prescription, medication compliance, or appointment scheduling logic.
- **Model training pipeline** — training occurs offline in `ai/notebooks/`; the deployed system only performs inference.
- **Regulatory certification** (e.g., FDA, DOH) and full hospital information system (HIS) integration.

## 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
| :---- | :---- |
| **AI** | Artificial Intelligence. |
| **AUC-ROC** | Area Under the Receiver Operating Characteristic Curve; a measure of a classifier's discriminative ability. |
| **CAD** | Computer-Aided Detection/Diagnosis. |
| **CLAHE** | Contrast Limited Adaptive Histogram Equalization; the contrast-enhancement step applied during standardization. |
| **CNN** | Convolutional Neural Network; here, a MobileNetV3-Large binary classifier. |
| **CSRF** | Cross-Site Request Forgery; the system uses Django's CSRF cookie/header protection. |
| **CXR** | Chest X-Ray. |
| **DICOM** | Digital Imaging and Communications in Medicine. |
| **DRF** | Django REST Framework. |
| **Grad-CAM** | Gradient-weighted Class Activation Mapping; produces the saliency heatmap overlay. |
| **HITL** | Human-in-the-loop; the workflow model requiring human clinical verification of AI output. |
| **LAN** | Local Area Network. |
| **MRN** | Medical Record Number (display-only placeholder; not a persisted Patient field). |
| **PACS** | Picture Archiving and Communication System. |
| **PHI/PII** | Protected Health Information / Personally Identifiable Information. |
| **RBAC** | Role-Based Access Control. |
| **SRS** | Software Requirements Specification. |
| **SUS** | System Usability Scale. |
| **TB** | Tuberculosis. |
| **TB-XR** | The collaborative teleradiology platform specified herein. |
| **UUID** | Universally Unique Identifier; used for X-ray transaction IDs. |

## 1.4 References

**Standards**
- IEEE Std 830-1998, *IEEE Recommended Practice for Software Requirements Specifications*.
- IEEE Std 1016-2009, *IEEE Standard for Information Technology — Systems Design — Software Design Descriptions*.

**Academic and clinical**
- T. Rahman et al., "Reliable Tuberculosis Detection Using Chest X-Ray With Deep Learning, Segmentation and Visualization," *IEEE Access*, vol. 8, pp. 191586–191601, 2020, doi: 10.1109/ACCESS.2020.3031384.
- Hansun et al., 2023. "Machine and Deep Learning for Tuberculosis Detection on Chest X-Rays: Systematic Literature Review." *Journal of Medical Internet Research*.
- Nampewo et al., 2024. "Benefits of Artificial Intelligence versus Human-Reader in Chest X-Ray Screening for Tuberculosis in the Philippines." *International Journal of Health Sciences and Research*.
- Teo et al., 2021. "Duration and Determinants of Delayed Tuberculosis Diagnosis and Treatment in High-Burden Countries: A Mixed-Methods Systematic Review and Meta-Analysis." *Respiratory Research*.
- Philippine Data Privacy Act of 2012 (Republic Act No. 10173).

**Project documents**
- `documentation/SDD.md` — Software Design Description.
- `backend/ENDPOINTS.md` — backend endpoint source of truth.
- `backend/TBXR/settings.py`, `backend/.env.example`, `backend/.env.production.example` — configuration.
- `documentation/W1-CONTRACT-FREEZE-2026-08-22.md` — frozen API/auth/disclaimer contracts.
- `documentation/SECURITY-ENV-PROFILE.md` — production security profile.
- `documentation/backup-restore.md` — backup and restore runbook.
- `documentation/progression-service.md` — progression rule engine specification.
- `documentation/CODING-STANDARDS.md` — team coding standards.
- `ai/model_resources/MODEL_PERFORMANCE.md`, `INFO.md`, `USAGE.md`, `QUALITY_CHECK.md`, `ai/notebooks/PREPROCESS_SPEC.md` — model assets and preprocessing contract.
- `documentation/Software Proposal.md`, `documentation/VALIDATION-ROADMAP.md`, `documentation/SIX-WEEK-SPRINT.md` — proposal, validation plan, and sprint backlog.

## 1.5 Document Conventions

- **MUST / SHALL** denotes a mandatory requirement; **SHOULD** denotes a recommended requirement; **MAY** denotes optional behaviour.
- Requirement identifiers use `REQ-<module>.<n>`; use cases use `UC-<module>.<n>`.
- **[Implemented]** means the behaviour is present in the current codebase. **[Target]** means a defined but as-yet-unverified numeric objective. **[Planned]** means designed but not yet built.
- File paths are relative to the repository root unless stated otherwise.
- Sequence and class diagrams for each module are maintained as Mermaid source files under `documentation/sequence diagrams/` (e.g. `1.1_Sequence Diagram.md`) and `documentation/class diagrams/` (e.g. `1.1_Class Diagram.md`). They are referenced by path rather than duplicated here.

---

# 2. Overall Description

## 2.1 Product Perspective

TB-XR is a self-contained, semi-integrated client–server web application that complements existing clinical workflows. It does not replace a PACS or HIS; it digitizes image handling, AI triage, diagnostic annotation, and longitudinal monitoring.

**Architecture (as built):**

| Layer | Technology |
| :---- | :---- |
| Frontend | React 19 + Vite 8 + Tailwind CSS v4 (single-page application, JSX) |
| Backend | Django 5.2 + Django REST Framework; function-based API views |
| Auth | Django session authentication + CSRF (cookie/header); `@role_required` decorator for RBAC |
| Database | PostgreSQL (production, when `DB_NAME` is set) / SQLite (development) |
| AI/ML | PyTorch + TorchVision MobileNetV3-Large (`deploy_model.pth`), in-process inference + Grad-CAM heatmaps |
| Image Processing | OpenCV (CLAHE), pydicom (DICOM), Pillow |
| Reporting | Django HTML templates rendered to PDF via a Node.js + Puppeteer subprocess |
| API docs | drf-spectacular (`/api/schema/`, `/api/docs/`) |
| Deployment | Local edge server over LAN/intranet; Docker/Compose configuration not present **[Planned]** |

**Major external interfaces:** digital radiography image files (DICOM/JPEG/PNG) provided as uploads; a pre-trained CNN weight file; a Node/Puppeteer runtime for PDF rendering; a relational DBMS.

## 2.2 Product Functions

- Secure, session-authenticated login with role-directed landing.
- Role-based access control across all workflows (Technologist, Radiologist, Physician).
- Patient registration, listing, name search, and profile (Technologist-initiated).
- Chest X-ray upload with format/size validation, DICOM conversion, and PII tag removal.
- Automated image standardization (CLAHE contrast enhancement, 224×224 normalization).
- Automated image quality assessment with a user-confirmable override.
- Automated CNN baseline risk scoring with risk label and Grad-CAM heatmap.
- Graceful AI failure handling (manual-review status and notification).
- Radiologist review queue with search/filters/pagination and concurrency-safe review locking.
- Interactive X-ray annotation (rectangle, circle, freehand) with notes and undo/delete.
- Structured diagnostic report composition with draft save, validation, and finalization.
- In-system notification of report readiness to physicians.
- Patient history retrieval and side-by-side longitudinal comparison.
- Disease progression computation with trend data and logged manual override.
- Comprehensive per-case PDF report generation.
- Role-specific dashboards (Technologist, Radiologist, Physician) and a shared analytics dashboard.
- Consolidated analytics summary and CSV/PDF export.
- Automated database + media backup and restore tooling.

## 2.3 User Classes and Characteristics

| User class | Description | Technical proficiency | Primary needs |
| :---- | :---- | :---- | :---- |
| **Radiologic Technologist** | Operates radiography equipment; captures and submits patient images. | Moderate; familiar with image capture and basic data entry. | Intuitive upload and patient data entry; clear validation feedback. |
| **Radiologist** | Medical specialist interpreting medical images. | High within specialized tools. | Efficient queue triage, precise annotation, fast reporting; time-sensitive. |
| **Physician (Attending)** | Reviews finalized reports; supports clinical decisions. | Variable; accustomed to EMR and report systems. | Clear, concise, interpretable outputs; consolidated reporting. |

Across all roles, basic computing literacy is assumed; deployment environments may include resource-limited settings, reinforcing the need for accessible, low-bandwidth interactions.

## 2.4 Operating Environment

- **Client:** modern web browser (Chrome v100+, Firefox v100+, Edge v100+) on standard laptops/desktops; keyboard + mouse primary, touchscreen optional.
- **Client hardware:** Intel Core i3 class (or equivalent), ≥ 4 GB RAM.
- **Server:** local edge server (minimum quad-core CPU, ≥ 8 GB RAM, ≥ 20 GB SSD for application, logs, and image cache).
- **Network:** facility LAN/Wi-Fi with stable internal connectivity sufficient for 5–10 MB image transfers; internet connectivity not required for core screening operations.
- **Database:** PostgreSQL 15+ (production) or SQLite (development).
- **AI runtime:** Python with Torch/TorchVision (CPU or CUDA), OpenCV, pydicom, Pillow.
- **PDF runtime:** Node.js 20+ with Puppeteer/Chromium.

## 2.5 Design and Implementation Constraints

- **REQ-2.5.1 [Implemented]** Core screening operations MUST function on a local LAN without external internet access.
- **REQ-2.5.2 [Implemented]** The platform MUST run within low-resource hardware budgets (client i3/4 GB; server quad-core/8 GB).
- **REQ-2.5.3 [Implemented]** The system MUST accept DICOM, JPEG, and PNG chest X-ray inputs and normalize them for display and inference.
- **REQ-2.5.4 [Implemented]** AI output MUST be presented as a non-definitive, assistive baseline; a visible, non-dismissible disclaimer MUST be shown across dashboard and reporting surfaces.
- **REQ-2.5.5 [Implemented]** No PHI/PII may be stored or transmitted in unencrypted channels; DICOM uploads MUST be de-identified.
- **REQ-2.5.6 [Implemented]** Uploads MUST be limited to 20 MB and to `.jpg/.jpeg/.png/.dcm`.
- **REQ-2.5.7 [Implemented]** In production (`DJANGO_ENV=production`), `DEBUG` MUST be `False`, `SECRET_KEY` MUST be set, and `ALLOWED_HOSTS` MUST NOT contain localhost/testserver values.
- **REQ-2.5.8 [Implemented]** The AI model MUST be a pre-trained, serialized weight file loaded at server start; training is out of scope at runtime.
- **REQ-2.5.9 [Implemented]** The system excludes PACS networking, cloud object storage, autonomous diagnosis, and treatment workflows.

## 2.6 Assumptions and Dependencies

- **Pre-trained model availability:** the runtime depends on `ai/model_resources/v1.0.0/deploy_model.pth` being present and uncorrupted; otherwise AI-assisted scoring is unavailable (results route to manual review).
- **Model conformance:** the model is assumed to meet the accepted performance baseline on the reference dataset (Section 6.1).
- **Digital radiography capability:** source machines produce digital outputs in DICOM or JPEG/PNG without extra conversion hardware.
- **DBMS availability:** the configured PostgreSQL/SQLite instance is running and reachable before deployment.
- **Node/Puppeteer availability:** PDF generation requires a Node.js runtime with Chromium; when unavailable, report export fails (Section 7).
- **Persistent local storage:** a local, persistent media partition (baseline 10 GB) is mounted; cloud object storage is intentionally excluded per RA 10173.
- **Backup host:** the backup/restore scripts assume a POSIX host (they use `fcntl.flock`); Windows hosts are unsupported for the file lock.
- **User literacy:** users have basic web literacy for file uploads and interface navigation.

---

# 3. External Interface Requirements

## 3.1 User Interfaces

The frontend is a React SPA with role-guarded routes. Routes are defined in `frontend/src/App.jsx`; layout, sidebar, header, and the global AI disclaimer are provided by `frontend/src/components/layout/AppLayout.jsx`.

| Route | Page component | Allowed role(s) | Notes |
| :---- | :---- | :---- | :---- |
| `/login` | `LoginPage` | Public | Renders outside `AppLayout` (no sidebar/disclaimer). |
| `/dashboard/technologist` | `TechnologistDashboardPage` | `RADIOLOGIC_TECH` | Role-guarded. |
| `/dashboard/radiologist` | `RadiologistDashboardPage` | `RADIOLOGIST` | Role-guarded. |
| `/dashboard/physician` | `PhysicianDashboardPage` | `PHYSICIAN` | Role-guarded. |
| `/dashboard/analytics` | `AnalyticsDashboardPage` | `RADIOLOGIST`, `PHYSICIAN` | Role-guarded. |
| `/radiologist/review/:transactionId` | `AnnotationReviewPage` | `RADIOLOGIST` | Role-guarded. |
| `/radiologist/report/:transactionId` | `ReportWritePage` | `RADIOLOGIST` | Role-guarded. |
| `/patients` | `PatientsPage` | *(currently unguarded)* | See Section 7. |
| `/patients/:patientId` | `PatientDetailPage` | *(currently unguarded)* | See Section 7. |
| `*` | — | — | Redirects to `/login`. |

- **REQ-3.1.1 [Implemented]** The user interface MUST expose role-appropriate navigation derived from the authenticated role.
- **REQ-3.1.2 [Implemented]** A global, non-dismissible AI disclaimer MUST render on every `AppLayout` page (all dashboards, review, report, patients pages).
- **REQ-3.1.3 [Implemented]** The interface MUST provide interactive annotation tooling (rectangle, circle, freehand) with notes and undo/delete.
- **REQ-3.1.4 [Implemented]** The interface MUST provide an image viewer with zoom/pan and an optional Grad-CAM heatmap toggle.
- **REQ-3.1.5 [Implemented]** The header MUST provide a notification bell with an unread badge and mark-read controls.

## 3.2 Hardware Interfaces

- **a) Radiography equipment (indirect):** the system does not control radiographic machines; it consumes exported DICOM/JPEG/PNG files.
- **b) User access devices:** desktops, laptops, and mobile/tablet browsers; keyboard and mouse primary, optional touch.
- **c) Display:** rendering of high-resolution chest X-ray images; medical-grade monitors not required but recommended for radiologists.

## 3.3 Software Interfaces

- **Database:** PostgreSQL (production) or SQLite (development). Core entities: User, Patient, XrayRecord, ProcessedImage, Annotation, AIResult, Report, Notification, ProgressionStatus, ProgressionOverrideAuditLog (Section 5).
- **Web browsers:** Chrome/Firefox/Edge v100+; ES6+, Fetch API, modern CSS.
- **AI engine:** in-process import of `ai/scripts/inference.py` (MobileNetV3-Large + TorchVision transforms + Grad-CAM) invoked by the imaging views.
- **Image libraries:** OpenCV (CLAHE), pydicom (DICOM parsing/anonymization), Pillow (image IO).
- **PDF renderer:** Node.js + Puppeteer invoked via `backend/pdf_scripts/generate.js`.
- **API framework:** Django REST Framework, with session authentication and drf-spectacular OpenAPI schema.

## 3.4 Communications Interfaces

- **Transport:** all client–server traffic MUST be encrypted over HTTPS in production (`SECURE_SSL_REDIRECT`, secure cookies, HSTS).
- **API style:** RESTful endpoints under `/accounts/`, `/api/patients/`, `/api/imaging/`, and `/api/analytics/`.
- **Session auth:** cookie-based (`sessionid`) with CSRF protection. Unsafe methods require a matching `csrftoken` cookie and `X-CSRFToken` header, plus `Origin`/`Referer` as required by Django CSRF.
- **Media:** in development, uploaded media is served from `/media/`.

---

# 4. System Features (Functional Requirements)

Each use case below is grounded in the current implementation. Actor roles and access rules reflect the code (Section 4.6).

## 4.1 Module 1: X-ray Ingestion and Data Management

### 4.1.1 UC-1.1 Secure Image and Metadata Upload

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.1 |
| **Primary Actor** | Radiologic Technologist |
| **Secondary Actor** | System (TB-XR) |
| **Preconditions** | The Technologist is authenticated with role `RADIOLOGIC_TECH`; a target Patient profile exists (or is created first). |
| **Postconditions** | An `XrayRecord` exists with a UUID `transaction_id`, linked to the Patient and uploader, status initially `PENDING`; AI scoring is attempted. |
| **Main Success Scenario** | 1. Technologist opens the patient detail page and chooses "Upload X-ray". 2. Technologist selects a `.jpg/.jpeg/.png/.dcm` file (≤ 20 MB) and submits. 3. The `XrayRecordUploadSerializer` validates extension and size. 4. For DICOM, the serializer converts to PNG and creates a `ProcessedImage`. 5. The backend strips PII tags (Section 6.2), applies CLAHE, generates the 224×224 tensor artifact, and stores preprocessing metadata. 6. The backend runs AI inference automatically (UC-3.1.2). 7. On success the record is returned to the client with status `AI_REVIEWED`. |
| **Alternative Flows** | **AF-1 (Low-quality image):** if the quality score is below threshold, the backend returns `quality_check_failed` with `requires_confirmation=true` and `can_proceed=true`; the UI prompts the Technologist, who may "Proceed Anyway" (re-invokes `analyse/` with `force_proceed=true`) or re-upload. |
| **Exception Flows** | **EF-1 (Unsupported/large file):** the serializer rejects with a validation error (400) and the UI displays it. **EF-2 (Corrupt DICOM/unreadable):** conversion fails, the record is deleted, and a 500 with an error message is returned. **EF-3 (Standardization pipeline error):** the record is deleted and a 500 is returned. |
| **Endpoints** | `POST /api/imaging/patients/<patient_id>/xray/upload/`; `GET .../xray/upload/confirm/<transaction_id>/` |
| **Source** | `backend/apps/imaging/views.py` (`upload_xray`, `upload_confirm`), `serializers.py` (`XrayRecordUploadSerializer`), `preprocessing.py` |

- **REQ-4.1.1 [Implemented]** The system MUST restrict uploads to `RADIOLOGIC_TECH`.
- **REQ-4.1.2 [Implemented]** The system MUST reject files that are not `.jpg/.jpeg/.png/.dcm` or that exceed 20 MB.
- **REQ-4.1.3 [Implemented]** The system MUST assign a UUID `transaction_id` and link the record to the Patient and uploader.

### 4.1.2 UC-1.2 Automated Image Standardization

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.2 |
| **Primary Actor** | System (TB-XR) |
| **Preconditions** | An X-ray image has been uploaded and an `XrayRecord` created. |
| **Postconditions** | A processed (CLAHE-enhanced) PNG exists in `media/xray_processed/`; a normalized 224×224 CHW tensor artifact is recorded in preprocessing metadata. |
| **Main Success Scenario** | 1. The backend reads the raw or DICOM-converted image in grayscale. 2. CLAHE is applied (clip limit 2.0, 8×8 tiles). 3. The enhanced image is saved as PNG. 4. `preprocess_xray` resizes to 224×224, converts L→RGB, applies ImageNet mean/std normalization, and writes a `.npy` tensor artifact. 5. Preprocessing metadata records `ai_tensor_path` and `ai_tensor_ready=true`. |
| **Exception Flows** | **EF-1 (Standardization failure):** an exception aborts the upload, deletes the record, and returns 500. |
| **Endpoints** | Internal to upload pipeline |
| **Source** | `backend/apps/imaging/views.py`, `preprocessing.py` |

- **REQ-4.1.4 [Implemented]** The system MUST apply CLAHE contrast enhancement and produce a 224×224 ImageNet-normalized representation.

> **Note:** the `.npy` tensor is generated and recorded but is not currently consumed by `ai/scripts/inference.py`, which re-derives its input from the image file (Section 7).

### 4.1.3 UC-1.3 Centralized Patient Profiling and Storage

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.3 |
| **Primary Actor** | Radiologic Technologist |
| **Secondary Actor** | System (TB-XR) |
| **Preconditions** | The Technologist is authenticated. |
| **Postconditions** | A Patient master record is created and indexed; patients can be listed, searched, and retrieved. |
| **Main Success Scenario** | 1. Technologist opens the Patients page. 2. Technologist submits the new-patient form with first name, last name, date of birth, sex (M/F/O), and contact number. 3. The backend validates via `PatientCreateSerializer` and saves the Patient (201, `Location` header). 4. Technologist may search by name or open a patient profile. |
| **Exception Flows** | **EF-1 (Validation error):** 400 with field-level errors. **EF-2 (Wrong role):** non-Technologist registration returns 403. |
| **Endpoints** | `POST /api/patients/register/`; `GET /api/patients/`; `GET /api/patients/search/?name=`; `GET /api/patients/<patient_id>/` |
| **Source** | `backend/apps/patients/views.py`, `serializers.py`, `models.py` |

- **REQ-4.1.5 [Implemented]** Patient registration MUST be restricted to `RADIOLOGIC_TECH`.
- **REQ-4.1.6 [Implemented]** Patient listing/search/detail MUST be available to authenticated clinical roles.

### 4.1.4 UC-1.4 Image Quality Gate

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.4 |
| **Primary Actor** | System (TB-XR) |
| **Secondary Actor** | Radiologic Technologist |
| **Preconditions** | An image has been uploaded and preprocessing initiated. |
| **Postconditions** | Either AI scoring proceeds, or the Technologist is prompted to confirm/re-upload. |
| **Main Success Scenario** | 1. The AI module's `assess_quality` computes a quality score. 2. If the score is ≥ 0.6, processing continues to AI scoring. 3. If below 0.6 and `force_proceed` is false, the system returns `quality_check_failed` with the score and `requires_confirmation=true`, and does not create an `AIResult`. 4. The Technologist confirms ("Proceed Anyway") or re-uploads. |
| **Exception Flows** | **EF-1 (Proceed override):** when confirmed, `force_proceed=true` is recorded in preprocessing metadata and scoring proceeds. |
| **Endpoints** | `POST .../xray/upload/`; `POST /api/imaging/xray/<transaction_id>/analyse/` |
| **Source** | `ai/scripts/quality.py`, `backend/apps/imaging/views.py` |

- **REQ-4.1.7 [Implemented]** The system MUST compute a deterministic quality score (threshold 0.6) using resolution, exposure, contrast, and blur heuristics.
- **REQ-4.1.8 [Implemented]** The system MUST NOT silently discard low-quality images; the user MUST be prompted with an explicit proceed/re-upload choice, and overrides MUST be recorded.

## 4.2 Module 2: Annotation and Diagnostic Review

### 4.2.1 UC-2.1 Remote Access Queue

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.1.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist is authenticated; at least one X-ray record exists. |
| **Postconditions** | A paginated, filterable queue of X-ray records is presented, with AI scores where available. |
| **Main Success Scenario** | 1. Radiologist opens the Radiologist Dashboard. 2. The system returns records (default ordering by upload time) with filters. 3. The table shows patient, transaction ID, upload time, uploader, status, and AI score/label. 4. Radiologist may search (`search=`) and filter by `status` and `risk_label`. |
| **Alternative Flows** | **AF-1 (Empty queue):** the table shows "No records found." |
| **Exception Flows** | **EF-1 (Retrieval error):** an error banner is displayed. |
| **Endpoints** | `GET /api/imaging/queue/` |
| **Source** | `backend/apps/imaging/views.py` (`radiologist_queue`), `serializers.py`; `frontend/src/pages/dashboard/RadiologistDashboardPage.jsx` |

- **REQ-4.2.1 [Implemented]** The queue MUST support filtering by `status` (`PENDING`, `IN_REVIEW`, `AI_REVIEWED`, `MANUAL_REVIEW`, `COMPLETED`), `risk_label` (`LOW`, `MODERATE`, `HIGH`), and free-text `search`, with pagination (page size 20).

### 4.2.2 UC-2.2 Concurrency-Safe Review Session

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.2.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist opens an X-ray detail. |
| **Postconditions** | The record is rendered in the review workspace; the record status transitions to `IN_REVIEW`; a review lock is held by this Radiologist. |
| **Main Success Scenario** | 1. Radiologist selects a record from the queue. 2. The system acquires a review lock (`active_reviewer`, `lock_timestamp`) and, for `PENDING`/`AI_REVIEWED`/`MANUAL_REVIEW`, sets status to `IN_REVIEW`. 3. The workspace renders the image, AI panel, annotation canvas, and patient history. |
| **Alternative Flows** | **AF-1 (Locked by another):** the system returns HTTP 409 with the active reviewer and lock timestamp; the UI opens a **read-only mode** banner and disables editing. |
| **Exception Flows** | **EF-1 (Expired lock):** a lock older than `REVIEW_LOCK_TIMEOUT_MINUTES` (default 60) is considered expired and can be re-acquired. |
| **Endpoints** | `GET /api/imaging/xray/<transaction_id>/` |
| **Source** | `models.py` (`XrayRecord.acquire_lock`/`lock_has_expired`), `views.py` (`xray_detail`); `frontend/src/pages/AnnotationReviewPage.jsx` |

- **REQ-4.2.2 [Implemented]** The system MUST prevent conflicting concurrent reviews by issuing a lock and returning 409 to a second reviewer.
- **REQ-4.2.3 [Implemented]** Locks MUST auto-expire after a configurable timeout (default 60 minutes).

### 4.2.3 UC-2.3 Interactive Annotation

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.3.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | An X-ray image is open in an editable review session. |
| **Postconditions** | One or more regions of interest (ROIs) with labels and text notes are captured for submission. |
| **Main Success Scenario** | 1. Radiologist selects a tool (rectangle, circle, or freehand). 2. Radiologist draws an ROI on the image. 3. The system renders the overlay and prompts for a label. 4. Radiologist may add multiple ROIs, undo (Ctrl/Cmd+Z), or delete ROIs. 5. Radiologist adds a diagnostic note. |
| **Alternative Flows** | **AF-1 (Delete ROI):** selected ROI is removed. **AF-2 (Undo):** the last ROI is reverted (history bounded to 20). |
| **Endpoints** | Client-side; persisted via `POST /api/imaging/xray/<transaction_id>/annotate/` |
| **Source** | `frontend/src/components/imaging/AnnotationCanvas.jsx`, `AnnotationPanel.jsx` |

- **REQ-4.2.4 [Implemented]** The annotation toolset MUST support rectangle, circle, and freehand ROI drawing, label assignment, deletion, and undo.
- **REQ-4.2.5 [Implemented]** ROIs MUST be stored in normalized coordinates with labels; notes MUST be attached to the annotation record.

> **Note:** brightness/contrast adjustments are not currently implemented; the viewer provides zoom/pan only (Section 7).

### 4.2.4 UC-2.4 Structured Diagnostic Report

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.4.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist is authenticated and a record exists. |
| **Postconditions** | A `Report` exists for the transaction with status `DRAFT` or `SUBMITTED`. |
| **Main Success Scenario** | 1. Radiologist opens the report page for a transaction. 2. The system pre-populates any existing draft. 3. Radiologist completes **Findings**, **Impression**, **Recommendation**, and **Severity** (`NORMAL`/`MILD`/`MODERATE`/`SEVERE`/`CRITICAL`). 4. Radiologist may **Save Draft** (status remains `DRAFT`). 5. On **Submit Report**, the system validates required fields, sets status to `SUBMITTED`, stamps `created_by`, and triggers a physician notification. 6. A submitted report becomes immutable. |
| **Alternative Flows** | **AF-1 (Edit before submit):** the Radiologist saves/updates the draft (PATCH) before submission. |
| **Exception Flows** | **EF-1 (Validation error):** missing required fields block submission (400; UI highlights fields). **EF-2 (Modify finalized):** PATCH on a `SUBMITTED` report returns 400 "Cannot modify a finalized report." |
| **Endpoints** | `GET/POST/PATCH /api/imaging/xray/<transaction_id>/report/`; `GET .../report/generate/` |
| **Source** | `models.py` (`Report`), `serializers.py` (`ReportCreateSerializer`, `ReportSerializer`), `views.py` (`report_detail`, `generate_report`); `frontend/src/pages/ReportWritePage.jsx` |

- **REQ-4.2.6 [Implemented]** The report MUST capture Findings, Impression, Recommendation, and Severity.
- **REQ-4.2.7 [Implemented]** The system MUST support draft save and MUST validate required fields before final submission.
- **REQ-4.2.8 [Implemented]** Submitted reports MUST be immutable.
- **REQ-4.2.9 [Implemented]** Report endpoints MUST be restricted to `RADIOLOGIST`.

### 4.2.5 UC-2.5 Annotation Submission and Transaction Completion

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.5.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | An active review session with at least one ROI. |
| **Postconditions** | The `Annotation` is created/updated; the `XrayRecord` status becomes `COMPLETED`. |
| **Main Success Scenario** | 1. Radiologist submits findings. 2. The system upserts the radiologist's annotation (`bounding_boxes`, `notes`) and sets status to `COMPLETED`. 3. The Radiologist is returned to the queue. |
| **Endpoints** | `POST /api/imaging/xray/<transaction_id>/annotate/` |
| **Source** | `views.py` (`annotate_xray`), `models.py` (`Annotation`) |

- **REQ-4.2.10 [Implemented]** Submitting an annotation MUST require at least one bounding box and MUST transition the record to `COMPLETED`.
- **REQ-4.2.11 [Implemented]** The annotation endpoint MUST be restricted to `RADIOLOGIST`.

## 4.3 Module 3: AI Engine and Longitudinal Monitoring

### 4.3.1 UC-3.1 AI Baseline Risk Scoring

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.1.1 |
| **Primary Actor** | System (Automated) |
| **Secondary Actor** | CNN AI Engine (MobileNetV3-Large) |
| **Preconditions** | A standardized, quality-accepted image exists for a transaction. |
| **Postconditions** | An `AIResult` exists (`risk_score`, `risk_label`, `model_version`, optional heatmap), and the record status is `AI_REVIEWED`. |
| **Main Success Scenario** | 1. The backend loads the inference module and calls `predict(image_path)`. 2. The model returns a probability in [0,1]; the backend maps it to a DB risk label. 3. The backend calls `generate_heatmap` and stores the resulting image on `AIResult`. 4. The backend writes the `AIResult` (create/update) and sets status to `AI_REVIEWED`. |
| **Exception Flows** | **EF-1 (Model unavailable / inference error):** the system does not retry; it sets status to `MANUAL_REVIEW`, records the error, and notifies all radiologists that manual review is required. **EF-2 (Invalid/out-of-range score):** treated as an inference failure and routed to `MANUAL_REVIEW`. |
| **Endpoints** | Triggered by upload; re-runnable via `POST /api/imaging/xray/<transaction_id>/analyse/` |
| **Source** | `ai/scripts/inference.py`, `backend/apps/imaging/views.py` (`_run_ai_inference`, `_get_inference_module`) |

- **REQ-4.3.1 [Implemented]** The system MUST compute a TB risk probability using the configured CNN and persist it with a model version.
- **REQ-4.3.2 [Implemented]** The system MUST generate a Grad-CAM heatmap when possible and attach it to the result.
- **REQ-4.3.3 [Implemented]** On inference failure, the system MUST set `MANUAL_REVIEW`, persist an error reason, and notify radiologists; it MUST NOT present a stale or default score.
- **REQ-4.3.4 [Target]** The AI baseline score SHOULD be produced within 10 seconds of image acceptance; measured mean inference is 73.3 ms (Section 6.1).

> **Note on risk labels:** the DB enum supports `LOW`/`MODERATE`/`HIGH`, but the deployed model is binary (threshold 0.5 → "High Risk"/"Low Risk"). `MODERATE` is therefore only produced by seeded/demo data or a "moderate" label from inference; it is not emitted by the shipped model (Section 7).

> **Note on retries:** the original SRS specified up to 3 retries before declaring AI unavailable. The current implementation performs no automatic retry; a failure immediately routes to manual review.

### 4.3.2 UC-3.2 Historical Record Retrieval

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.2.1 |
| **Primary Actor** | System (Automated) |
| **Secondary Actor** | Radiologist |
| **Preconditions** | A patient workspace is opened. |
| **Postconditions** | All prior X-ray records for the patient are retrieved (or an empty-state is confirmed). |
| **Main Success Scenario** | 1. The system extracts the Patient ID. 2. The system queries all `XrayRecord` rows for that patient, ordered chronologically ascending, with AI results and annotations. 3. The system populates the longitudinal panel and thumbnails. |
| **Alternative Flows** | **AF-1 (No history):** the panel shows "First Visit / No Historical Records Found". |
| **Exception Flows** | **EF-1 (Retrieval error):** a non-intrusive "Unable to load patient history" message is shown; current review continues. |
| **Endpoints** | `GET /api/imaging/patients/<patient_id>/xray/`; `GET /api/imaging/patients/<patient_id>/history/` |
| **Source** | `views.py` (`patient_xrays`, `patient_history`), `serializers.py`; `frontend/src/components/imaging/LongitudinalPanel.jsx` |

- **REQ-4.3.5 [Implemented]** The system MUST retrieve and order patient history chronologically for longitudinal review.

### 4.3.3 UC-3.3 Comparative Progression Tracking and Override

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.3.1 |
| **Primary Actor** | System (Automated) |
| **Secondary Actor** | Radiologist |
| **Preconditions** | The patient has at least one prior valid AI result, or the current result is available. |
| **Postconditions** | A progression snapshot/status and trend data are available for the patient; overrides are audited. |
| **Main Success Scenario** | 1. The system identifies the current AI score and the immediately preceding valid AI score for the patient (ordered by upload time then PK). 2. It computes `delta = round(current − previous, 4)` and `abs_delta`, then classifies: `abs_delta ≤ threshold` → `stable`; `delta < 0` → `decreased_risk` (Improvement); else `increased_risk` (Deterioration); no prior → `no_prior`. 3. It persists a `ProgressionStatus` snapshot and exposes trend data. 4. The UI plots a trend chart. |
| **Alternative Flows** | **AF-1 (No comparable prior):** `comparison_available=false` with a reason; only available points are plotted. **AF-2 (Manual override):** a Radiologist sets an override status and MUST supply a clinical note; the system persists the override and writes a `ProgressionOverrideAuditLog`. |
| **Exception Flows** | **EF-1 (Invalid threshold/score):** the service raises a validation error rather than silently defaulting. |
| **Endpoints** | `GET /api/imaging/patients/<patient_id>/progression/`; `GET /api/imaging/cases/<case_id>/progression/`; `POST /api/imaging/cases/<case_id>/progression/override/` |
| **Source** | `backend/apps/imaging/services.py` (`ProgressionService`), `models.py` (`ProgressionStatus`, `ProgressionOverrideAuditLog`), `views.py`; `frontend/src/components/imaging/LongitudinalPanel.jsx` |

- **REQ-4.3.6 [Implemented]** The system MUST compute a progression status using a configurable stable threshold (default 0.05) with an inclusive boundary.
- **REQ-4.3.7 [Implemented]** The system MUST support Radiologist manual override with a mandatory clinical note, and MUST write an audit-log entry.
- **REQ-4.3.8 [Implemented]** Override MUST be restricted to `RADIOLOGIST`; progression retrieval MUST be available to authenticated users.

> **Note:** the comparison uses the immediately preceding record that has a valid AI result, regardless of record status, rather than only `COMPLETED` scans as originally specified.

### 4.3.4 UC-3.4 Comprehensive PDF Report Generation

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.4.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The `XrayRecord` status is `COMPLETED`. |
| **Postconditions** | A PDF report is downloaded. |
| **Main Success Scenario** | 1. Radiologist triggers "Generate Report". 2. The system assembles patient demographics, AI score/label, heatmap, annotations, and clinical text. 3. The system renders an HTML template and invokes Node/Puppeteer to produce a PDF. 4. The PDF is streamed to the browser. |
| **Exception Flows** | **EF-1 (Not completed):** returns 400. **EF-2 (Renderer failure):** returns 500 with diagnostic detail. |
| **Endpoints** | `GET /api/imaging/xray/<transaction_id>/report/generate/` |
| **Source** | `views.py` (`generate_report`), `backend/pdf_scripts/generate.js`, `backend/templates/reports/xray_report.html` |

- **REQ-4.3.9 [Implemented]** PDF generation MUST require a `COMPLETED` transaction.
- **REQ-4.3.10 [Implemented]** The generated report MUST include the non-dismissible clinical safety disclaimer.

## 4.4 Module 4: Clinical Dashboards and Reporting

### 4.4.1 UC-4.1 Authentication and Role-Based Access Control

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.1.1 |
| **Primary Actor** | User (Technologist, Radiologist, Physician) |
| **Preconditions** | The user has a registered account with an assigned role. |
| **Postconditions** | A secure session is created and the user is directed to their role dashboard. |
| **Main Success Scenario** | 1. The client obtains a CSRF cookie from `GET /accounts/csrf-token/`. 2. The user submits credentials to `POST /accounts/login/`. 3. The backend authenticates and returns `{role, redirect}`. 4. The client stores the role and navigates to the role dashboard. |
| **Alternative Flows** | **AF-1 (Logout):** `POST /accounts/logout/` ends the session and clears local state. |
| **Exception Flows** | **EF-1 (Invalid credentials):** 401. **EF-2 (Missing role mapping):** 400. **EF-3 (Wrong role for endpoint):** 403 (authenticated) or redirect to login (unauthenticated). |
| **Endpoints** | `GET /accounts/csrf-token/`; `POST /accounts/login/`; `POST /accounts/logout/` |
| **Source** | `backend/apps/accounts/views.py`, `decorators.py`, `models.py`, `enums.py`; `frontend/src/context/AuthContext.jsx`, `components/login/LoginForm.jsx`, `components/auth/RoleGuard.jsx` |

- **REQ-4.4.1 [Implemented]** Authentication MUST use Django session cookies with CSRF protection.
- **REQ-4.4.2 [Implemented]** The system MUST enforce role checks through the `@role_required` decorator (403 for wrong role).
- **REQ-4.4.3 [Implemented]** The client MUST guard routes by role and redirect to the correct dashboard.

### 4.4.2 UC-4.2 Role-Specific Dashboards and Transaction Tracking

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.2.1 |
| **Primary Actor** | User (Technologist, Radiologist, Physician) |
| **Preconditions** | The user is authenticated with a confirmed role. |
| **Postconditions** | The system displays a dashboard tailored to the role. |
| **Main Success Scenario** | 1. The dashboard requests its role-scoped data. 2. The backend filters records/reports for that role. 3. The dashboard renders stat cards, filters, and a paginated table or cards. |
| **Endpoints** | `GET /api/imaging/dashboard/technologist/` (Tech); `GET /api/imaging/queue/` (Radiologist); `GET /api/physician/dashboard[/]` (Physician) |
| **Source** | `views.py` (`technologist_dashboard`, `radiologist_queue`, `physician_dashboard`); `frontend/src/pages/dashboard/*` |

- **REQ-4.4.4 [Implemented]** The Technologist dashboard MUST show only records uploaded by that Technologist.
- **REQ-4.4.5 [Implemented]** The Physician dashboard MUST surface finalized (`SUBMITTED`) reports, unread alerts, report-ready items, and patient progress, and MUST be restricted to `PHYSICIAN`.

### 4.4.3 UC-4.3 In-System Notifications

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.3.1 |
| **Primary Actor** | User |
| **Preconditions** | Notifications exist for the current user. |
| **Postconditions** | Notifications are listed and may be marked read. |
| **Main Success Scenario** | 1. A report submission (DRAFT→SUBMITTED) creates a notification for a physician. 2. An AI failure creates notifications for all radiologists. 3. The user opens the notification bell, retrieves notifications, and may mark one or all read. |
| **Endpoints** | `GET /api/imaging/notifications/`; `POST /api/imaging/notifications/<notification_id>/mark-read/` |
| **Source** | `models.py` (`Notification`), `views.py` (`notifications`, `notification_mark_read`, `_trigger_report_submission_notification`, `_trigger_manual_review_notification`); `frontend/src/components/layout/Header.jsx` |

- **REQ-4.4.6 [Implemented]** The system MUST generate in-system notifications on report submission and AI failure.
- **REQ-4.4.7 [Implemented]** Notification access MUST be ownership-scoped (a user MUST NOT read/mark another user's notifications).

### 4.4.4 UC-4.4 Consolidated Analytics and Export

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.4.1 |
| **Primary Actor** | Radiologist or Physician |
| **Preconditions** | The user has an authorized role. |
| **Postconditions** | Aggregated case/report metrics are displayed and can be exported. |
| **Main Success Scenario** | 1. The analytics dashboard requests a summary with optional `date_from`, `date_to`, and `severity`. 2. The backend computes totals and breakdowns (case status, AI risk label, report severity, report status). 3. The UI renders charts/tables. 4. The user exports CSV or PDF. |
| **Exception Flows** | **EF-1 (Empty dataset):** empty-state prompts. **EF-2 (Invalid filters):** 400. |
| **Endpoints** | `GET /api/analytics/summary/` (alias `GET /api/imaging/analytics/summary/`); `POST /api/analytics/export/` (alias `.../imaging/analytics/export/`) |
| **Source** | `views.py` (`analytics_summary`, `analytics_export`, `_get_analytics_data`); `frontend/src/pages/dashboard/AnalyticsDashboardPage.jsx` |

- **REQ-4.4.8 [Implemented]** The system MUST compute aggregated metrics filtered by date range and severity.
- **REQ-4.4.9 [Implemented]** The system MUST export consolidated analytics as CSV and PDF.

### 4.4.5 UC-4.5 Automated Backup and Restore

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.5.1 |
| **Primary Actor** | DevOps / Administrator |
| **Preconditions** | A POSIX host with DB and media access. |
| **Postconditions** | A timestamped, checksummed backup exists (or a verified, optionally applied restore). |
| **Main Success Scenario** | 1. Operator runs `python scripts/backup.py`. 2. The tool dumps the database and archives media into a timestamped directory with a `manifest.json` (per-file SHA-256). 3. On demand, `python scripts/restore.py [DIR] [--apply]` verifies checksums and restores the DB and/or media. |
| **Exception Flows** | **EF-1 (Overlapping dirs):** backup root and media root must be disjoint. **EF-2 (Checksum mismatch):** restore refuses. **EF-3 (Non-POSIX):** the file lock raises. |
| **Source** | `backend/scripts/backup.py`, `restore.py`, `backup_lock.py`; `documentation/backup-restore.md` |

- **REQ-4.4.10 [Implemented]** Backups MUST include the database and media with integrity manifests.
- **REQ-4.4.11 [Implemented]** Restore MUST verify integrity and support dry-run and partial (DB-only/media-only) modes.

## 4.5 Cross-cutting: Status Lifecycles

**XrayRecord status (`backend/apps/imaging/models.py`):**

| Status | Meaning | Typical transition source |
| :---- | :---- | :---- |
| `PENDING` | Uploaded; not yet scored/reviewed. | Upload. |
| `IN_REVIEW` | A radiologist has an active (locked) review. | `xray_detail` lock acquisition. |
| `AI_REVIEWED` | AI score successfully produced. | `_run_ai_inference`. |
| `MANUAL_REVIEW` | AI unavailable/failed; manual review required. | `_run_ai_inference` failure. |
| `COMPLETED` | Radiologist annotation submitted. | `annotate_xray`. |

**Report status (`backend/apps/imaging/models.py`):**

| Status | Meaning |
| :---- | :---- |
| `DRAFT` | Editable; may be saved/updated repeatedly. |
| `SUBMITTED` | Finalized and immutable; triggers physician notification. |

- **REQ-4.5.1 [Implemented]** The system MUST use the status vocabularies above; the original SRS's verbose per-stage labels ("Pending Standardization", etc.) are obsolete.

## 4.6 Cross-cutting: Role-Based Access Control Matrix

Roles: `RADIOLOGIC_TECH` (T), `RADIOLOGIST` (R), `PHYSICIAN` (P). "Auth" = any authenticated role.

| Capability / Endpoint | T | R | P | Auth |
| :---- | :----: | :----: | :----: | :----: |
| Register patient | ✔ | | | |
| List/search/detail patients | ✔ | ✔ | ✔ | |
| Upload / confirm X-ray | ✔ | | | |
| Re-run AI analysis (`analyse/`) | ✔ | | | |
| Patient x-ray list / history | ✔ | ✔ | ✔ | |
| X-ray detail (review lock) | ✔ | ✔ | ✔ | |
| Annotate X-ray | | ✔ | | |
| Radiologist queue | | ✔ | | |
| Technologist dashboard | ✔ | | | |
| Physician dashboard | | | ✔ | |
| Report read/create/update | | ✔ | | |
| Report generate (PDF) | | ✔ | | |
| Progression retrieval | | | | ✔ |
| Progression override | | ✔ | | |
| Notifications list / mark-read | | | | ✔ |
| Analytics summary / export | | ✔ | ✔ | |

- **REQ-4.6.1 [Implemented]** RBAC MUST be enforced server-side; client-side guards are supplementary.
- **REQ-4.6.2 [Implemented]** Access rules MUST be applied consistently; deviations (e.g. patient endpoints also allowing `PHYSICIAN`, progression/notifications being login-only) are documented in Section 7.

---

# 5. Data Requirements

Entities are defined in `backend/apps/*/models.py`. All timestamps are timezone-aware UTC.

### 5.1 User (`accounts.User`)
`username`, `password`, `first_name`, `last_name`, `email`; `role` enum (`RADIOLOGIC_TECH`, `RADIOLOGIST`, `PHYSICIAN`; default `RADIOLOGIC_TECH`).

### 5.2 Patient (`patients.Patient`)
| Field | Type | Notes |
| :---- | :---- | :---- |
| `patient_id` | AutoField PK | |
| `first_name` / `last_name` | CharField(100) | |
| `date_of_birth` | DateField | |
| `sex` | CharField(1) | `M`/`F`/`O` (canonical field name is `sex`) |
| `contact_number` | CharField(20) | |
| `date_created` | DateTimeField | auto |

### 5.3 XrayRecord (`imaging.XrayRecord`)
`transaction_id` (UUID, unique), `patient` (FK), `raw_image` (FileField, `raw/`), `upload_timestamp`, `status` (see 4.5), `uploader` (FK User), `file_format`, `active_reviewer` (FK User, nullable), `lock_timestamp` (nullable).

### 5.4 ProcessedImage (`imaging.ProcessedImage`)
`xray_record` (OneToOne), `processed_image` (ImageField, `xray_processed/`), `preprocessing_metadata` (JSON: source, CLAHE settings, `ai_tensor_path`, `ai_tensor_ready`, and low-quality override flags when applicable).

### 5.5 Annotation (`imaging.Annotation`)
`xray_record` (FK), `radiologist` (FK User, nullable), `bounding_boxes` (JSON array of `{x, y, width, height, label}`; UI also stores `shape`/`points` for circle/freehand), `notes` (TextField), `submitted_at`.

### 5.6 AIResult (`imaging.AIResult`)
`xray_record` (OneToOne), `risk_score` (float, [0,1]), `risk_label` (`LOW`/`MODERATE`/`HIGH`), `heatmap_image` (ImageField, `heatmaps/`, nullable), `model_version` (e.g. `v1.0.0`), `generated_at`.

### 5.7 Report (`imaging.Report`)
`xray_record` (OneToOne), `findings`, `impression`, `recommendation` (TextFields), `severity` (`NORMAL`/`MILD`/`MODERATE`/`SEVERE`/`CRITICAL`), `created_by` (FK User), `created_at`, `updated_at`, `status` (`DRAFT`/`SUBMITTED`).

### 5.8 Notification (`imaging.Notification`)
`recipient` (FK User), `message` (Text), `read_status` (bool), `created_at`, `updated_at`.

### 5.9 ProgressionStatus (`imaging.ProgressionStatus`)
`patient` (FK), `xray_record` (FK), `previous_record` (FK, nullable), `status` (`no_prior`/`stable`/`decreased_risk`/`increased_risk`), `score`, `previous_score`, `delta`, `abs_delta`, `threshold` (default 0.05), `comparison_available` (bool), `reason`, `source` (`ai`/`manual_override`), `clinical_note`, `is_overridden` (bool), `overridden_by` (FK User, nullable), `override_timestamp`, `recorded_at`.

### 5.10 ProgressionOverrideAuditLog (`imaging.ProgressionOverrideAuditLog`)
`patient` (FK), `xray_record` (FK), `radiologist` (FK User, nullable), `previous_status`, `new_status`, `clinical_note`, `created_at`.

- **REQ-5.1 [Implemented]** The data model MUST persist users, patients, X-ray transactions, processed images, annotations, AI results, reports, notifications, progression snapshots, and override audit logs as above.
- **REQ-5.2 [Implemented]** The canonical patient demographic field is `sex` (not `gender`).

---

# 6. Non-Functional Requirements

## 6.1 Performance

Measured (validation split, 837 images; `ai/model_resources/MODEL_PERFORMANCE.md`):

| Metric | Result |
| :---- | :---- |
| Accuracy | 99.88% |
| Sensitivity (Recall) | 99.27% |
| Specificity | 100.00% |
| Precision | 100.00% |
| F1 | 99.63% |
| AUC-ROC | 1.0000 |
| Inference latency (mean / median) | 73.335 ms / 65.557 ms (max 467.838 ms) |

- **REQ-6.1.1 [Implemented]** AI inference MUST return a baseline score under the accepted threshold; measured mean is ~73 ms on the reference host.
- **REQ-6.1.2 [Target]** Image standardization SHOULD complete in < 6 s per upload.
- **REQ-6.1.3 [Target]** Queue/review loading SHOULD complete in < 5 s.
- **REQ-6.1.4 [Target]** Heatmap generation SHOULD complete in < 10 s.
- **REQ-6.1.5 [Target]** Progression comparison SHOULD complete in < 3 s.
- **REQ-6.1.6 [Target]** PDF report generation SHOULD complete in < 2 s.
- **REQ-6.1.7 [Target]** The AI baseline score SHOULD be produced in < 10 s (original SRS objective).

## 6.2 Security and Privacy

- **REQ-6.2.1 [Implemented]** All clinical endpoints MUST require an authenticated session; role restrictions MUST be enforced server-side.
- **REQ-6.2.2 [Implemented]** State-changing requests MUST be CSRF-protected (cookie + `X-CSRFToken`).
- **REQ-6.2.3 [Implemented]** DICOM uploads MUST be de-identified by stripping at least: PatientName, PatientID, PatientBirthDate, PatientSex, PatientAge, InstitutionName, ReferringPhysicianName, StudyDate, AccessionNumber.
- **REQ-6.2.4 [Implemented]** In production, the system MUST enforce `DEBUG=False`, a configured `SECRET_KEY`, non-localhost `ALLOWED_HOSTS`, HTTPS-only `CSRF_TRUSTED_ORIGINS`, secure cookies, SSL redirect, and HSTS.
- **REQ-6.2.5 [Implemented]** Review data MUST be protected against conflicting concurrent edits via review locking.
- **REQ-6.2.6 [Implemented]** Progression overrides MUST be attributable via an audit log capturing actor, prior/new status, note, and timestamp.
- **REQ-6.2.7 [Target]** PHI/PII SHOULD be encrypted in transit and at rest; cloud object storage is excluded.

## 6.3 Reliability and Availability

- **REQ-6.3.1 [Implemented]** The system MUST provide automated backup tooling covering the database and media with integrity manifests.
- **REQ-6.3.2 [Implemented]** Restore MUST support dry-run verification and partial restore.
- **REQ-6.3.3 [Implemented]** Backup retention MUST default to 14 archives (configurable; 0 = keep all).
- **REQ-6.3.4 [Implemented]** AI failure MUST NOT block the clinical workflow; affected records route to `MANUAL_REVIEW`.
- **REQ-6.3.5 [Target]** The platform SHOULD maintain high availability for remote radiologist access.
- **REQ-6.3.6 [Implemented]** Backups are crash-consistent (database and media are not a single atomic unit), as documented in the runbook.

## 6.4 Usability

- **REQ-6.4.1 [Implemented]** The interface MUST provide role-tailored dashboards and clear validation feedback.
- **REQ-6.4.2 [Target]** The system SHOULD achieve a SUS score > 70 in pilot evaluation.
- **REQ-6.4.3 [Implemented]** A visible, non-dismissible AI disclaimer MUST appear on all dashboard/reporting surfaces.

## 6.5 Maintainability and Testability

- **REQ-6.5.1 [Implemented]** Backend tests MUST cover access control, upload/AI, reports, progression, physician dashboard, and backup/restore.
- **REQ-6.5.2 [Implemented]** A CI pipeline MUST run smoke tests (backend) and unit tests + lint (frontend) on push/PR.
- **REQ-6.5.3 [Target]** Report-related code SHOULD maintain ≥ 80% coverage; the progression module ≥ 85%.
- **REQ-6.5.4 [Implemented]** The backend MUST expose an OpenAPI schema/Swagger UI (public in DEBUG, staff-only otherwise).

## 6.6 Regulatory and Ethical Compliance

- **REQ-6.6.1 [Implemented]** The system MUST protect PHI/PII consistent with the Philippine Data Privacy Act of 2012 (RA 10173).
- **REQ-6.6.2 [Implemented]** The AI MUST be presented strictly as an assistive, non-definitive baseline; diagnostic authority remains with human clinicians.
- **REQ-6.6.3 [Implemented]** The system MUST include clinical liability disclaimers in the UI and in generated reports.

---

# 7. Known Limitations and Future Work

The following are verified limitations of the current implementation; they are listed so that requirements are not misrepresented and so that remediation can be tracked.

| # | Area | Limitation | Suggested direction |
| :-- | :---- | :---- | :---- |
| 1 | AI retry | No automatic retry/timeout loop; any inference failure goes straight to `MANUAL_REVIEW`. | Add bounded retries before declaring unavailable (per original UC-3.1.2 EF-2). |
| 2 | Risk labels | DB supports `LOW`/`MODERATE`/`HIGH`, but the shipped model is binary (0.5). `MODERATE` is not produced by inference. | Either train a 3-class/ordinal model or derive MODERATE from calibrated bands. |
| 3 | Progression PDF | The generated report has no progression section; the original AF-1 (omit section) is moot. | Add a progression block to `xray_report.html` when comparison data exists. |
| 4 | Progression comparison | Compares against the immediately preceding valid AI result regardless of record status (original spec used `COMPLETED`). | Align comparison basis if clinically required. |
| 5 | Notification recipient | No physician-assignment model; report-ready notifications go to the first physician by ID (deduped). | Introduce patient↔physician assignment. |
| 6 | Frontend route protection | `/patients` and `/patients/:id` are not wrapped in `RoleGuard`. | Add auth/role guards. |
| 7 | Session identity | Login persists only `{role}`; header name/email render blank. | Persist the full user profile from login. |
| 8 | Global search | Header search input is decorative (no handler). | Implement or remove. |
| 9 | `.npy` tensor | Generated and recorded but not consumed by inference. | Feed the tensor to inference or drop the artifact. |
| 10 | Dead code | `XrayViewer.jsx` is unused; legacy backend HTML dashboard placeholders are unrouted. | Remove. |
| 11 | Deployment | No Docker/Compose or production web-server config in-repo. | Add deployment configuration. |
| 12 | Backup portability | Backup/restore file lock is POSIX-only. | Add a Windows-compatible lock or document the constraint. |
| 13 | AI docs drift | `USAGE.md` uses `Normalize([0.5]*3)` while code uses ImageNet stats; `model_check.py` references stale filenames. | Reconcile documentation/scripts. |
| 14 | Annotation display controls | No brightness/contrast adjustments beyond zoom/pan. | Add display controls if required. |
| 15 | Dataset representativeness | Performance is measured on a small, "easy" dataset; recall is the priority metric. | Validate on local clinical data during pilot. |
| 16 | Report workflow | PDF generation auto-creates a minimal placeholder draft report when none exists, silently creating a clinical record as a side effect of report generation. | Require an existing draft report before PDF generation, or return an explicit error directing the user to create one first. |
| 17 | Report auditability | `Report` has no dedicated `finalized_at` timestamp; finalization is only observable via `status` and `updated_at`. | Add `finalized_at` (nullable) if audit, signature, or governance requirements grow. |
| 18 | Report validation layer | Draft/final submission invariants live in the serializer; there is no domain-layer enforcement. | Move key invariants into model or service-layer validation if the report workflow expands. |
| 19 | Severity semantics | The clinical meaning of `severity` (TB suspicion level vs. radiology severity vs. clinical urgency) is not explicitly defined. | Confirm and document the intended meaning; rename if a more precise term is needed. |

---

# Appendix A: Traceability Matrix

| Use Case | Requirement(s) | Primary endpoint(s) | Source file(s) |
| :---- | :---- | :---- | :---- |
| UC-1.1 Upload | REQ-4.1.1–4.1.3 | `POST /api/imaging/patients/<id>/xray/upload/` | `apps/imaging/views.py`, `serializers.py` |
| UC-1.2 Standardization | REQ-4.1.4 | (upload pipeline) | `apps/imaging/preprocessing.py`, `views.py` |
| UC-1.3 Patient profiling | REQ-4.1.5–4.1.6 | `/api/patients/*` | `apps/patients/views.py`, `models.py` |
| UC-1.4 Quality gate | REQ-4.1.7–4.1.8 | `POST .../upload/`, `POST .../analyse/` | `ai/scripts/quality.py`, `apps/imaging/views.py` |
| UC-2.1 Queue | REQ-4.2.1 | `GET /api/imaging/queue/` | `apps/imaging/views.py`, `serializers.py` |
| UC-2.2 Review session | REQ-4.2.2–4.2.3 | `GET /api/imaging/xray/<id>/` | `apps/imaging/models.py`, `views.py` |
| UC-2.3 Annotation | REQ-4.2.4–4.2.5 | `POST /api/imaging/xray/<id>/annotate/` | `frontend/src/components/imaging/AnnotationCanvas.jsx`, `AnnotationPanel.jsx` |
| UC-2.4 Structured report | REQ-4.2.6–4.2.9 | `/api/imaging/xray/<id>/report/` | `apps/imaging/models.py`, `serializers.py`, `views.py` |
| UC-2.5 Annotation submit | REQ-4.2.10–4.2.11 | `POST /api/imaging/xray/<id>/annotate/` | `apps/imaging/views.py` |
| UC-3.1 AI scoring | REQ-4.3.1–4.3.4 | `POST /api/imaging/xray/<id>/analyse/` | `ai/scripts/inference.py`, `apps/imaging/views.py` |
| UC-3.2 History | REQ-4.3.5 | `/api/imaging/patients/<id>/history/` | `apps/imaging/views.py` |
| UC-3.3 Progression | REQ-4.3.6–4.3.8 | `.../progression/`, `.../progression/override/` | `apps/imaging/services.py`, `models.py`, `views.py` |
| UC-3.4 PDF report | REQ-4.3.9–4.3.10 | `GET .../report/generate/` | `apps/imaging/views.py`, `pdf_scripts/generate.js`, `templates/reports/xray_report.html` |
| UC-4.1 Auth/RBAC | REQ-4.4.1–4.4.3 | `/accounts/*` | `apps/accounts/views.py`, `decorators.py`; `frontend/src/context/AuthContext.jsx` |
| UC-4.2 Dashboards | REQ-4.4.4–4.4.5 | role dashboard endpoints | `apps/imaging/views.py`; `frontend/src/pages/dashboard/*` |
| UC-4.3 Notifications | REQ-4.4.6–4.4.7 | `/api/imaging/notifications/*` | `apps/imaging/views.py`; `frontend/src/components/layout/Header.jsx` |
| UC-4.4 Analytics | REQ-4.4.8–4.4.9 | `/api/analytics/summary/`, `/api/analytics/export/` | `apps/imaging/views.py`; `frontend/src/pages/dashboard/AnalyticsDashboardPage.jsx` |
| UC-4.5 Backup/restore | REQ-4.4.10–4.4.11 | (CLI scripts) | `backend/scripts/backup.py`, `restore.py`, `backup_lock.py` |
| Non-functional | REQ-6.x | — | `TBXR/settings.py`, `documentation/*`, `ai/model_resources/*` |

---

# Appendix B: API Endpoint Catalog

All endpoints use session authentication and CSRF as described in Section 3.4. Role abbreviations: T = `RADIOLOGIC_TECH`, R = `RADIOLOGIST`, P = `PHYSICIAN`, Auth = any authenticated.

## Accounts
| Method | Path | Role |
| :---- | :---- | :---- |
| GET | `/accounts/csrf-token/` | Public |
| POST | `/accounts/login/` | Public |
| POST | `/accounts/logout/` | Auth |

## Patients
| Method | Path | Role |
| :---- | :---- | :---- |
| GET | `/api/patients/` | T, R, P |
| POST | `/api/patients/register/` | T |
| GET | `/api/patients/search/?name=` | T, R, P |
| GET | `/api/patients/<patient_id>/` | T, R, P |

## Imaging
| Method | Path | Role |
| :---- | :---- | :---- |
| POST | `/api/imaging/patients/<patient_id>/xray/upload/` | T |
| GET | `/api/imaging/patients/<patient_id>/xray/upload/confirm/<transaction_id>/` | T |
| POST | `/api/imaging/xray/<transaction_id>/annotate/` | R |
| POST | `/api/imaging/xray/<transaction_id>/analyse/` | T |
| GET | `/api/imaging/patients/<patient_id>/xray/` | T, R, P |
| GET | `/api/imaging/patients/<patient_id>/history/` | T, R, P |
| GET | `/api/imaging/cases/<case_id>/progression/` | Auth |
| POST | `/api/imaging/cases/<case_id>/progression/override/` | R |
| GET | `/api/imaging/patients/<patient_id>/progression/` | Auth |
| GET | `/api/imaging/dashboard/technologist/` | T |
| GET | `/api/imaging/physician/dashboard/` | P |
| GET | `/api/imaging/queue/` | R |
| GET | `/api/imaging/xray/<transaction_id>/` | T, R, P |
| GET/POST/PATCH | `/api/imaging/xray/<transaction_id>/report/` | R |
| GET | `/api/imaging/xray/<transaction_id>/report/generate/` | R |
| GET | `/api/imaging/notifications/` | Auth |
| POST | `/api/imaging/notifications/<notification_id>/mark-read/` | Auth |
| GET | `/api/imaging/analytics/summary/` | R, P |
| POST | `/api/imaging/analytics/export/` | R, P |

## Analytics / Physician (project-level aliases)
| Method | Path | Role |
| :---- | :---- | :---- |
| GET | `/api/analytics/summary/` | R, P |
| POST | `/api/analytics/export/` | R, P |
| GET | `/api/physician/dashboard` and `/api/physician/dashboard/` | P |

## Documentation
| Method | Path | Access |
| :---- | :---- | :---- |
| GET | `/api/schema/` | Public in DEBUG; staff-only otherwise |
| GET | `/api/docs/` | Public in DEBUG; staff-only otherwise |

**Query parameters of note**
- Queue/Technologist dashboard: `page`, `search`, `status`, `risk_label`.
- Physician dashboard: `severity`, `date_from`, `date_to`.
- Analytics summary/export: `date_from`, `date_to`, `severity`; export body includes `format` (`csv`/`pdf`) and `filters`.
- Progression history: paginated (page size 25, max 100).

**Canonical enum values**
- XrayRecord status: `PENDING`, `IN_REVIEW`, `AI_REVIEWED`, `MANUAL_REVIEW`, `COMPLETED`.
- AI risk label: `LOW`, `MODERATE`, `HIGH`.
- Report severity: `NORMAL`, `MILD`, `MODERATE`, `SEVERE`, `CRITICAL`.
- Report status: `DRAFT`, `SUBMITTED`.
- Progression status: `no_prior`, `stable`, `decreased_risk`, `increased_risk`.
- Patient sex: `M`, `F`, `O`.

---

*End of document.*

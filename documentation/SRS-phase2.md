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
| 2.0 | September 25, 2026 | Borgonia, J.D.; Emia, S.N.; Enario, L.J.L.; Epan, R.S.; Tolentino, B. | Refactored to describe the as-built system, emphasizing endpoints, status lifecycles, and code-level traceability. |
| 3.0 | October 2, 2026 | Borgonia, J.D.; Emia, S.N.; Enario, L.J.L.; Epan, R.S.; Tolentino, B. | Rewritten in capability-based language so the SRS reads as a forward-looking development guide rather than a description of the current source code. Specific implementation values were replaced with descriptive intent; technical detail is deferred to the design documentation. |

> **About this revision.** This document describes *what TB-XR is required to do*, not *how the current code happens to do it*. Requirements are stated as capabilities and behaviour so that they remain stable even as the implementation evolves. Implementation specifics — technologies, endpoints, data structures, and exact tuned values — belong to the Software Design Description (`documentation/SDD.md`) and the backend endpoint reference (`backend/ENDPOINTS.md`), and are deliberately kept out of this SRS. Where a requirement is aspirational rather than yet demonstrated, it is labelled **Target**; where a capability is designed but not yet present, it is labelled **Planned**. The prior version of this document, which was written tightly against the codebase, is preserved as `documentation/refactored-SRS.md`.

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
   5. [Cross-cutting: Record and Report Lifecycles](#45-cross-cutting-record-and-report-lifecycles)
   6. [Cross-cutting: Role-Based Access Control](#46-cross-cutting-role-based-access-control)
5. [Data Requirements](#5-data-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
   1. [Performance and Responsiveness](#61-performance-and-responsiveness)
   2. [Security and Privacy](#62-security-and-privacy)
   3. [Reliability and Availability](#63-reliability-and-availability)
   4. [Usability](#64-usability)
   5. [Maintainability and Testability](#65-maintainability-and-testability)
   6. [Regulatory and Ethical Compliance](#66-regulatory-and-ethical-compliance)
7. [Known Limitations and Future Work](#7-known-limitations-and-future-work)
8. [Appendix A: Traceability Matrix](#appendix-a-traceability-matrix)

---

# 1. Introduction

## 1.1 Purpose

This document specifies the functional and non-functional requirements of **TB-XR**, a collaborative, AI-integrated teleradiology platform for pulmonary tuberculosis (TB) screening. It is intended for developers, project managers, clinical stakeholders, and thesis evaluators, and it aligns with the structure recommended by IEEE Std 830-1998.

The document is written as a **guide for development**: it states the intended behaviour of the system in plain, capability-based terms so that each requirement can be designed, built, and verified independently of any particular implementation. It does not prescribe code structure, frameworks, formulae, or tuned constants; those decisions are recorded in the Software Design Description and related technical documents.

## 1.2 Scope

TB-XR is a role-based, web-based clinical decision support platform that supports an end-to-end TB chest X-ray screening workflow: secure image ingestion, automated standardization, AI-assisted risk triage, human-in-the-loop annotation and structured diagnostic reporting, longitudinal progression monitoring, and role-specific dashboards with consolidated analytics.

The system is organized into four modules:

- **Module 1 — X-ray Ingestion and Data Management**: capture of chest X-rays with patient metadata, normalization and de-identification of incoming images, image quality gating, and centralized patient profiling.
- **Module 2 — Annotation and Diagnostic Review**: remote review queue, concurrency-safe review sessions, interactive annotation, and structured diagnostic report composition and submission.
- **Module 3 — AI Engine and Longitudinal Monitoring**: AI-informed baseline risk scoring with explainability overlays, historical record retrieval, comparative progression tracking, clinician progression override, and comprehensive report generation.
- **Module 4 — Clinical Dashboards and Reporting**: authentication and role-based access control, role-specific dashboards, in-system notifications, and consolidated analytics with export.

**In scope:** secure session-based login and logout; patient registration, search, and profiles; chest X-ray upload with de-identification and preprocessing; automated AI risk scoring and explainability heatmap generation; radiologist review queue, review locking, and annotation; structured diagnostic reports with a draft/submit lifecycle; physician notification and physician dashboard; progression computation with trend data and manual override; per-case and consolidated report export; analytics summary; and automated backup and restore tooling.

**Out of scope (boundaries):**

- **Direct PACS/DICOM network integration** — images are uploaded manually as files; the system does not route over DICOM network protocols.
- **Autonomous diagnosis or chart signing** — the AI engine emits an informational risk score only; final diagnostic authority remains with authenticated human Radiologists and Physicians.
- **Definitive multi-disease diagnosis** — the AI component is a generalized risk triage aid and does not issue differentiated diagnoses for non-TB pathologies.
- **Pharmaceutical or treatment workflows** — no prescription, medication compliance, or appointment scheduling logic.
- **Model training pipeline** — model training happens offline; the deployed system only performs inference on already-trained models.
- **Regulatory certification** (e.g., FDA, DOH) and full hospital information system (HIS) integration.

## 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
| :---- | :---- |
| **AI** | Artificial Intelligence. |
| **AI-assisted triage** | Use of a trained model to estimate TB risk and prioritize images for human review. |
| **CAD** | Computer-Aided Detection/Diagnosis. |
| **CLAHE** | Contrast Limited Adaptive Histogram Equalization; the contrast-enhancement step applied during image standardization. |
| **CNN** | Convolutional Neural Network; the class of model used for image-based risk scoring. |
| **CSRF** | Cross-Site Request Forgery; a class of web request-forgery attack the system guards against. |
| **CXR** | Chest X-Ray. |
| **DICOM** | Digital Imaging and Communications in Medicine; the standard format for medical imaging files. |
| **De-identification** | Removal of patient-identifying information from an image or record before storage or analysis. |
| **Grad-CAM** | Gradient-weighted Class Activation Mapping; a technique that produces the explainability heatmap overlay. |
| **HITL** | Human-in-the-loop; the workflow model requiring human clinical verification of AI output. |
| **LAN** | Local Area Network. |
| **PACS** | Picture Archiving and Communication System. |
| **PHI/PII** | Protected Health Information / Personally Identifiable Information. |
| **RBAC** | Role-Based Access Control. |
| **ROI** | Region of Interest; a marked area on an image. |
| **SRS** | Software Requirements Specification. |
| **SUS** | System Usability Scale. |
| **TB** | Tuberculosis. |
| **TB-XR** | The collaborative teleradiology platform specified herein. |
| **Transaction ID** | A unique, non-reusable identifier assigned to each X-ray screening case. |

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

**Project documents** (technical detail beyond the scope of this SRS)
- `documentation/SDD.md` — Software Design Description; source of architectural and implementation detail.
- `documentation/refactored-SRS.md` — the prior, code-grounded requirements revision.
- `backend/ENDPOINTS.md` — backend endpoint reference.
- `documentation/SECURITY-ENV-PROFILE.md` — production security profile.
- `documentation/backup-restore.md` — backup and restore runbook.
- `documentation/progression-service.md` — progression rule engine specification.
- `documentation/CODING-STANDARDS.md` — team coding standards.
- `documentation/Software Proposal.md`, `documentation/VALIDATION-ROADMAP.md`, `documentation/SIX-WEEK-SPRINT.md` — proposal, validation plan, and sprint backlog.
- Sequence and class diagrams for each module, maintained under `documentation/sequence diagrams/` and `documentation/class diagrams/`.

## 1.5 Document Conventions

- **MUST / SHALL** denotes a mandatory requirement; **SHOULD** denotes a recommended requirement; **MAY** denotes optional behaviour.
- Requirement identifiers use `REQ-<module>.<n>`; use cases use `UC-<module>.<n>`.
- Requirements describe *intent and observable behaviour*. Exact numeric limits, tuned values, protocols, and algorithms are stated only when they are part of the required behaviour, and are otherwise deferred to the design documentation.
- **[Present]** means the capability is available in the current system. **[Target]** means a defined but as-yet-unverified objective. **[Planned]** means designed but not yet built.
- This SRS does not reference source files, endpoints, or data field names; readers seeking that level of detail should consult the documents listed in Section 1.4.

---

# 2. Overall Description

## 2.1 Product Perspective

TB-XR is a self-contained, semi-integrated client–server application that complements existing clinical workflows. It does not replace a PACS or HIS; it digitizes image handling, AI-assisted triage, diagnostic annotation, and longitudinal monitoring, and it presents its results alongside the clinician's own judgement.

The platform follows a browser-based client/server model. Clinicians work through a role-appropriate web interface; the server hosts the clinical data, coordinates the screening workflow, performs image preparation and AI-assisted scoring, and produces reports. AI analysis and report rendering are provided as internal services of the platform rather than as separate systems that the user must operate.

**Major external interfaces:** digital radiography image files (DICOM/JPEG/PNG) supplied as uploads; a pre-trained AI model for risk scoring; a report-rendering component that produces print-ready documents; and a relational database for clinical data. The detailed technology choices behind each of these are recorded in `documentation/SDD.md`.

## 2.2 Product Functions

- Secure, session-based login with role-directed landing.
- Role-based access control across all workflows (Technologist, Radiologist, Physician).
- Patient registration, listing, name search, and profiles.
- Chest X-ray upload with format and size validation, conversion of medical image formats, and removal of patient-identifying information.
- Automated image standardization to prepare every image consistently for review and analysis.
- Image quality assessment with a user-confirmable override.
- Automated AI-assisted baseline risk scoring with a risk label and an explainability heatmap.
- Graceful AI failure handling that routes affected cases to manual review.
- Radiologist review queue with search, filters, and paging, plus concurrency-safe review locking.
- Interactive image annotation (rectangle, circle, freehand) with notes, undo, and delete.
- Structured diagnostic report composition with draft save, validation, and finalization.
- In-system notification of report readiness to physicians.
- Patient history retrieval and side-by-side longitudinal comparison.
- Disease progression computation with trend data and a logged clinician override.
- Comprehensive per-case report generation.
- Role-specific dashboards (Technologist, Radiologist, Physician) and a shared analytics dashboard.
- Consolidated analytics summary with export.
- Automated database and media backup and restore tooling.

## 2.3 User Classes and Characteristics

| User class | Description | Technical proficiency | Primary needs |
| :---- | :---- | :---- | :---- |
| **Radiologic Technologist** | Operates radiography equipment; captures and submits patient images. | Moderate; familiar with image capture and basic data entry. | Intuitive upload and patient data entry; clear validation feedback. |
| **Radiologist** | Medical specialist interpreting medical images. | High within specialized tools. | Efficient queue triage, precise annotation, fast reporting; time-sensitive. |
| **Physician (Attending)** | Reviews finalized reports; supports clinical decisions. | Variable; accustomed to EMR and report systems. | Clear, concise, interpretable outputs; consolidated reporting. |

Across all roles, basic computing literacy is assumed. Deployment environments may include resource-limited settings, reinforcing the need for accessible, low-bandwidth interactions.

## 2.4 Operating Environment

- **Client:** a modern, standards-compliant web browser on a standard laptop or desktop; keyboard and mouse are the primary input devices, with touch input optional.
- **Server:** a local edge server located within the facility.
- **Network:** the facility LAN/Wi-Fi with stable internal connectivity, sufficient to transfer typical chest X-ray images (in the range of 5–10 MB). Internet connectivity is not required for core screening operations.
- **Supporting runtimes:** a relational database, an AI inference runtime, and a document-rendering runtime for report export.

Specific minimum hardware, browser versions, and software versions are recorded in `documentation/SDD.md` and `documentation/SETUP.md`.

## 2.5 Design and Implementation Constraints

- **REQ-2.5.1 [Present]** Core screening operations MUST function on a local network without external internet access.
- **REQ-2.5.2 [Present]** The platform MUST operate within modest, low-resource hardware, consistent with deployment in resource-limited clinical settings.
- **REQ-2.5.3 [Present]** The system MUST accept common chest X-ray image formats, including medical imaging and ordinary image files, and MUST normalize them for consistent display and analysis.
- **REQ-2.5.4 [Present]** AI output MUST be presented as a non-definitive, assistive baseline, accompanied by a visible disclaimer that cannot be permanently dismissed.
- **REQ-2.5.5 [Present]** No patient-identifying information may be stored or transmitted over unencrypted channels, and uploaded medical images MUST be de-identified before storage or analysis.
- **REQ-2.5.6 [Present]** The system MUST enforce a maximum upload size and an allowed set of image file types, rejecting anything outside those limits with a clear message.
- **REQ-2.5.7 [Present]** When deployed in a production profile, the system MUST disable developer/debug behaviour, require secure configuration values, and refuse to run with development-only host settings.
- **REQ-2.5.8 [Present]** The AI model MUST be a pre-trained model loaded by the running system; model training is out of scope at runtime.
- **REQ-2.5.9 [Present]** The system deliberately excludes PACS networking, cloud object storage, autonomous diagnosis, and treatment workflows.

## 2.6 Assumptions and Dependencies

- **Trained model availability:** AI-assisted scoring depends on a valid, uncorrupted trained model being available to the running system; when it is not, cases route to manual review rather than producing a score.
- **Model conformance:** the model is assumed to meet the accepted performance baseline on the reference dataset (Section 6.1).
- **Digital radiography capability:** source machines produce digital images without requiring additional conversion hardware.
- **Database availability:** the configured database is running and reachable before deployment.
- **Report-rendering availability:** report export depends on the document-rendering runtime being present; when unavailable, export fails (Section 7).
- **Persistent local storage:** a local, persistent media store of adequate capacity is available; cloud object storage is intentionally excluded in line with RA 10173.
- **Backup host:** the backup and restore tooling assumes a POSIX-style host; a Windows host is not supported by the file-locking mechanism.
- **User literacy:** users have basic web literacy for file uploads and interface navigation.

---

# 3. External Interface Requirements

## 3.1 User Interfaces

TB-XR presents a single-page, browser-based interface in which navigation and available actions adapt to the signed-in user's role. The interface is composed of a shared frame — navigation, header, and a persistent AI disclaimer — around role-specific pages.

The system MUST provide the following user-facing areas:

| Area | Intended users | Purpose |
| :---- | :---- | :---- |
| **Sign-in** | All | Authenticate and be directed to the appropriate dashboard. |
| **Technologist dashboard** | Technologist | Track and manage the images this technologist has submitted. |
| **Radiologist dashboard** | Radiologist | Triage and open cases from the review queue. |
| **Review workspace** | Radiologist | Inspect an image, view AI output, annotate, and record findings. |
| **Report workspace** | Radiologist | Compose, save, and submit the structured diagnostic report. |
| **Physician dashboard** | Physician | Review finalized reports, alerts, and patient progress. |
| **Analytics dashboard** | Radiologist, Physician | Explore consolidated metrics and export them. |
| **Patient pages** | Clinical roles | Register, search, and view patient profiles and history. |

- **REQ-3.1.1 [Present]** The user interface MUST expose role-appropriate navigation and actions derived from the authenticated user's role.
- **REQ-3.1.2 [Present]** A non-dismissible AI disclaimer MUST be visible on every clinical surface of the application.
- **REQ-3.1.3 [Present]** The interface MUST provide interactive annotation tooling supporting rectangle, circle, and freehand regions, with label assignment, notes, undo, and delete.
- **REQ-3.1.4 [Present]** The interface MUST provide an image viewer with zoom and pan, and an optional explainability heatmap overlay.
- **REQ-3.1.5 [Present]** The interface MUST provide a notification indicator with an unread count and controls to mark notifications as read.
- **REQ-3.1.6 [Present]** The interface MUST present validation feedback clearly when a user submits incomplete or invalid data.

## 3.2 Hardware Interfaces

- **a) Radiography equipment (indirect):** the system does not control radiographic machines; it consumes exported image files.
- **b) User access devices:** desktops, laptops, and mobile/tablet browsers; keyboard and mouse primary, touch optional.
- **c) Display:** rendering of high-resolution chest X-ray images; medical-grade monitors are not required but are recommended for radiologists.

## 3.3 Software Interfaces

- **Database:** a relational database stores clinical records (see Section 5).
- **Web browsers:** modern evergreen browsers supporting standard web technologies.
- **AI engine:** an internal inference component that scores prepared images and produces an explainability heatmap.
- **Image processing:** components that convert, de-identify, and standardize uploaded images.
- **Report renderer:** a component that turns report content into a print-ready document.
- **Public interface documentation:** the system MUST expose a machine-readable description of its interfaces for developers and integrators.

Specific products, versions, and library choices are recorded in `documentation/SDD.md`.

## 3.4 Communications Interfaces

- **Transport:** all client–server traffic MUST be encrypted over HTTPS in production, with secure cookies and strict transport enforcement.
- **Interface style:** the system exposes a structured, resource-oriented interface for its clinical operations, consumed by the browser client.
- **Session security:** authenticated sessions MUST be protected against request-forgery attacks on state-changing operations.
- **Media delivery:** uploaded and processed images MUST be served only to authorized, authenticated users.

Concrete endpoint paths, headers, and payload shapes are documented in `backend/ENDPOINTS.md`.

---

# 4. System Features (Functional Requirements)

Each feature below states the intended behaviour of the system. Use cases describe the interaction from the actor's point of view; the numbered requirements that follow are the testable statements of intent.

## 4.1 Module 1: X-ray Ingestion and Data Management

### 4.1.1 UC-1.1 Secure Image and Metadata Upload

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.1 |
| **Primary Actor** | Radiologic Technologist |
| **Secondary Actor** | System (TB-XR) |
| **Preconditions** | The Technologist is authenticated; a target patient profile exists, or will be created first. |
| **Postconditions** | A new screening case is created and linked to the patient and the uploading technologist, and AI-assisted scoring is attempted. |
| **Main Success Scenario** | 1. The Technologist opens the patient's profile and chooses to upload an X-ray. 2. The Technologist selects a supported image file within the allowed size and submits it. 3. The system validates the file type and size. 4. If the file is in a medical imaging format, the system converts it to a displayable image. 5. The system removes patient-identifying information, standardizes the image, and prepares it for analysis. 6. The system automatically attempts AI-assisted risk scoring. 7. The case is returned to the client with its updated status. |
| **Alternative Flows** | **AF-1 (Low-quality image):** if the image quality is below the acceptable level, the system does not score it and instead prompts the Technologist to either proceed anyway or upload a replacement. |
| **Exception Flows** | **EF-1 (Unsupported or oversized file):** the system rejects the upload and displays a clear validation message. **EF-2 (Unreadable or corrupt image):** the system aborts the upload, discards the incomplete case, and reports the error. **EF-3 (Standardization failure):** the system aborts the upload, discards the incomplete case, and reports the error. |
| **Access** | Restricted to the Radiologic Technologist role. |

- **REQ-4.1.1 [Present]** Only a Radiologic Technologist MUST be able to upload X-ray images.
- **REQ-4.1.2 [Present]** The system MUST reject files that are not of an allowed image type or that exceed the maximum permitted size, with a clear message to the user.
- **REQ-4.1.3 [Present]** The system MUST assign each accepted case a unique, non-reusable transaction identifier and link it to the patient and the uploading technologist.

### 4.1.2 UC-1.2 Automated Image Standardization

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.2 |
| **Primary Actor** | System (TB-XR) |
| **Preconditions** | An image has been uploaded and a case created. |
| **Postconditions** | A standardized version of the image is stored and is ready for review and analysis. |
| **Main Success Scenario** | 1. The system reads the uploaded or converted image in a consistent form. 2. The system enhances contrast to compensate for variation between sources. 3. The system saves the standardized image. 4. The system prepares a normalized representation suitable for the AI component to consume. |
| **Exception Flows** | **EF-1 (Standardization failure):** the upload is aborted, the incomplete case is discarded, and the error is reported. |
| **Access** | Internal to the upload pipeline. |

- **REQ-4.1.4 [Present]** The system MUST automatically enhance contrast and normalize every accepted image so that images from different sources are presented and analyzed consistently.
- **REQ-4.1.5 [Present]** The system MUST prepare an analysis-ready representation of each standardized image.

### 4.1.3 UC-1.3 Centralized Patient Profiling and Storage

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.3 |
| **Primary Actor** | Radiologic Technologist |
| **Secondary Actor** | System (TB-XR) |
| **Preconditions** | The Technologist is authenticated. |
| **Postconditions** | A patient master record is created and indexed; patients can be listed, searched, and retrieved. |
| **Main Success Scenario** | 1. The Technologist opens the Patients page. 2. The Technologist submits a new-patient form with the required demographics. 3. The system validates the input and saves the patient. 4. The Technologist may search for a patient by name or open a patient profile. |
| **Exception Flows** | **EF-1 (Validation error):** the system rejects incomplete or invalid input with field-level messages. **EF-2 (Wrong role):** a user without the Technologist role is refused. |
| **Access** | Registration restricted to the Technologist role; viewing available to all clinical roles. |

- **REQ-4.1.6 [Present]** Patient registration MUST be restricted to the Radiologic Technologist role.
- **REQ-4.1.7 [Present]** Patient listing, search, and profile viewing MUST be available to authenticated clinical roles.

### 4.1.4 UC-1.4 Image Quality Gate

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-1.4 |
| **Primary Actor** | System (TB-XR) |
| **Secondary Actor** | Radiologic Technologist |
| **Preconditions** | An image has been uploaded and standardization has been initiated. |
| **Postconditions** | Either AI-assisted scoring proceeds, or the Technologist is prompted to confirm or replace the image. |
| **Main Success Scenario** | 1. The system assesses the technical quality of the image, considering factors such as resolution, exposure, contrast, and sharpness. 2. If the image meets the acceptable quality level, processing continues to AI-assisted scoring. 3. If the image falls below that level, the system pauses the workflow and asks the Technologist to either proceed anyway or upload a replacement. 4. If the Technologist proceeds, the system records the decision and continues. |
| **Exception Flows** | **EF-1 (Proceed override):** the override decision is recorded before scoring continues. |
| **Access** | Restricted to the Radiologic Technologist role for the override decision. |

- **REQ-4.1.8 [Present]** The system MUST assess image quality using a consistent, repeatable measure before AI-assisted scoring.
- **REQ-4.1.9 [Present]** The system MUST NOT silently discard a low-quality image. It MUST present an explicit choice to proceed or replace the image, and MUST record any decision to proceed on a low-quality image.

## 4.2 Module 2: Annotation and Diagnostic Review

### 4.2.1 UC-2.1 Remote Access Queue

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.1 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist is authenticated and at least one case exists. |
| **Postconditions** | A paginated, filterable list of cases is presented, with AI output where available. |
| **Main Success Scenario** | 1. The Radiologist opens the Radiologist dashboard. 2. The system presents cases, ordered by recency by default. 3. Each entry summarizes the patient, the case identifier, when it was uploaded, who uploaded it, its current status, and any AI score or label. 4. The Radiologist may search and filter the queue by status and by AI risk label. |
| **Alternative Flows** | **AF-1 (Empty queue):** the system presents a clear empty state. |
| **Exception Flows** | **EF-1 (Retrieval error):** the system displays an error message without disrupting the rest of the dashboard. |
| **Access** | Restricted to the Radiologist role. |

- **REQ-4.2.1 [Present]** The review queue MUST support free-text search and filtering by case status and AI risk label, and MUST page through results for large queues.

### 4.2.2 UC-2.2 Concurrency-Safe Review Session

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.2 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist opens a case for review. |
| **Postconditions** | The case is rendered in the review workspace, its status reflects that review is under way, and an exclusive review lock is held by this Radiologist. |
| **Main Success Scenario** | 1. The Radiologist selects a case from the queue. 2. The system grants an exclusive review lock to this Radiologist and marks the case as under review. 3. The workspace presents the image, AI output, annotation tools, and the patient's history. |
| **Alternative Flows** | **AF-1 (Locked by another):** if another Radiologist already holds the lock, the system opens the case in read-only mode, identifies the current reviewer, and disables editing. |
| **Exception Flows** | **EF-1 (Expired lock):** a lock that has been held beyond the configured review timeout is treated as expired and may be acquired by another Radiologist. |
| **Access** | Restricted to the Radiologist role for editing; viewing may be broader. |

- **REQ-4.2.2 [Present]** The system MUST prevent two Radiologists from editing the same case simultaneously by issuing an exclusive review lock.
- **REQ-4.2.3 [Present]** A review lock MUST expire automatically after a configurable period of inactivity so that abandoned reviews do not block other clinicians.

### 4.2.3 UC-2.3 Interactive Annotation

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.3 |
| **Primary Actor** | Radiologist |
| **Preconditions** | An image is open in an editable review session. |
| **Postconditions** | One or more regions of interest, with labels and notes, are captured for submission. |
| **Main Success Scenario** | 1. The Radiologist selects an annotation tool (rectangle, circle, or freehand). 2. The Radiologist draws a region of interest on the image. 3. The system renders the overlay and prompts for a label. 4. The Radiologist may add further regions, undo the most recent action, or delete a region. 5. The Radiologist adds a diagnostic note. |
| **Alternative Flows** | **AF-1 (Delete region):** the selected region is removed. **AF-2 (Undo):** the most recent annotation action is reverted. |
| **Access** | Restricted to the Radiologist role. |

- **REQ-4.2.4 [Present]** The annotation toolset MUST support rectangle, circle, and freehand region drawing, label assignment, deletion, and undo.
- **REQ-4.2.5 [Present]** Annotations MUST be stored independently of display size so that regions remain accurate at any zoom or screen resolution, and MUST retain their labels and associated notes.

### 4.2.4 UC-2.4 Structured Diagnostic Report

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.4 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The Radiologist is authenticated and a case exists. |
| **Postconditions** | A report exists for the case in either a draft or a finalized state. |
| **Main Success Scenario** | 1. The Radiologist opens the report page for a case. 2. The system pre-populates any existing draft. 3. The Radiologist completes the report's sections — findings, impression, recommendation, and severity. 4. The Radiologist may save a draft, which remains editable. 5. On submission, the system validates the required sections, records the author, finalizes the report, and notifies the relevant physician. 6. A finalized report becomes read-only. |
| **Alternative Flows** | **AF-1 (Edit before submit):** the Radiologist may save or update the draft any number of times before submission. |
| **Exception Flows** | **EF-1 (Validation error):** missing required content blocks submission, and the interface highlights what is missing. **EF-2 (Modify after finalization):** attempts to change a finalized report are refused. |
| **Access** | Restricted to the Radiologist role. |

- **REQ-4.2.6 [Present]** The report MUST capture findings, impression, recommendation, and a severity assessment.
- **REQ-4.2.7 [Present]** The system MUST allow a report to be saved as an editable draft and MUST validate required content before final submission.
- **REQ-4.2.8 [Present]** Once submitted, a report MUST be immutable.
- **REQ-4.2.9 [Present]** Report authoring and submission MUST be restricted to the Radiologist role.
- **REQ-4.2.10 [Present]** Submitting a report MUST notify the relevant physician in-system.

### 4.2.5 UC-2.5 Annotation Submission and Case Completion

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-2.5 |
| **Primary Actor** | Radiologist |
| **Preconditions** | An active review session exists with at least one marked region. |
| **Postconditions** | The annotation is saved and the case is marked complete. |
| **Main Success Scenario** | 1. The Radiologist submits findings. 2. The system saves the annotation, including marked regions and notes, and marks the case complete. 3. The Radiologist returns to the queue. |
| **Exception Flows** | **EF-1 (No regions marked):** submission without at least one region is refused with a clear message. |
| **Access** | Restricted to the Radiologist role. |

- **REQ-4.2.11 [Present]** Submitting findings MUST require at least one marked region and MUST mark the case complete.
- **REQ-4.2.12 [Present]** Annotations MUST be attributable to the Radiologist who submitted them.

## 4.3 Module 3: AI Engine and Longitudinal Monitoring

### 4.3.1 UC-3.1 AI-Assisted Baseline Risk Scoring

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.1 |
| **Primary Actor** | System (automated) |
| **Secondary Actor** | Radiologist |
| **Preconditions** | A standardized, quality-accepted image exists for the case. |
| **Main Success Scenario** | 1. The system submits the prepared image to the AI model. 2. The model returns a TB risk estimate, which the system records alongside the model version. 3. The system produces an explainability heatmap highlighting the image regions that most influenced the estimate. 4. The case status is updated to reflect that AI output is available. |
| **Alternative Flows** | **AF-1 (Score outside the valid range):** treated as an inference failure and routed to manual review. |
| **Exception Flows** | **EF-1 (Model unavailable or inference error):** the system records the failure, marks the case for manual review, and notifies the radiologists. It MUST NOT present a stale, default, or fabricated score. |
| **Access** | Automatic; re-running analysis is available to the Radiologic Technologist. |

- **REQ-4.3.1 [Present]** The system MUST estimate TB risk using the configured AI model and MUST record the estimate together with the model version that produced it.
- **REQ-4.3.2 [Present]** The system MUST generate an explainability heatmap, when possible, and attach it to the AI output.
- **REQ-4.3.3 [Present]** On inference failure, the system MUST mark the case for manual review, record the reason, and notify the radiologists; it MUST NOT present a stale or default score.
- **REQ-4.3.4 [Present]** AI output MUST be presented as an assistive baseline only, never as a diagnosis.
- **REQ-4.3.5 [Target]** The AI baseline score SHOULD be produced within a few seconds of image acceptance; measured mean inference on the reference host is well under one second (Section 6.1).

> **Note on risk labels.** The system distinguishes risk levels for prioritization, but the currently deployed model produces a binary high/low decision. Any intermediate or moderate level in the data is therefore not emitted by inference today (Section 7).

> **Note on retries.** Automated retry before declaring AI unavailable is not currently performed; the first failure routes the case to manual review.

### 4.3.2 UC-3.2 Historical Record Retrieval

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.2 |
| **Primary Actor** | System (automated) |
| **Secondary Actor** | Radiologist |
| **Preconditions** | A patient workspace is opened. |
| **Postconditions** | All prior cases for the patient are retrieved in chronological order, or a clear empty state is shown. |
| **Main Success Scenario** | 1. The system identifies the patient. 2. The system retrieves that patient's previous cases in chronological order, together with AI output and annotations. 3. The system populates the longitudinal panel and image thumbnails. |
| **Alternative Flows** | **AF-1 (No history):** the system shows a clear first-visit / no-history message. |
| **Exception Flows** | **EF-1 (Retrieval error):** a non-intrusive message is shown and the current review continues unaffected. |
| **Access** | Available to authenticated clinical roles. |

- **REQ-4.3.6 [Present]** The system MUST retrieve a patient's history in chronological order for longitudinal review.

### 4.3.3 UC-3.3 Comparative Progression Tracking and Override

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.3 |
| **Primary Actor** | System (automated) |
| **Secondary Actor** | Radiologist |
| **Preconditions** | The patient has a current risk estimate and, for comparison, at least one earlier valid estimate. |
| **Postconditions** | A progression status and trend data are available for the patient; any override is recorded and auditable. |
| **Main Success Scenario** | 1. The system identifies the current risk estimate and the most recent earlier valid estimate for the patient. 2. The system classifies the change as stable, decreased risk (improvement), or increased risk (deterioration); when there is no earlier estimate, it reports that no comparison is available. 3. The system records a progression snapshot and exposes trend data. 4. The interface presents the change as a trend. |
| **Alternative Flows** | **AF-1 (No comparable prior):** the system reports that no comparison is available and plots only the points it has. **AF-2 (Clinician override):** a Radiologist may set the progression status manually; a clinical note is mandatory, and the override is recorded for audit. |
| **Exception Flows** | **EF-1 (Invalid input):** the system rejects an invalid comparison configuration or score rather than silently substituting a default. |
| **Access** | Retrieval available to authenticated users; override restricted to the Radiologist role. |

- **REQ-4.3.7 [Present]** The system MUST compare the current risk estimate with the patient's most recent earlier valid estimate and classify the change as stable, improvement, deterioration, or not comparable.
- **REQ-4.3.8 [Present]** The classification MUST apply a configurable stability threshold so that small changes are not misreported as significant.
- **REQ-4.3.9 [Present]** The system MUST support a Radiologist override of the computed progression status, requiring a mandatory clinical note.
- **REQ-4.3.10 [Present]** Every progression override MUST be recorded in an audit log capturing the actor, the previous and new status, the note, and the time.
- **REQ-4.3.11 [Present]** Progression retrieval MUST be available to authenticated users; override MUST be restricted to the Radiologist role.

> **Note.** Comparison currently uses the most recent prior case that has a valid AI estimate, regardless of that case's workflow status (Section 7).

### 4.3.4 UC-3.4 Comprehensive Report Generation

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-3.4 |
| **Primary Actor** | Radiologist |
| **Preconditions** | The case has been marked complete. |
| **Postconditions** | A print-ready report is delivered to the user. |
| **Main Success Scenario** | 1. The Radiologist requests report generation. 2. The system assembles patient demographics, the AI score and label, the explainability heatmap, annotations, and the clinical text. 3. The system renders the content into a print-ready document. 4. The document is delivered to the browser. |
| **Exception Flows** | **EF-1 (Case not complete):** the request is refused with a clear message. **EF-2 (Rendering failure):** the system reports the failure and provides diagnostic detail. |
| **Access** | Restricted to the Radiologist role. |

- **REQ-4.3.12 [Present]** Report generation MUST require a completed case.
- **REQ-4.3.13 [Present]** The generated report MUST include the clinical safety disclaimer in full.

## 4.4 Module 4: Clinical Dashboards and Reporting

### 4.4.1 UC-4.1 Authentication and Role-Based Access Control

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.1 |
| **Primary Actor** | User (Technologist, Radiologist, Physician) |
| **Preconditions** | The user has a registered account with an assigned role. |
| **Postconditions** | A secure session is created and the user is directed to the dashboard appropriate to their role. |
| **Main Success Scenario** | 1. The user provides credentials. 2. The system authenticates the user and determines their role. 3. The system establishes a secure session and directs the user to the matching dashboard. |
| **Alternative Flows** | **AF-1 (Logout):** the user ends the session, and the system clears the session and any client-side state. |
| **Exception Flows** | **EF-1 (Invalid credentials):** the system refuses access without revealing which detail was incorrect. **EF-2 (Missing role):** an account without a recognized role cannot proceed. **EF-3 (Unauthorized action):** a request outside the user's role is refused, and an unauthenticated user is directed to sign in. |
| **Access** | Sign-in is public; all clinical features require an authenticated session. |

- **REQ-4.4.1 [Present]** Authentication MUST be session-based, and the session MUST be protected against request-forgery and session-hijacking attacks.
- **REQ-4.4.2 [Present]** The system MUST enforce role permissions on the server for every clinical operation; client-side restrictions are supplementary and never the sole control.
- **REQ-4.4.3 [Present]** The client MUST direct each user to the correct dashboard for their role and MUST prevent navigation to features outside their role.

### 4.4.2 UC-4.2 Role-Specific Dashboards and Case Tracking

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.2 |
| **Primary Actor** | User (Technologist, Radiologist, Physician) |
| **Preconditions** | The user is authenticated with a confirmed role. |
| **Postconditions** | A dashboard tailored to the user's role is displayed. |
| **Main Success Scenario** | 1. The dashboard requests the data relevant to the role. 2. The system returns only the records appropriate to that role. 3. The dashboard presents summary information, filters, and a paged list of relevant cases or reports. |
| **Access** | Each dashboard restricted to its corresponding role. |

- **REQ-4.4.4 [Present]** The Technologist dashboard MUST show only the records uploaded by that technologist.
- **REQ-4.4.5 [Present]** The Physician dashboard MUST surface finalized reports, unread alerts, report-ready items, and patient progress, and MUST be restricted to the Physician role.
- **REQ-4.4.6 [Present]** Each dashboard MUST present only the information and actions appropriate to its role.

### 4.4.3 UC-4.3 In-System Notifications

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.3 |
| **Primary Actor** | User |
| **Preconditions** | Notifications relevant to the current user exist. |
| **Postconditions** | Notifications are listed and may be marked as read. |
| **Main Success Scenario** | 1. A report is submitted, and the system notifies the relevant physician. 2. An AI failure occurs, and the system notifies the radiologists that manual review is required. 3. The user opens the notification indicator, views their notifications, and may mark one or all as read. |
| **Exception Flows** | **EF-1 (Foreign notification):** a user cannot view or mark another user's notifications. |
| **Access** | Available to authenticated users, scoped to their own notifications. |

- **REQ-4.4.7 [Present]** The system MUST generate in-system notifications on report submission and on AI failure.
- **REQ-4.4.8 [Present]** Notification access MUST be scoped to the recipient; a user MUST NOT be able to view or modify another user's notifications.

### 4.4.4 UC-4.4 Consolidated Analytics and Export

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.4 |
| **Primary Actor** | Radiologist or Physician |
| **Preconditions** | The user has an authorized role. |
| **Postconditions** | Aggregated case and report metrics are displayed and can be exported. |
| **Main Success Scenario** | 1. The user opens the analytics dashboard and may narrow the view by date range and severity. 2. The system computes totals and breakdowns across case status, AI risk label, report severity, and report status. 3. The dashboard presents the results as charts and tables. 4. The user exports the results as a spreadsheet or a print-ready document. |
| **Alternative Flows** | **AF-1 (Empty dataset):** the system presents a clear empty state rather than misleading zeros. |
| **Exception Flows** | **EF-1 (Invalid filters):** the system rejects the request with a clear message. |
| **Access** | Restricted to Radiologist and Physician roles. |

- **REQ-4.4.9 [Present]** The system MUST compute consolidated metrics, filterable by date range and severity.
- **REQ-4.4.10 [Present]** The system MUST export consolidated analytics in both a tabular format and a print-ready document format.

### 4.4.5 UC-4.5 Automated Backup and Restore

| Field | Description |
| :---- | :---- |
| **Use Case ID** | UC-4.5 |
| **Primary Actor** | DevOps / Administrator |
| **Preconditions** | A supported host has access to the database and media store. |
| **Postconditions** | A timestamped, integrity-checked backup exists, or a verified restore has been performed. |
| **Main Success Scenario** | 1. The operator runs the backup tool. 2. The tool captures the database and media into a timestamped archive together with an integrity manifest. 3. On demand, the operator runs the restore tool, which verifies the archive's integrity and restores the database, the media, or both. |
| **Alternative Flows** | **AF-1 (Dry run):** the restore tool can verify an archive without applying it. **AF-2 (Partial restore):** the operator may restore only the database or only the media. |
| **Exception Flows** | **EF-1 (Overlapping locations):** the backup and media locations must not overlap. **EF-2 (Integrity mismatch):** a failed integrity check causes the restore to refuse to proceed. **EF-3 (Unsupported host):** the file-locking mechanism requires a POSIX-style host. |
| **Access** | Administrative tooling; not exposed to clinical users. |

- **REQ-4.4.11 [Present]** Backups MUST cover the database and media and MUST include an integrity manifest.
- **REQ-4.4.12 [Present]** Restore MUST verify archive integrity and MUST support a dry run and partial restores.

## 4.5 Cross-cutting: Record and Report Lifecycles

Every screening case progresses through a small, well-defined set of states, from upload to completion. The exact state names are an implementation detail, but the system MUST represent, at minimum, the following stages:

| Stage | Meaning |
| :---- | :---- |
| **Newly uploaded** | The case has been received but not yet scored or reviewed. |
| **Under review** | A Radiologist currently holds the review lock for the case. |
| **AI output available** | AI-assisted scoring completed successfully and output is available. |
| **Manual review required** | AI output is unavailable or unusable, and the case must be reviewed manually. |
| **Complete** | A Radiologist has submitted findings for the case. |

Diagnostic reports progress through two states:

| Stage | Meaning |
| :---- | :---- |
| **Draft** | Editable; may be saved and updated repeatedly. |
| **Finalized** | Read-only; submission notifies the relevant physician. |

- **REQ-4.5.1 [Present]** The system MUST represent cases and reports through a single, consistent set of lifecycle stages, and MUST expose the current stage to the appropriate roles.

## 4.6 Cross-cutting: Role-Based Access Control

The system defines three clinical roles. The table summarizes the intended capability model; the exact mapping to individual operations is maintained in the design documentation.

| Capability | Technologist | Radiologist | Physician |
| :---- | :----: | :----: | :----: |
| Register patients | ✔ | | |
| View patients and history | ✔ | ✔ | ✔ |
| Upload and prepare images | ✔ | | |
| Re-run AI analysis | ✔ | | |
| Review and annotate cases | | ✔ | |
| Author and finalize reports | | ✔ | |
| Generate printable reports | | ✔ | |
| View physician dashboard | | | ✔ |
| Analytics summary and export | | ✔ | ✔ |
| Override disease progression | | ✔ | |

All authenticated roles may view progression data and their own notifications.

- **REQ-4.6.1 [Present]** Role permissions MUST be enforced on the server for every clinical operation; client-side guards are supplementary only.
- **REQ-4.6.2 [Present]** Access rules MUST be applied consistently across related operations; any deliberate deviation MUST be documented (Section 7).

---

# 5. Data Requirements

The system MUST persist the following categories of information. This section describes the data at a conceptual level; the physical schema, field names, and types are recorded in `documentation/SDD.md`.

- **User accounts** — credentials and an assigned role. Every clinical action is attributable to an account.
- **Patients** — the demographic details needed to identify a patient and associate cases with them.
- **Screening cases** — one per uploaded image, each with a unique transaction identifier, a reference to its patient and uploading technologist, the source image, the time of upload, and its current lifecycle stage.
- **Standardized images** — the prepared version of each uploaded image, together with a record of how it was prepared (including any decision to proceed despite a low-quality result).
- **Annotations** — regions of interest marked on an image, each with coordinates that are independent of display size, a label, and associated notes, attributed to the reviewing Radiologist.
- **AI results** — the risk estimate, its risk label, the model version that produced it, an optional explainability heatmap, and the time it was generated.
- **Reports** — the findings, impression, recommendation, and severity, attributed to the author, with a lifecycle state and timestamps.
- **Notifications** — a message, its recipient, its read state, and timestamps.
- **Progression records** — the computed progression status for a patient, the estimates compared, the stability threshold applied, and whether the status was overridden. Overrides additionally produce an **override audit record** capturing the actor, the previous and new status, the clinical note, and the time.

- **REQ-5.1 [Present]** The system MUST persist all categories above and MUST associate every clinical record with the patient and, where applicable, the responsible user.
- **REQ-5.2 [Present]** The system MUST maintain a single consistent set of risk, severity, and lifecycle values across all data and interfaces.
- **REQ-5.3 [Present]** Progression overrides and other clinically significant manual decisions MUST be permanently attributable and auditable.

---

# 6. Non-Functional Requirements

## 6.1 Performance and Responsiveness

The AI model's measured performance on its reference validation set is summarized below. These figures characterize the model, not the end-to-end clinical workflow.

| Metric | Result |
| :---- | :---- |
| Accuracy | 99.88% |
| Sensitivity (Recall) | 99.27% |
| Specificity | 100.00% |
| Precision | 100.00% |
| F1 | 99.63% |
| AUC-ROC | 1.0000 |
| Inference latency (mean / median) | 73.3 ms / 65.6 ms |

- **REQ-6.1.1 [Present]** AI inference MUST return a score within an interactive time frame; measured mean inference is well under one second on the reference host.
- **REQ-6.1.2 [Target]** Image standardization SHOULD complete within a few seconds per upload.
- **REQ-6.1.3 [Target]** Queue and review workspaces SHOULD load within a few seconds.
- **REQ-6.1.4 [Target]** Explainability heatmap generation SHOULD complete within a few seconds.
- **REQ-6.1.5 [Target]** Progression comparison SHOULD complete within a few seconds.
- **REQ-6.1.6 [Target]** Printable report generation SHOULD complete within a few seconds.
- **REQ-6.1.7 [Target]** The AI baseline score SHOULD be produced within ten seconds of image acceptance.

> **Note.** The measured metrics above were obtained on a small validation set and should be treated as indicative until validated on local clinical data (Section 7).

## 6.2 Security and Privacy

- **REQ-6.2.1 [Present]** Every clinical operation MUST require an authenticated session, and role restrictions MUST be enforced on the server.
- **REQ-6.2.2 [Present]** State-changing requests MUST be protected against cross-site request forgery.
- **REQ-6.2.3 [Present]** Uploaded medical images MUST be de-identified, removing at least the standard patient and study identifiers carried by the image format, before storage or analysis.
- **REQ-6.2.4 [Present]** In production, the system MUST run with developer behaviour disabled, require properly configured secrets, restrict accepted hosts, and enforce HTTPS, secure cookies, and strict transport security.
- **REQ-6.2.5 [Present]** Concurrent review of the same case MUST be prevented through review locking.
- **REQ-6.2.6 [Present]** Progression overrides MUST be attributable through an audit log capturing the actor, the previous and new status, the note, and the time.
- **REQ-6.2.7 [Present]** Access to patient-identifying data MUST be limited to authenticated, authorized users, and media MUST be served only to such users.
- **REQ-6.2.8 [Target]** Patient-identifying information SHOULD be encrypted in transit and at rest; cloud object storage is excluded.

## 6.3 Reliability and Availability

- **REQ-6.3.1 [Present]** The system MUST provide automated backup tooling covering the database and media, with integrity manifests.
- **REQ-6.3.2 [Present]** Restore MUST support integrity verification, dry runs, and partial restores.
- **REQ-6.3.3 [Present]** Backup retention MUST be configurable, with a sensible default that limits storage growth while retaining recent archives.
- **REQ-6.3.4 [Present]** AI failure MUST NOT block the clinical workflow; affected cases MUST route to manual review.
- **REQ-6.3.5 [Target]** The platform SHOULD maintain high availability for remote radiologist access.
- **REQ-6.3.6 [Present]** Backups MUST be documented as crash-consistent, and the runbook MUST state clearly what is and is not covered by a single backup.

## 6.4 Usability

- **REQ-6.4.1 [Present]** The interface MUST provide role-tailored dashboards and clear, actionable validation feedback.
- **REQ-6.4.2 [Target]** The system SHOULD achieve a System Usability Scale score above the accepted threshold in pilot evaluation.
- **REQ-6.4.3 [Present]** A visible, non-dismissible AI disclaimer MUST appear on all clinical surfaces.

## 6.5 Maintainability and Testability

- **REQ-6.5.1 [Present]** Automated tests MUST cover access control, upload and AI handling, report authoring, progression, the physician dashboard, and backup and restore.
- **REQ-6.5.2 [Present]** A continuous-integration pipeline MUST run backend smoke tests and frontend unit tests and linting on every push and pull request.
- **REQ-6.5.3 [Target]** Report-related components SHOULD maintain strong test coverage, and the progression component higher still.
- **REQ-6.5.4 [Present]** The system MUST expose a machine-readable description of its public interfaces for developers.

## 6.6 Regulatory and Ethical Compliance

- **REQ-6.6.1 [Present]** The system MUST protect patient-identifying information consistent with the Philippine Data Privacy Act of 2012 (RA 10173).
- **REQ-6.6.2 [Present]** The AI MUST be presented strictly as an assistive, non-definitive baseline; diagnostic authority remains with human clinicians.
- **REQ-6.6.3 [Present]** The system MUST include clinical liability disclaimers both in the interface and in generated reports.

---

# 7. Known Limitations and Future Work

The following limitations are acknowledged so that requirements are not misrepresented and remediation can be tracked. They are stated in capability terms; implementation-specific detail is maintained in `documentation/GAP-CHECKLIST-SRS-SDD-vs-code.md`.

| # | Area | Limitation | Suggested direction |
| :-- | :---- | :---- | :---- |
| 1 | AI retry | No automatic retry before declaring AI unavailable; the first failure routes a case to manual review. | Add bounded retries before declaring the model unavailable. |
| 2 | Risk levels | The system distinguishes multiple risk levels, but the deployed model produces a binary high/low decision, so an intermediate level is never produced by inference. | Train a multi-level model, or derive an intermediate level from calibrated bands. |
| 3 | Progression in reports | Generated reports do not include a progression section when comparison data exists. | Include a progression block in generated reports. |
| 4 | Progression comparison basis | Comparison uses the most recent prior case with a valid estimate, regardless of that case's workflow status. | Align the comparison basis with clinical requirements if needed. |
| 5 | Notification recipient | There is no patient-to-physician assignment; report-ready notifications go to a default recipient. | Introduce an explicit patient-to-physician assignment. |
| 6 | Route protection | Some patient-facing pages are not yet protected by role guards on the client. | Apply authentication and role guards consistently. |
| 7 | Session identity | The signed-in user's name and email are not fully displayed after login. | Persist and display the full user profile. |
| 8 | Global search | The global search control is not yet functional. | Implement or remove it. |
| 9 | Prepared-analysis artifact | A prepared analysis artifact is generated and recorded but not yet consumed by inference. | Feed the artifact to inference, or stop generating it. |
| 10 | Dead code | Some unused components and legacy placeholders remain in the codebase. | Remove them. |
| 11 | Deployment | No containerized or production web-server configuration is provided in-repo. | Add deployment configuration. |
| 12 | Backup portability | Backup and restore tooling is limited to POSIX-style hosts. | Add a Windows-compatible locking mechanism, or document the constraint clearly. |
| 13 | Documentation drift | Some AI documentation and helper scripts no longer match the implemented preprocessing and filenames. | Reconcile documentation and scripts with the implementation. |
| 14 | Annotation display controls | The image viewer offers zoom and pan but no brightness or contrast adjustment. | Add display controls if clinically required. |
| 15 | Dataset representativeness | Model performance is measured on a small, undemanding dataset; recall is the priority metric. | Validate on local clinical data during the pilot. |
| 16 | Report generation side effect | Generating a printable report can silently create a placeholder draft when none exists. | Require an existing draft before generating a printable report, or return a clear message. |
| 17 | Report auditability | Finalization is not recorded with a dedicated timestamp, only through status and update time. | Add an explicit finalization timestamp if governance requires it. |
| 18 | Report validation layer | Key report invariants are enforced in one layer only, with no domain-level enforcement. | Move key invariants to a shared validation layer if the workflow expands. |
| 19 | Severity semantics | The clinical meaning of the severity field is not explicitly defined. | Confirm and document the intended meaning. |

---

# Appendix A: Traceability Matrix

This matrix links each use case to its requirements so that coverage can be verified. It deliberately omits implementation references; those are maintained in the design documentation.

| Use Case | Requirement(s) |
| :---- | :---- |
| UC-1.1 Secure image and metadata upload | REQ-4.1.1–4.1.3 |
| UC-1.2 Automated image standardization | REQ-4.1.4–4.1.5 |
| UC-1.3 Centralized patient profiling | REQ-4.1.6–4.1.7 |
| UC-1.4 Image quality gate | REQ-4.1.8–4.1.9 |
| UC-2.1 Remote access queue | REQ-4.2.1 |
| UC-2.2 Concurrency-safe review session | REQ-4.2.2–4.2.3 |
| UC-2.3 Interactive annotation | REQ-4.2.4–4.2.5 |
| UC-2.4 Structured diagnostic report | REQ-4.2.6–4.2.10 |
| UC-2.5 Annotation submission and case completion | REQ-4.2.11–4.2.12 |
| UC-3.1 AI-assisted baseline risk scoring | REQ-4.3.1–4.3.5 |
| UC-3.2 Historical record retrieval | REQ-4.3.6 |
| UC-3.3 Comparative progression tracking and override | REQ-4.3.7–4.3.11 |
| UC-3.4 Comprehensive report generation | REQ-4.3.12–4.3.13 |
| UC-4.1 Authentication and RBAC | REQ-4.4.1–4.4.3 |
| UC-4.2 Role-specific dashboards | REQ-4.4.4–4.4.6 |
| UC-4.3 In-system notifications | REQ-4.4.7–4.4.8 |
| UC-4.4 Consolidated analytics and export | REQ-4.4.9–4.4.10 |
| UC-4.5 Automated backup and restore | REQ-4.4.11–4.4.12 |
| Cross-cutting lifecycles | REQ-4.5.1 |
| Cross-cutting RBAC | REQ-4.6.1–4.6.2 |
| Data requirements | REQ-5.1–5.3 |
| Non-functional requirements | REQ-6.x |

---

*End of document.*

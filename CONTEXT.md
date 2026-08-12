# PROJECT SYSTEM CONTEXT & GROUNDING DOCUMENT

## 1. Executive Summary & Core Identity
* **Project Name:** TB-XR
* **Target Domain:** Healthcare / Pulmonary Tuberculosis screening in low-resource clinical environments
* **Elevator Pitch:** TB-XR is a collaborative, AI-integrated teleradiology platform that helps Radiologic Technologists and remote Radiologists manage chest X-ray uploads, detect high-risk TB cases using a lightweight local AI model, and monitor patient progression over time through structured review and reporting workflows.

## 2. Problem Statement & Objectives
* **The Core Problem:** TB screening in low-resource healthcare settings is hindered by limited radiological expertise, delayed image interpretation, fragmented patient data, and the lack of affordable, locally deployable AI tools. In the Philippines, tuberculosis remains a major public health burden, and many primary care facilities lack the infrastructure, personnel, and digital workflow support needed for rapid and reliable chest X-ray screening.
* **Primary Objective:** To design and develop a lightweight, AI-assisted TB chest X-ray screening system that supports rapid image ingestion, secure patient management, human-in-the-loop review, and longitudinal disease monitoring in resource-constrained healthcare environments.
* **Specific Objectives:**
  - Reduce manual image preparation time for Radiologic Technologists by automating upload validation, image standardization, and patient linkage.
  - Accelerate radiologist review by providing a collaborative, remote annotation workflow for pending chest X-ray cases.
  - Augment clinical decision-making with rapid AI risk scoring and longitudinal comparison of patient X-ray records.
  - Minimize administrative delays by tracking transactions and generating structured PDF clinical reports for physicians.

## 3. Scope and Boundaries
* **In-Scope Features:** 
  - Secure chest X-ray upload and patient record management
  - Image preprocessing and standardization using contrast enhancement and resizing
  - AI-assisted TB risk triage using a lightweight CNN model
  - Human-in-the-loop annotation and diagnostic review workflow
  - Longitudinal patient monitoring and historical X-ray comparison
  - Role-based dashboards, audit logging, and report generation
* **Explicitly Out-of-Scope:** 
  - Live PACS/DICOM network integration or autonomous medical diagnosis
  - Definitive multi-disease diagnosis beyond generalized TB risk triage
  - Pharmaceutical management, treatment tracking, or appointment scheduling
  - Full regulatory certification or hospital-wide HIS integration in the MVP
* **Target Users:** Radiologic Technologists, Radiologists, Attending Physicians, and clinical facilities operating in low-resource TB screening environments.

## 4. Technical Architecture Baseline
| Layer | Technology |
|-------|-----------|
| Backend | Django + Django REST Framework |
| Frontend | React + Vite + Tailwind CSS |
| Database | PostgreSQL (production) / SQLite (development) |
| AI/ML | PyTorch-based lightweight CNN, with MobileNetV3-inspired deployment context |
| Image Processing | OpenCV, pydicom, Pillow |
| Auth | JWT authentication, RBAC, audit logging |
| Deployment | Local edge-server deployment over LAN/intranet, offline-first operation |

## 5. Non-Negotiable Constraints (Hard Constraints)
* **Academic Constraints:** The project must be developed as a feasible thesis system with clear implementation scope, validation, and documentation suitable for final defense and evaluation.
* **Technical Constraints:** The system must be lightweight enough to run on low-resource hardware, support local LAN-based deployment, and provide AI-assisted screening without depending on cloud-only inference.
* **Clinical Safety Constraints:** The AI model is a support tool only; it cannot make final medical diagnoses. Final verification remains with human Radiologists and Physicians.
* **Data Privacy Constraints:** The platform must comply with the Philippine Data Privacy Act of 2012 (RA 10173), protect PHI/PII, and avoid unsecured transmission or storage of patient data.
* **Operational Constraints:** The system must handle DICOM/JPEG/PNG uploads, generate standardized outputs for review, and provide a visible clinical disclaimer that AI outputs are non-definitive baseline suggestions.
* **System Boundary Constraints:** The MVP excludes full PACS integration, cloud storage, direct treatment workflows, and definitive multi-disease classification.
* **Infrastructure Constraints:** The deployment environment assumes local hosting, limited bandwidth conditions, stable intranet connectivity, and efficient processing on standard laptops or small edge-server infrastructure.

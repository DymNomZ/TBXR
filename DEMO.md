# TB-XR — Demo Script

This file documents the end-to-end walkthrough for each increment's demo.
Add each week's section as development progresses.

---

## Week 1 Demo — X-ray Ingestion & Data Management

**What to show:** A Radiologic Technologist using the system to upload a chest X-ray from start to finish.

**Prepare before the demo:**
- Backend running at `localhost:8000`
- Frontend running at `localhost:5173` (or served via Django templates)
- A seeded `RADIOLOGIC_TECH` test account ready to log in
- A sample valid chest X-ray image (JPEG or PNG) on hand
- A sample invalid file (e.g., a `.pdf` or `.txt`) on hand for the rejection demo
- Database is clean or has at most a few test records

---

### Step 1 — Log In as a Radiologic Technologist

- Open the app in the browser
- Enter the technologist credentials (username + password)
- Click **Log In**
- **Expected:** Redirect to the Technologist Dashboard
- **Point out:** Role-based redirect — a Radiologist or Physician logging in would land on a different dashboard

---

### Step 2 — Create or Search for a Patient Profile

- From the dashboard, navigate to **Patients**
- Use the search bar to look up a patient by name or ID
- If no patient exists, click **New Patient** and fill in the form:
  - First name, last name, date of birth, sex, contact number
  - Click **Save**
- **Expected:** Patient profile created and visible in the patient list
- **Point out:** Every X-ray upload is always linked to a patient profile — no orphan records

---

### Step 3 — Initiate an X-ray Upload

- From the patient's profile page, click **Upload X-ray**
- The upload form is pre-linked to the selected patient
- **Expected:** Upload form appears with a file picker and the patient's name already filled

---

### Step 4 — Attempt an Invalid File Upload (Rejection Demo)

- On the upload form, attach the sample invalid file (e.g., `.pdf`)
- Click **Submit**
- **Expected:** System displays an error message — "Unsupported file type. Please upload a JPEG, PNG, or DICOM (.dcm) file."
- The file is **not** saved anywhere
- **Point out:** Format validation happens server-side, not just in the browser

---

### Step 5 — Upload a Valid Chest X-ray

- Clear the invalid file and attach the valid chest X-ray (JPEG or PNG)
- Click **Submit**
- **Expected:**
  - File passes validation
  - Image is preprocessed in the background (resized to 224×224, contrast-enhanced)
  - A unique Transaction ID (UUID) is generated and stored
  - System redirects to an upload confirmation page

---

### Step 6 — View the Upload Confirmation

- Confirmation page displays:
  - **Transaction ID** (e.g., `a3f7b2c1-...`)
  - Patient name
  - Upload timestamp
  - Current status: **"Pending Review"**
- **Point out:** This Transaction ID is the permanent record identifier that follows this X-ray through the entire workflow — annotation, AI analysis, and final report

---

### Step 7 — View the Technologist Dashboard

- Navigate back to the dashboard
- **Expected:** The new upload appears in the table with:
  - Transaction ID
  - Patient name
  - Upload date
  - Status: **"Pending Review"**
- **Point out:** The technologist's work ends here — the record is now in the queue for a Radiologist to pick up (which will be demonstrated in Week 2)

---

## Week 2 Demo — Radiologist Annotation Module
*(To be added)*

---

## Week 3 Demo — AI Integration & Longitudinal Monitoring
*(To be added)*

---

## Week 4 Demo — Role-Based Dashboards & Reporting
*(To be added)*

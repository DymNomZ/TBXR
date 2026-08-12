# TB-XR: Clinical Validation & Hospital Partnership Roadmap

This document outlines the non-technical roadmap for validating the TB-XR system in a real clinical environment. Its purpose is to give the team a shared understanding of **why** the hospital visit matters, **what** data we are collecting, and **when** each phase must happen relative to our semester timeline.

---

## Why This Matters

TB-XR is both a **software engineering project** and a **thesis research project**. These have different success criteria:

- The software project succeeds when the system is complete, secure, and deployable.
- The thesis research succeeds when we have **empirical evidence** that the system actually delivers clinical value to real users.

The hospital pilot is the bridge between the two. Without it, our defense is "here is a system we built." With it, it becomes "here is a system that physicians validated and showed measurable clinical value."

---

## What We Are Measuring and Why

| Metric | Why It Matters |
|--------|----------------|
| **System Usability Scale (SUS) score** | Validates the UI is intuitive for our target users (target: SUS > 70) |
| **Task completion rates** | Confirms workflows are clear — upload → review → report end-to-end |
| **Time-to-diagnosis benchmarks** | Proves heatmap reduces annotation time vs. no-AI baseline |
| **AI accuracy (sensitivity / specificity)** | Validates CNN model on real TB vs. non-TB cases (target: > 85%) |
| **User feedback (qualitative)** | Uncovers undocumented needs, friction points, and training gaps |
| **Workflow integration friction** | Shows how TB-XR fits (or doesn't) into existing clinic processes |

These metrics collectively answer the thesis committee's core questions:
- *Did you validate this actually works?*
- *How did users respond?*
- *Is the AI accurate?*
- *What would production deployment need?*

---

## Phase Roadmap

| Phase | When | What | Key Deliverable |
|-------|------|------|-----------------|
| **Phase 1: MVP Hardening** | Now — End of Week 6 | Close all gap checklist items, security audit, feature freeze | Deployment-ready system |
| **Phase 2: Partnership & Ethics Prep** | Weeks 7–10 | IRB approval, MOU with hospital, test protocol design, data governance plan | Formal hospital agreement + ethics clearance |
| **Phase 3: Limited Pilot Deployment** | Weeks 11–14 | Deploy to 2–4 radiologists, 50–100 de-identified cases, structured observation | Raw data + preliminary analysis |
| **Phase 4: Thesis Analysis & Defense** | Semester 2 | Analyze pilot data, document findings, iterate, defend | Defended thesis with empirical evidence |

---

## Phase 2 Checklist: What Must Be Done Before the Hospital Visit

- [ ] Re-engage advisor and physician contact to confirm partnership interest and target timeline
- [ ] Draft Memorandum of Understanding (MOU) template for hospital partnership
- [ ] Submit IRB (Institutional Review Board) application through university *(allow 4–6 weeks for approval)*
- [ ] Document current system capabilities and known limitations
- [ ] Design validation study protocol:
  - Define research questions
  - Choose test format (structured usability test, embedded observation, or hybrid)
  - Define success metrics and thresholds
- [ ] Create data protection and anonymization spec aligned with RA 10173 (Philippine Data Privacy Act)
- [ ] Define data retention, deletion, and access control policies

---

## Phase 3 Scope: Pilot Parameters

- **Participants:** 2–4 radiologists and/or radiologic technologists
- **Dataset:** 50–100 de-identified TB chest X-ray cases
- **Duration:** 2–4 week usage period
- **Data collection methods:**
  - SUS questionnaire (after 1–2 days of use)
  - Timed task-based testing (upload → annotate → generate report)
  - Researcher observation notes (friction, workarounds, praise)
  - AI accuracy validation (model output vs. radiologist consensus)
  - Workflow time logs (with and without heatmap feature)

---

## Notes

- The **heatmap feature** has been identified by our physician contact as a non-standard but high-value tool, particularly for junior radiologists who spend significant time on annotation. This should be a **featured element** in the pilot study protocol and a highlighted result in the thesis.
- The appropriate time to approach the hospital for scheduling is **end of Week 6**, once Phase 1 is complete. Approaching earlier risks presenting an incomplete system and losing credibility with the clinical partner.
- IRB submission should be initiated **no later than Week 7** due to typical 4–6 week review cycles.

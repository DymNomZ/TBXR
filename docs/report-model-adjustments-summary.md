# Report Model Adjustments Summary

## Current MVP Decision
For the current TB-XR MVP, the proposed **one Report per XrayRecord** design is acceptable and aligned with the current workflow:

- one canonical clinical report per completed X-ray,
- radiologist drafts before finalization,
- finalized reports become immutable,
- persisted report data is used for PDF generation and review.

This is a reasonable fit for the thesis scope and should not block the PR.

## Recommended Adjustments

### 1. Clarify the report lifecycle in the design docs
Document that the MVP treats `Report` as the **single canonical report** for each `XrayRecord`.

Why this matters:
- removes ambiguity about whether revisions or multiple reports are allowed,
- helps future contributors understand the intended boundary,
- makes thesis defense explanations more consistent.

### 2. Reconsider automatic placeholder report creation during PDF generation
The current implementation auto-creates a minimal report if PDF generation is requested before a report exists.

Recommended adjustment:
- require an existing draft report before generating the PDF, or
- return a clear error instructing the user to create a report first.

Why this matters:
- avoids silently creating clinical records as a side effect of report generation,
- prevents placeholder content from being mistaken for real findings,
- keeps the report workflow explicit and auditable.

### 3. Clarify the meaning of `severity`
The `severity` field is workable, but the team should confirm what it represents:

- TB suspicion level,
- radiology severity,
- or clinical urgency.

Recommended adjustment:
- keep the field for now,
- but document its meaning clearly,
- and rename it later if the team decides a more precise term is needed.

Why this matters:
- reduces semantic confusion,
- helps preserve clinical clarity,
- makes the model easier to defend as part of the thesis.

### 4. Consider adding `finalized_at` later if audit needs grow
Not required for the MVP, but useful if the workflow expands.

Potential future addition:
- `finalized_at = DateTimeField(null=True, blank=True)`

Why this matters:
- gives a precise timestamp for when the report became official,
- supports stronger audit trails,
- helps if revisions, signatures, or governance controls are added later.

### 5. Move workflow rules closer to the domain layer if the model expands
Right now the serializer handles most draft/final validation, which is fine for the MVP.

If the model grows later, consider moving key invariants into:
- model validation,
- a service layer,
- or domain-specific workflow helpers.

Why this matters:
- prevents workflow rules from being tied too tightly to one API path,
- makes the behavior easier to reuse,
- improves maintainability as the system grows.

## Bottom Line
For the current MVP, the proposed design is **acceptable** and should be kept. The main recommended adjustments are about **clarity, auditability, and avoiding implicit side effects**, not about changing the core one-report-per-X-ray structure.

We can revisit the model later if the team wants:
- multiple report versions,
- co-signing,
- revision history,
- or a more formal clinical workflow.

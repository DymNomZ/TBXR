# TB-XR Coding Standards

Purpose:
- Define the baseline rules the TB-XR team should follow when writing code.
- Give human developers and code-generating agents a shared source of truth.
- Reduce avoidable bugs now and make a later TypeScript migration easier.

Scope:
- Applies to `backend/`, `frontend/`, `ai/`, and related scripts.
- Applies to pull requests, direct coding sessions, and AI-assisted code generation.

Status:
- This is the active baseline during the current 6-week sprint.
- These standards are intentionally practical, not idealized.

## 1. Core Principles

1. Build for correctness before cleverness.
2. Prefer simple, explicit code over abstract or reusable-looking code that hides behavior.
3. Keep features small and reviewable.
4. Do not mix bug fixes, refactors, and feature work unless they are directly related.
5. Code should be easy for another teammate to debug without asking the original author.

## 2. Architecture Rules

1. Keep business logic out of UI components when possible.
2. Keep business logic out of Django views when it grows beyond simple request handling.
3. Prefer service or utility functions for reusable domain behavior.
4. Centralize enums, status values, and role names instead of duplicating raw strings.
5. Do not invent parallel data shapes for the same entity in different files without reason.

Examples of values that must stay centralized:
- roles
- case status values
- severity or risk labels
- notification status values
- progression labels

## 3. Naming and Readability

1. Use descriptive names. Avoid one-letter variables except trivial loop indexes.
2. Match names to domain language used in the SRS/SDD and API contracts.
3. Use `sex` consistently if that is the actual model field. Do not alternate with `gender` unless both fields intentionally exist.
4. If a field has one canonical backend name, use that exact name across serializers, frontend payloads, and templates unless there is a deliberate mapping layer.
5. Prefer smaller functions with one clear responsibility.

## 4. Frontend Standards

1. Components should focus on rendering and user interaction.
2. API calls should be routed through a shared service layer where practical.
3. Avoid inline ad hoc request shapes inside many components.
4. Shared UI state should live in context or a dedicated state owner, not in duplicated local component state across pages.
5. Form validation rules should be explicit and visible in the code.
6. Role gating must be enforced consistently in routing and in rendered actions.

Frontend file conventions:
- Page components should assemble sections and orchestration.
- Reusable display components should not know backend details.
- API adapters or service utilities should shape responses for UI use.
- Constants should hold repeated labels, enum values, and route fragments.

## 5. Backend Standards

1. Views should validate input, authorize access, call domain logic, and return responses.
2. Heavy workflow logic should move into services or helper modules.
3. Serializer validation should enforce business rules for final submission paths.
4. Keep model responsibilities focused on data and small invariants.
5. Use explicit status transitions rather than silent side effects where possible.

Backend patterns to prefer:
- serializer validation for request rules
- service functions for workflow steps
- utility modules for image preprocessing or report helpers
- centralized constants for statuses and roles

## 6. API Contract Discipline

This is the most important section for reducing bugs before a TypeScript migration.

1. Every endpoint should have one documented request and response shape.
2. If an endpoint contract changes, update the code and contract note in the same PR.
3. Do not return the same concept under different property names across endpoints unless explicitly documented.
4. Do not rename fields casually once frontend and backend both depend on them.
5. Use stable enum values. Avoid changing labels used by persisted data or filters without migration planning.

Minimum contract checklist for changed endpoints:
- route
- method
- auth requirement
- request body or query params
- success response shape
- failure response shape
- enum values

## 7. Pre-TypeScript Migration Rules

These are mandatory disciplines if the team wants a smoother TypeScript migration after the sprint.

1. Centralize shared payload shapes conceptually even if they are still written in JavaScript.
2. Keep API response keys stable.
3. Keep repeated object shapes in one helper, mapper, or constants file when possible.
4. Avoid passing giant unstructured objects deep through props if only a few fields are needed.
5. Prefer explicit default values and null handling.
6. Avoid magic string checks spread across many files.
7. Document any temporary inconsistencies so they can be typed cleanly later.

High-priority areas to keep clean for future TS migration:
- auth context
- dashboard row data
- report form payloads
- notification payloads
- progression response objects
- risk and status enums

## 8. Testing and Verification

1. Every bug fix should include a verification step.
2. Every non-trivial backend workflow change should update or add a test.
3. Frontend changes should be manually verified against realistic role flows even if automated coverage is limited.
4. Do not merge code that only “looks right” without exercising the affected path.
5. Smoke paths must stay green for auth, report generation, and other critical workflows.

Minimum verification expectations:
- endpoint tested directly or through the UI
- edge cases checked when status transitions are involved
- role permissions rechecked when authorization logic changes
- no obvious console or template errors introduced

## 9. Git and Pull Request Discipline

1. One PR should represent one coherent unit of work.
2. Reference the issue or ticket in the PR and commit history.
3. PR descriptions should explain what changed, why, and how it was verified.
4. If a contract changed, call it out clearly.
5. Avoid large unrelated formatting churn.

PR checklist:
- summary
- affected files or modules
- screenshots or sample responses when useful
- tests added or updated
- known limitations
- docs updated if contract or behavior changed

## 10. AI Agent Guidance

Use this section when asking an AI assistant to generate code.

Agent instructions for this repo:
1. Follow existing architecture before introducing new patterns.
2. Do not create new enums, statuses, or field names if canonical ones already exist.
3. Keep responses and generated code aligned with SRS/SDD terminology.
4. Prefer minimal focused changes over broad rewrites.
5. If changing an endpoint or payload, update the relevant documentation.
6. Do not silently change field meanings.
7. Preserve user-role restrictions in both UI and backend logic.
8. When unsure about a contract, inspect the current backend/frontend implementation first.

Recommended prompt note for teammates:
- “Use the repo coding standards in `documentation/CODING-STANDARDS.md` and keep changes aligned with the existing API contracts.”

## 11. Definition of Done

A ticket is not done just because code compiles.

Done means:
1. The intended behavior works.
2. The correct user role can access it.
3. The wrong user role cannot access it.
4. Validation and error handling are reasonable.
5. Tests or smoke verification were performed.
6. Documentation was updated if the behavior or contract changed.

## 12. Anti-Patterns to Avoid

1. Copy-pasting payload logic across pages.
2. Hardcoding endpoint URLs in many components.
3. Mixing display labels with persisted enum values.
4. Returning inconsistent backend field names for the same concept.
5. Writing giant views that preprocess, validate, authorize, mutate, and format everything inline.
6. Introducing refactors during urgent fixes unless strictly necessary.
7. Using comments to explain confusing code instead of simplifying the code.

## 13. Post-Sprint TypeScript Readiness Checklist

The project is ready to migrate incrementally when most of these are true:

- key endpoint contracts have stabilized
- role names are centralized
- severity and status enums are centralized
- report payload structure is stable
- notification payload shape is stable
- progression payload shape is stable
- ad hoc frontend fetch logic has been reduced
- major sprint features are complete and verified

## 14. Team Rule of Thumb

If a decision trades clarity for cleverness, choose clarity.

If a decision trades sprint delivery for a large refactor, choose sprint delivery unless the refactor removes a real blocker.

If a field, status, or payload name appears in more than one place, treat it like an interface even if the code is still JavaScript.
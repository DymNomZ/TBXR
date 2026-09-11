# ProgressionService — Domain Rule Documentation (Week 5 Foundation)

Source of truth: `backend/apps/imaging/services.py` (`ProgressionService`).
Tests: `backend/apps/imaging/test_progression.py` (44 tests).
Status: deterministic rule engine. No persistence, no UI, no manual override (explicitly out of scope).

## 1. Purpose

Compare consecutive AI TB-risk scores for the same patient and classify the change so
downstream APIs and UI (trend views, progression panels) have a stable, auditable input.

This is the foundation for longitudinal interpretation. It does **not** diagnose,
confirm improvement/deterioration clinically, or replace radiologist judgment.

> Clinical disclaimer: output describes change in **model-predicted TB risk only**.
> Final decisions remain with licensed Radiologists/Physicians.

## 2. Score semantics

- `AIResult.risk_score` is a float in `[0.0, 1.0]`.
- Higher = higher predicted TB probability.
- Therefore:
  - score decrease = model-predicted risk went down,
  - score increase = model-predicted risk went up.

## 3. Classification rules (deterministic)

Let `delta = round(current_score - previous_score, 4)`,
`abs_delta = round(abs(delta), 4)`, and `T` = stable threshold.

| Spec term      | Code status      | Rule                              | Example (`T=0.05`)        |
|----------------|------------------|-----------------------------------|---------------------------|
| — (baseline)   | `no_prior`       | No preceding valid `AIResult`     | First scan, or single-record history |
| Stable         | `stable`         | `abs_delta <= T`                  | `0.50 → 0.52` (`0.02 ≤ 0.05`), `0.50 → 0.55` (boundary inclusive) |
| Improvement    | `decreased_risk` | `delta < 0` and `abs_delta > T`   | `0.80 → 0.60` (`-0.20`)   |
| Deterioration  | `increased_risk` | `delta > 0` and `abs_delta > T`   | `0.30 → 0.60` (`+0.30`)   |

Notes:

- Boundary is inclusive: `abs_delta == T` is `stable`. This is covered by
  `test_stable_exact_boundary_is_inclusive`.
- Rounding to 4 decimals happens **before** comparison, so callers and tests
  observe the same `delta`/`abs_delta` the rule used.
- Status strings are centralized on `ProgressionService` (`NO_PRIOR`, `STABLE`,
  `DECREASED_RISK`, `INCREASED_RISK`) per `documentation/CODING-STANDARDS.md`.
  Do not duplicate raw strings in views/frontend; map spec labels
  (Improvement/Deterioration) to code statuses at the presentation layer.

## 4. Threshold — documented, configurable, no magic numbers

- Setting: `PROGRESSION_STABLE_THRESHOLD` (Django settings, optional).
- Default: `ProgressionService.DEFAULT_STABLE_THRESHOLD = 0.05`
  (5 percentage points of absolute TB probability).
- Meaning: minimum absolute score change considered meaningful. Smaller changes
  are treated as noise/stable.
- Valid range: `[0, 1]`. `0` = any change flips status; `1` = almost always stable.
- Configure via environment/settings, e.g. in `.env`:
  `PROGRESSION_STABLE_THRESHOLD=0.05` (see `backend/.env.example`).
- Per-call override: `compute()`, `compare_history()`, and `get_for_record()`
  accept `threshold=` which takes precedence over settings. Explicit param is
  validated with the same `[0, 1]` rule (`ValueError` otherwise).
- Invalid setting raises `ValueError` with an explicit message
  (`must be numeric` / `must be between 0 and 1`) — never silently falls back.

Rationale for `0.05`: small enough to surface real risk shifts for triage,
large enough to suppress model jitter between consecutive scans on low-resource
hardware. Tune only with clinical review; threshold changes alter all downstream
classifications.

## 5. Ordering and predecessor rules

- Chronological order is `(upload_timestamp ASC, pk ASC)`.
- `get_previous_result(current_record)` returns the immediately preceding valid
  `AIResult` for the **same patient**, excluding the current record:
  `upload_timestamp < current` OR (`==` AND `pk < current.pk`),
  ordered by `(-upload_timestamp, -pk).first()`.
- Records without an `AIResult` are skipped (they have no score to compare).
- Patient isolation is strict: other patients' records are never considered.
- Same-timestamp tie-break uses `pk`, so rapid repeat uploads have a total order.

## 6. Method contracts (stable for API/UI)

All methods are read-only; none persist progression data.

### `compute(current_score, previous_score, threshold=None) -> dict`

Pure function, no DB. Returns:

```python
{
  "status": "no_prior | stable | decreased_risk | increased_risk",
  "current_score": float,
  "previous_score": float | None,
  "delta": float | None,       # rounded to 4 decimals
  "abs_delta": float | None,
  "threshold": float,          # resolved T
}
```

`previous_score=None` yields `no_prior` with `delta/abs_delta=None`.

### `get_previous_result(current_record) -> AIResult | None`

DB lookup per §5. Returns `None` when no predecessor exists.

### `compare_history(patient_id, threshold=None) -> list[dict]`

Full longitudinal chain for one patient, in chronological order.
Each entry = `compute()` result plus:

```python
{
  "current_transaction_id": str,
  "current_timestamp": datetime,
  "previous_transaction_id": str | None,
  "previous_timestamp": datetime | None,
  "current_model_version": str,
  "previous_model_version": str | None,
  "comparison_available": bool,  # False only for first valid score
}
```

Empty list when the patient has no valid `AIResult`s. Gaps (records without AI)
are skipped but the chain links across them (R3 compares to R1 if R2 has no AI).

### `get_for_record(current_record, threshold=None) -> dict`

Single-record facade. Same shape as `compare_history` entries.
Special case — current record has no `AIResult`:

```python
{
  "status": "no_prior",
  "current_score": None, "previous_score": None,
  "delta": None, "abs_delta": None,
  "threshold": float,
  "comparison_available": False,
  "reason": "current_ai_result_unavailable",
}
```

Frontend guidance: use `comparison_available` to decide whether to render
delta/trend elements; use `reason` to render the no-baseline state.

## 7. Edge cases (acceptance criteria)

| Case | Behavior |
|------|----------|
| No prior image | `no_prior`, `comparison_available=False` |
| Only one image in history | Single entry, `no_prior` (§6 `compare_history`) |
| Current record has no `AIResult` | `no_prior` + `reason=current_ai_result_unavailable` |
| Invalid score (`nan`, `inf`, out of `[0,1]`, non-numeric) | `ValueError` via `validate_score` |
| Invalid threshold (setting or param) | `ValueError`, explicit message |
| Cross-patient leakage | Impossible by `patient_id` filter (tested) |

## 8. QA checklist mapping (spec → test)

| Spec QA item | Test |
|--------------|------|
| Decreasing history → improvement | `ComputeTests.test_decreased_risk`, `CompareHistoryTests.test_chained_classification_and_linkage` |
| Minimal delta within threshold → stable | `test_stable_within_threshold`, `test_stable_exact_boundary_is_inclusive`, `test_stable_zero_delta` |
| Increasing history → deterioration | `test_increased_risk`, chained linkage test |
| Single-record → no-prior baseline | `test_single_valid_score_has_no_prior`, `GetForRecordTests.test_no_previous_but_current_has_ai`, `test_first_record_has_no_previous` |
| Threshold matches documented rules | `GetThresholdTests` (9), `test_custom_threshold_changes_classification`, `test_threshold_override`, `test_threshold_zero_any_change_flips`, `test_threshold_one_always_stable` |

Run: `python manage.py test apps.imaging.test_progression apps.imaging.tests apps.imaging.test_smoke apps.imaging.test_report apps.imaging.test_physician_dashboard -v 1`
(103 tests green at time of writing: 44 new + 59 existing.)

## 9. Out of scope (not in this milestone slice)

- Persistence of progression snapshots (`ProgressionLog` in SDD is future work).
- Trend graph UI (`TrendChart`, `ProgressionPanel`).
- Manual override behavior (`override_progression`, `ProgressionOverrideForm`).
- Multi-disease classification, treatment tracking, PACS integration.

## 10. For backend developers

- Call the service from views; keep views thin per coding standards.
- Import is `from django.db.models import Q` (not `django.conf`) — fixed during test creation.
- Never invent parallel status strings; import from `ProgressionService`.
- If adding `progression_summary` API later, return the §6 dicts verbatim so
  the frontend contract in §6 stays stable.

## 11. For frontend developers

- Map for display: `decreased_risk` → Improvement, `increased_risk` → Deterioration,
  `stable` → Stable, `no_prior` → Baseline / Not enough history.
- Gate delta rendering on `comparison_available`, not on `delta is not None` alone
  (covers the missing-current-AI case).
- Always render the assistive-only disclaimer alongside any progression label.

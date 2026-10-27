from __future__ import annotations

import math

from django.conf import settings
from django.db.models import Q

from .models import AIResult, ProgressionStatus, XrayRecord

class ProgressionService:
    """
    Deterministic longitudinal progression engine.

    Progression is calculated by comparing the current AI risk score
    against the immediately preceding valid AI result for the same patient.

    Score semantics:
        Higher risk_score = higher TB probability.

    Classification rules:
        - no_prior:
            No preceding AI result exists.

        - stable:
            Absolute score change is less than or equal to the
            configured stable threshold.

        - decreased_risk:
            Score decreases by more than the stable threshold.

        - increased_risk:
            Score increases by more than the stable threshold.
    """
    NO_PRIOR = "no_prior"
    DECREASED_RISK = "decreased_risk"
    STABLE = "stable"
    INCREASED_RISK = "increased_risk"

    DEFAULT_STABLE_THRESHOLD = 0.05
    @classmethod
    def get_threshold(cls) -> float:
        """
        Return the configured progression threshold.

        The threshold represents an absolute change in TB probability.
        """

        threshold = getattr(
            settings,
            "PROGRESSION_STABLE_THRESHOLD",
            cls.DEFAULT_STABLE_THRESHOLD,
        )

        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            raise ValueError(
                "PROGRESSION_STABLE_THRESHOLD must be numeric."
            )

        if not 0 <= threshold <= 1:
            raise ValueError(
                "PROGRESSION_STABLE_THRESHOLD must be between 0 and 1."
            )

        return threshold

    
    @classmethod
    def validate_score(cls, score: float) -> float:
        """
        Validate an AI risk score.
        """

        try:
            score = float(score)
        except (TypeError, ValueError):
            raise ValueError(
                "AI risk score must be numeric."
            )

        if not math.isfinite(score):
            raise ValueError(
                "AI risk score must be finite."
            )

        if not 0 <= score <= 1:
            raise ValueError(
                "AI risk score must be between 0 and 1."
            )

        return score

    @classmethod
    def compute(
        cls,
        current_score: float,
        previous_score: float | None,
        threshold: float | None = None,
    ) -> dict:
        """
        Compute progression classification from two consecutive scores.

        This method is deterministic and does not access the database.
        """

        current_score = cls.validate_score(current_score)

        if threshold is None:
            threshold = cls.get_threshold()

        threshold = float(threshold)

        if not 0 <= threshold <= 1:
            raise ValueError(
                "Progression threshold must be between 0 and 1."
            )

        if previous_score is None:
            return {
                "status": cls.NO_PRIOR,
                "current_score": current_score,
                "previous_score": None,
                "delta": None,
                "abs_delta": None,
                "threshold": threshold,
            }

        previous_score = cls.validate_score(previous_score)

        delta = round(
            current_score - previous_score,
            4,
        )

        abs_delta = round(
            abs(delta),
            4,
        )

        if abs_delta <= threshold:
            status = cls.STABLE

        elif delta < 0:
            status = cls.DECREASED_RISK

        else:
            status = cls.INCREASED_RISK

        return {
            "status": status,
            "current_score": current_score,
            "previous_score": previous_score,
            "delta": delta,
            "abs_delta": abs_delta,
            "threshold": threshold,
        }

    @classmethod
    def get_previous_result(
        cls,
        current_record: XrayRecord,
    ) -> AIResult | None:
        """
        Return the immediately preceding valid AI result
        for the same patient.

        Ordering:
            1. upload_timestamp ascending
            2. primary key ascending

        The current record is excluded.
        """

        return (
            AIResult.objects
            .filter(
                xray_record__patient_id=current_record.patient_id,
            )
            .filter(
                Q(
                    xray_record__upload_timestamp__lt=
                    current_record.upload_timestamp
                )
                |
                Q(
                    xray_record__upload_timestamp=
                    current_record.upload_timestamp,
                    xray_record__pk__lt=current_record.pk,
                )
            )
            .select_related("xray_record")
            .order_by(
                "-xray_record__upload_timestamp",
                "-xray_record__pk",
            )
            .first()
        )

    @classmethod
    def compare_history(
        cls,
        patient_id,
        threshold: float | None = None,
    ) -> list[dict]:
        """
        Compare all valid AI risk scores in a patient's history.

        Records must be ordered chronologically by:
            1. upload_timestamp
            2. primary key

        Records without an AIResult are skipped.

        The first valid AI score has no prior comparison.
        Each subsequent valid score is compared with the
        immediately preceding valid AI score.

        Note:
            The resulting classification describes a change in
            model-predicted TB risk, not confirmed clinical
            improvement or deterioration.
        """
        records = (
            XrayRecord.objects
            .filter(patient_id=patient_id)
            .select_related("ai_result")
            .order_by(
                "upload_timestamp",
                "pk",
            )
        )

        if threshold is None:
            threshold = cls.get_threshold()

        threshold = float(threshold)

        if not 0 <= threshold <= 1:
            raise ValueError(
                "Progression threshold must be between 0 and 1."
            )

        results = []

        previous_score = None
        previous_record = None

        for record in records:
            try:
                current_ai_result = record.ai_result
            except AIResult.DoesNotExist:
                continue

            current_score = cls.validate_score(
                current_ai_result.risk_score
            )

            comparison = cls.compute(
                current_score=current_score,
                previous_score=previous_score,
                threshold=threshold,
            )

            results.append({
                **comparison,

                "current_transaction_id": str(
                    record.transaction_id
                ),

                "current_timestamp": (
                    record.upload_timestamp
                ),

                "previous_transaction_id": (
                    str(previous_record.transaction_id)
                    if previous_record
                    else None
                ),

                "previous_timestamp": (
                    previous_record.upload_timestamp
                    if previous_record
                    else None
                ),

                "current_model_version": (
                    current_ai_result.model_version
                ),

                "previous_model_version": (
                    previous_record.ai_result.model_version
                    if previous_record
                    else None
                ),

                "comparison_available": (
                    previous_record is not None
                ),
            })

            previous_score = current_score
            previous_record = record

        return results

    @classmethod
    def get_for_record(
        cls,
        current_record: XrayRecord,
        threshold: float | None = None,
    ) -> dict:
        """
        Calculate progression for an XrayRecord.

        This method does not persist any progression data.
        """

        try:
            current_ai_result = current_record.ai_result

        except AIResult.DoesNotExist:

            return {
                "status": cls.NO_PRIOR,
                "current_score": None,
                "previous_score": None,
                "delta": None,
                "abs_delta": None,
                "threshold": (
                    threshold
                    if threshold is not None
                    else cls.get_threshold()
                ),
                "comparison_available": False,
                "reason": "current_ai_result_unavailable",
            }

        previous_result = cls.get_previous_result(
            current_record
        )

        result = cls.compute(
            current_score=current_ai_result.risk_score,
            previous_score=(
                previous_result.risk_score
                if previous_result
                else None
            ),
            threshold=threshold,
        )

        result.update({
            "comparison_available": (
                previous_result is not None
            ),

            "current_transaction_id": str(
                current_record.transaction_id
            ),

            "current_timestamp": (
                current_record.upload_timestamp
            ),

            "previous_transaction_id": (
                str(previous_result.xray_record.transaction_id)
                if previous_result
                else None
            ),

            "previous_timestamp": (
                previous_result.xray_record.upload_timestamp
                if previous_result
                else None
            ),

            "current_model_version": (
                current_ai_result.model_version
            ),

            "previous_model_version": (
                previous_result.model_version
                if previous_result
                else None
            ),
        })

        return result

    @classmethod
    def persist_for_record(
        cls,
        current_record: XrayRecord,
        threshold: float | None = None,
    ) -> ProgressionStatus:
        """
        Persist the computed progression state for a single X-ray record.
        """
        result = cls.get_for_record(current_record, threshold=threshold)
        previous_result = cls.get_previous_result(current_record)
        previous_record = previous_result.xray_record if previous_result else None

        existing_snapshot = ProgressionStatus.objects.filter(
            xray_record=current_record
        ).first()

        defaults = {
            "patient": current_record.patient,
            "previous_record": previous_record,
            "score": result.get("current_score"),
            "previous_score": result.get("previous_score"),
            "delta": result.get("delta"),
            "abs_delta": result.get("abs_delta"),
            "threshold": result.get("threshold", cls.get_threshold()),
            "comparison_available": bool(result.get("comparison_available", False)),
        }

        if existing_snapshot and existing_snapshot.is_overridden:
            defaults.update({
                "status": existing_snapshot.status,
                "reason": existing_snapshot.reason or "Manual override",
                "source": "manual_override",
                "clinical_note": existing_snapshot.clinical_note,
                "is_overridden": True,
                "overridden_by": existing_snapshot.overridden_by,
                "override_timestamp": existing_snapshot.override_timestamp,
            })
        else:
            defaults.update({
                "status": result["status"],
                "reason": result.get("reason", ""),
                "source": "ai",
                "clinical_note": "",
                "is_overridden": False,
                "overridden_by": None,
                "override_timestamp": None,
            })

        snapshot, _ = ProgressionStatus.objects.update_or_create(
            xray_record=current_record,
            defaults=defaults,
        )

        return snapshot

from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import AIResult, ProgressionOverrideAuditLog, ProgressionStatus, XrayRecord
from .services import ProgressionService


def _image_file(filename="xray.png"):
    buffer = BytesIO()
    # Lazy import so module import stays cheap for pure-logic tests.
    from PIL import Image

    Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")


class GetThresholdTests(SimpleTestCase):
    def test_default_threshold_when_setting_unset(self):
        self.assertEqual(
            ProgressionService.get_threshold(),
            ProgressionService.DEFAULT_STABLE_THRESHOLD,
        )
        self.assertEqual(ProgressionService.DEFAULT_STABLE_THRESHOLD, 0.05)

    @override_settings(PROGRESSION_STABLE_THRESHOLD=0.1)
    def test_custom_threshold_from_settings(self):
        self.assertEqual(ProgressionService.get_threshold(), 0.1)

    @override_settings(PROGRESSION_STABLE_THRESHOLD=0)
    def test_boundary_zero_accepted(self):
        self.assertEqual(ProgressionService.get_threshold(), 0)

    @override_settings(PROGRESSION_STABLE_THRESHOLD=1)
    def test_boundary_one_accepted(self):
        self.assertEqual(ProgressionService.get_threshold(), 1)

    @override_settings(PROGRESSION_STABLE_THRESHOLD="0.2")
    def test_numeric_string_coerced(self):
        self.assertEqual(ProgressionService.get_threshold(), 0.2)

    @override_settings(PROGRESSION_STABLE_THRESHOLD="abc")
    def test_non_numeric_rejected(self):
        with self.assertRaisesMessage(
            ValueError, "PROGRESSION_STABLE_THRESHOLD must be numeric."
        ):
            ProgressionService.get_threshold()

    @override_settings(PROGRESSION_STABLE_THRESHOLD=None)
    def test_none_rejected(self):
        with self.assertRaisesMessage(
            ValueError, "PROGRESSION_STABLE_THRESHOLD must be numeric."
        ):
            ProgressionService.get_threshold()

    @override_settings(PROGRESSION_STABLE_THRESHOLD=-0.01)
    def test_below_range_rejected(self):
        with self.assertRaisesMessage(
            ValueError, "PROGRESSION_STABLE_THRESHOLD must be between 0 and 1."
        ):
            ProgressionService.get_threshold()

    @override_settings(PROGRESSION_STABLE_THRESHOLD=1.01)
    def test_above_range_rejected(self):
        with self.assertRaisesMessage(
            ValueError, "PROGRESSION_STABLE_THRESHOLD must be between 0 and 1."
        ):
            ProgressionService.get_threshold()


class ValidateScoreTests(SimpleTestCase):
    def test_valid_boundaries_and_midpoint(self):
        self.assertEqual(ProgressionService.validate_score(0.0), 0.0)
        self.assertEqual(ProgressionService.validate_score(1.0), 1.0)
        self.assertEqual(ProgressionService.validate_score(0.5), 0.5)

    def test_int_and_numeric_string_coerced(self):
        self.assertEqual(ProgressionService.validate_score(0), 0.0)
        self.assertEqual(ProgressionService.validate_score(1), 1.0)
        self.assertEqual(ProgressionService.validate_score("0.73"), 0.73)

    def test_non_numeric_rejected(self):
        for bad in (None, "high", [], {}):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(
                    ValueError, "AI risk score must be numeric."
                ):
                    ProgressionService.validate_score(bad)

    def test_non_finite_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(
                    ValueError, "AI risk score must be finite."
                ):
                    ProgressionService.validate_score(bad)

    def test_out_of_range_rejected(self):
        for bad in (-0.001, -1, 1.001, 2):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(
                    ValueError, "AI risk score must be between 0 and 1."
                ):
                    ProgressionService.validate_score(bad)


class ComputeTests(SimpleTestCase):
    def test_no_prior_shape(self):
        result = ProgressionService.compute(
            current_score=0.6, previous_score=None, threshold=0.05
        )
        self.assertEqual(
            result,
            {
                "status": ProgressionService.NO_PRIOR,
                "current_score": 0.6,
                "previous_score": None,
                "delta": None,
                "abs_delta": None,
                "threshold": 0.05,
            },
        )

    def test_no_prior_resolves_threshold_from_settings(self):
        result = ProgressionService.compute(current_score=0.6, previous_score=None)
        self.assertEqual(result["status"], ProgressionService.NO_PRIOR)
        self.assertEqual(result["threshold"], ProgressionService.DEFAULT_STABLE_THRESHOLD)

    @override_settings(PROGRESSION_STABLE_THRESHOLD=0.1)
    def test_no_prior_uses_configured_threshold(self):
        result = ProgressionService.compute(current_score=0.6, previous_score=None)
        self.assertEqual(result["threshold"], 0.1)

    def test_stable_within_threshold(self):
        result = ProgressionService.compute(
            current_score=0.52, previous_score=0.50, threshold=0.05
        )
        self.assertEqual(result["status"], ProgressionService.STABLE)
        self.assertEqual(result["delta"], 0.02)
        self.assertEqual(result["abs_delta"], 0.02)

    def test_stable_exact_boundary_is_inclusive(self):
        # abs_delta == threshold -> stable per `<=` rule.
        result = ProgressionService.compute(
            current_score=0.55, previous_score=0.50, threshold=0.05
        )
        self.assertEqual(result["status"], ProgressionService.STABLE)
        self.assertEqual(result["abs_delta"], 0.05)

    def test_stable_zero_delta(self):
        result = ProgressionService.compute(
            current_score=0.6, previous_score=0.6, threshold=0.05
        )
        self.assertEqual(result["status"], ProgressionService.STABLE)
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["abs_delta"], 0.0)

    def test_decreased_risk(self):
        result = ProgressionService.compute(
            current_score=0.60, previous_score=0.80, threshold=0.05
        )
        self.assertEqual(result["status"], ProgressionService.DECREASED_RISK)
        self.assertEqual(result["delta"], -0.2)
        self.assertEqual(result["abs_delta"], 0.2)

    def test_increased_risk(self):
        result = ProgressionService.compute(
            current_score=0.60, previous_score=0.30, threshold=0.05
        )
        self.assertEqual(result["status"], ProgressionService.INCREASED_RISK)
        self.assertEqual(result["delta"], 0.3)
        self.assertEqual(result["abs_delta"], 0.3)

    def test_delta_rounded_to_four_decimals(self):
        result = ProgressionService.compute(
            current_score=0.50006, previous_score=0.50005, threshold=0.05
        )
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["abs_delta"], 0.0)
        self.assertEqual(result["status"], ProgressionService.STABLE)

    def test_threshold_zero_any_change_flips(self):
        result = ProgressionService.compute(
            current_score=0.51, previous_score=0.50, threshold=0.0
        )
        self.assertEqual(result["status"], ProgressionService.INCREASED_RISK)

    def test_threshold_one_always_stable(self):
        result = ProgressionService.compute(
            current_score=0.9, previous_score=0.1, threshold=1.0
        )
        self.assertEqual(result["status"], ProgressionService.STABLE)

    def test_invalid_threshold_rejected(self):
        for bad in (-0.1, 1.1):
            with self.subTest(bad=bad):
                with self.assertRaisesMessage(
                    ValueError, "Progression threshold must be between 0 and 1."
                ):
                    ProgressionService.compute(
                        current_score=0.5, previous_score=0.4, threshold=bad
                    )

    def test_invalid_scores_propagate(self):
        with self.assertRaisesMessage(
            ValueError, "AI risk score must be between 0 and 1."
        ):
            ProgressionService.compute(
                current_score=1.5, previous_score=0.5, threshold=0.05
            )
        with self.assertRaisesMessage(
            ValueError, "AI risk score must be between 0 and 1."
        ):
            ProgressionService.compute(
                current_score=0.5, previous_score=-0.1, threshold=0.05
            )


class ProgressionDBMixin:
    @classmethod
    def _create_xray_record(cls, patient, uploader, filename, status="PENDING"):
        return XrayRecord.objects.create(
            patient=patient,
            uploader=uploader,
            raw_image=_image_file(filename),
            status=status,
            file_format="png",
        )

    @classmethod
    def _create_ai_result(cls, record, score, model_version="v-test", label=None):
        return AIResult.objects.create(
            xray_record=record,
            risk_score=score,
            risk_label=label or AIResult.RiskLabel.MODERATE,
            model_version=model_version,
        )

    @staticmethod
    def _set_upload_timestamp(record, timestamp):
        XrayRecord.objects.filter(pk=record.pk).update(upload_timestamp=timestamp)
        record.refresh_from_db()


class GetPreviousResultTests(ProgressionDBMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_root.cleanup()

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tech = user_model.objects.create_user(
            username="prog-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Prog",
            last_name="Patient",
            date_of_birth="1990-01-01",
            sex="M",
            contact_number="09170000001",
        )
        cls.other_patient = Patient.objects.create(
            first_name="Other",
            last_name="Patient",
            date_of_birth="1991-02-02",
            sex="F",
            contact_number="09170000002",
        )

    def _make_chain(self, scores=(0.2, 0.5, 0.8)):
        base = timezone.now() - timedelta(minutes=10)
        records = []
        for i, score in enumerate(scores):
            record = self._create_xray_record(
                patient=self.patient, uploader=self.tech, filename=f"chain-{i}.png"
            )
            self._create_ai_result(record, score, model_version=f"v-{i}")
            self._set_upload_timestamp(record, base + timedelta(minutes=i))
            records.append(record)
        return records

    def test_first_record_has_no_previous(self):
        (first,) = self._make_chain(scores=(0.4,))
        self.assertIsNone(ProgressionService.get_previous_result(first))

    def test_returns_immediately_preceding_result(self):
        first, second, third = self._make_chain()
        prev = ProgressionService.get_previous_result(third)
        self.assertEqual(prev.pk, second.ai_result.pk)
        prev = ProgressionService.get_previous_result(second)
        self.assertEqual(prev.pk, first.ai_result.pk)

    def test_excludes_current_record(self):
        first, second = self._make_chain(scores=(0.3, 0.7))
        # Even when called on the latest record, it must not return itself.
        prev = ProgressionService.get_previous_result(second)
        self.assertNotEqual(prev.pk, second.ai_result.pk)
        self.assertEqual(prev.pk, first.ai_result.pk)

    def test_isolated_by_patient(self):
        first, second = self._make_chain(scores=(0.3, 0.7))
        other = self._create_xray_record(
            patient=self.other_patient, uploader=self.tech, filename="other.png"
        )
        self._create_ai_result(other, 0.99, model_version="v-other")
        self._set_upload_timestamp(other, timezone.now())

        prev = ProgressionService.get_previous_result(second)
        self.assertEqual(prev.pk, first.ai_result.pk)

        # Other patient's record has no prior within its own history.
        self.assertIsNone(ProgressionService.get_previous_result(other))

    def test_tie_breaker_same_timestamp_uses_pk(self):
        first = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="tie-1.png"
        )
        second = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="tie-2.png"
        )
        self._create_ai_result(first, 0.3)
        self._create_ai_result(second, 0.6)
        shared = timezone.now()
        self._set_upload_timestamp(first, shared)
        self._set_upload_timestamp(second, shared)

        self.assertLess(first.pk, second.pk)
        prev = ProgressionService.get_previous_result(second)
        self.assertEqual(prev.pk, first.ai_result.pk)
        self.assertIsNone(ProgressionService.get_previous_result(first))


class CompareHistoryTests(ProgressionDBMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_root.cleanup()

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tech = user_model.objects.create_user(
            username="prog-hist-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Hist",
            last_name="Patient",
            date_of_birth="1992-03-03",
            sex="M",
            contact_number="09170000003",
        )

    def _make_ordered(self, scores, filenames=None, model_versions=None):
        base = timezone.now() - timedelta(minutes=30)
        records = []
        for i, score in enumerate(scores):
            record = self._create_xray_record(
                patient=self.patient,
                uploader=self.tech,
                filename=(filenames or [f"hist-{i}.png"])[i]
                if filenames
                else f"hist-{i}.png",
            )
            self._create_ai_result(
                record,
                score,
                model_version=(model_versions[i] if model_versions else f"v-{i}"),
            )
            self._set_upload_timestamp(record, base + timedelta(minutes=i))
            records.append(record)
        return records

    def test_empty_history(self):
        self.assertEqual(
            ProgressionService.compare_history(self.patient.patient_id), []
        )

    def test_records_without_ai_are_skipped(self):
        lonely = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="lonely.png"
        )
        self._set_upload_timestamp(lonely, timezone.now() - timedelta(minutes=5))
        self.assertEqual(
            ProgressionService.compare_history(self.patient.patient_id), []
        )

    def test_single_valid_score_has_no_prior(self):
        (record,) = self._make_ordered([0.4])
        (entry,) = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.05
        )
        self.assertEqual(entry["status"], ProgressionService.NO_PRIOR)
        self.assertFalse(entry["comparison_available"])
        self.assertEqual(entry["current_score"], 0.4)
        self.assertIsNone(entry["previous_score"])
        self.assertIsNone(entry["delta"])
        self.assertIsNone(entry["abs_delta"])
        self.assertEqual(
            entry["current_transaction_id"], str(record.transaction_id)
        )
        self.assertIsNone(entry["previous_transaction_id"])
        self.assertIsNone(entry["previous_timestamp"])

    def test_chained_classification_and_linkage(self):
        r1, r2, r3 = self._make_ordered(
            [0.2, 0.5, 0.52], model_versions=["m1", "m2", "m3"]
        )
        results = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.05
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(
            [r["status"] for r in results],
            [
                ProgressionService.NO_PRIOR,
                ProgressionService.INCREASED_RISK,
                ProgressionService.STABLE,
            ],
        )
        # Chronological order matches creation order.
        self.assertEqual(
            [r["current_transaction_id"] for r in results],
            [str(r.transaction_id) for r in (r1, r2, r3)],
        )
        # Linkage chain.
        self.assertIsNone(results[0]["previous_transaction_id"])
        self.assertEqual(
            results[1]["previous_transaction_id"], str(r1.transaction_id)
        )
        self.assertEqual(
            results[2]["previous_transaction_id"], str(r2.transaction_id)
        )
        self.assertEqual(results[1]["previous_model_version"], "m1")
        self.assertEqual(results[2]["previous_model_version"], "m2")
        self.assertEqual(results[2]["current_model_version"], "m3")
        self.assertEqual(
            [r["comparison_available"] for r in results], [False, True, True]
        )

    def test_gap_skipped_but_chain_preserved(self):
        base = timezone.now() - timedelta(minutes=30)
        r1 = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="gap-1.png"
        )
        self._create_ai_result(r1, 0.2)
        self._set_upload_timestamp(r1, base)
        r2 = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="gap-2.png"
        )
        self._set_upload_timestamp(r2, base + timedelta(minutes=1))
        r3 = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="gap-3.png"
        )
        self._create_ai_result(r3, 0.8)
        self._set_upload_timestamp(r3, base + timedelta(minutes=2))

        results = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.05
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]["status"], ProgressionService.INCREASED_RISK)
        self.assertEqual(results[1]["previous_score"], 0.2)
        self.assertEqual(
            results[1]["previous_transaction_id"], str(r1.transaction_id)
        )

    def test_custom_threshold_changes_classification(self):
        self._make_ordered([0.50, 0.56])
        ( _, second_default) = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.05
        )
        self.assertEqual(second_default["status"], ProgressionService.INCREASED_RISK)
        (_, second_wide) = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.10
        )
        self.assertEqual(second_wide["status"], ProgressionService.STABLE)

    def test_conflicting_reversal_within_threshold_is_stable(self):
        self._make_ordered([0.42, 0.48, 0.43])
        results = ProgressionService.compare_history(
            self.patient.patient_id, threshold=0.05
        )

        self.assertEqual(
            [item["status"] for item in results],
            [
                ProgressionService.NO_PRIOR,
                ProgressionService.INCREASED_RISK,
                ProgressionService.STABLE,
            ],
        )
        self.assertEqual(results[2]["delta"], -0.05)
        self.assertEqual(results[2]["abs_delta"], 0.05)

    def test_invalid_threshold_rejected(self):
        self._make_ordered([0.2, 0.4])
        with self.assertRaisesMessage(
            ValueError, "Progression threshold must be between 0 and 1."
        ):
            ProgressionService.compare_history(self.patient.patient_id, threshold=2)


class GetForRecordTests(ProgressionDBMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_root.cleanup()

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tech = user_model.objects.create_user(
            username="prog-rec-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Rec",
            last_name="Patient",
            date_of_birth="1993-04-04",
            sex="F",
            contact_number="09170000004",
        )

    def _make_pair(self, old_score=0.3, new_score=0.7):
        base = timezone.now() - timedelta(minutes=10)
        old = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="old.png"
        )
        self._create_ai_result(old, old_score, model_version="m-old")
        self._set_upload_timestamp(old, base)
        new = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="new.png"
        )
        self._create_ai_result(new, new_score, model_version="m-new")
        self._set_upload_timestamp(new, base + timedelta(minutes=5))
        return old, new

    def test_current_without_ai_result(self):
        record = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="no-ai.png"
        )
        result = ProgressionService.get_for_record(record, threshold=0.05)
        self.assertEqual(result["status"], ProgressionService.NO_PRIOR)
        self.assertIsNone(result["current_score"])
        self.assertIsNone(result["previous_score"])
        self.assertIsNone(result["delta"])
        self.assertFalse(result["comparison_available"])
        self.assertEqual(result["reason"], "current_ai_result_unavailable")
        self.assertEqual(result["threshold"], 0.05)

    def test_current_without_ai_resolves_default_threshold(self):
        record = self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="no-ai-2.png"
        )
        result = ProgressionService.get_for_record(record)
        self.assertEqual(
            result["threshold"], ProgressionService.DEFAULT_STABLE_THRESHOLD
        )

    def test_no_previous_but_current_has_ai(self):
        (record,) = [self._create_xray_record(
            patient=self.patient, uploader=self.tech, filename="solo.png"
        )]
        self._create_ai_result(record, 0.65, model_version="m-solo")
        result = ProgressionService.get_for_record(record, threshold=0.05)
        self.assertEqual(result["status"], ProgressionService.NO_PRIOR)
        self.assertEqual(result["current_score"], 0.65)
        self.assertIsNone(result["previous_score"])
        self.assertFalse(result["comparison_available"])
        self.assertEqual(
            result["current_transaction_id"], str(record.transaction_id)
        )
        self.assertIsNone(result["previous_transaction_id"])
        self.assertEqual(result["current_model_version"], "m-solo")
        self.assertIsNone(result["previous_model_version"])

    def test_single_image_history_stays_no_prior_even_at_high_risk(self):
        record = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="solo-high-risk.png",
        )
        self._create_ai_result(record, 0.92, model_version="m-high")

        result = ProgressionService.get_for_record(record, threshold=0.05)

        self.assertEqual(result["status"], ProgressionService.NO_PRIOR)
        self.assertEqual(result["current_score"], 0.92)
        self.assertIsNone(result["previous_score"])
        self.assertFalse(result["comparison_available"])

    def test_with_previous_full_metadata(self):
        old, new = self._make_pair(old_score=0.3, new_score=0.7)
        ai_before = AIResult.objects.count()
        xray_before = XrayRecord.objects.count()

        result = ProgressionService.get_for_record(new, threshold=0.05)

        self.assertEqual(result["status"], ProgressionService.INCREASED_RISK)
        self.assertEqual(result["current_score"], 0.7)
        self.assertEqual(result["previous_score"], 0.3)
        self.assertEqual(result["delta"], 0.4)
        self.assertTrue(result["comparison_available"])
        self.assertEqual(result["current_transaction_id"], str(new.transaction_id))
        self.assertEqual(result["previous_transaction_id"], str(old.transaction_id))
        self.assertEqual(result["current_timestamp"], new.upload_timestamp)
        self.assertEqual(result["previous_timestamp"], old.upload_timestamp)
        self.assertEqual(result["current_model_version"], "m-new")
        self.assertEqual(result["previous_model_version"], "m-old")
        # Does not persist anything.
        self.assertEqual(AIResult.objects.count(), ai_before)
        self.assertEqual(XrayRecord.objects.count(), xray_before)

    def test_threshold_override(self):
        _, new = self._make_pair(old_score=0.50, new_score=0.56)
        default = ProgressionService.get_for_record(new, threshold=0.05)
        wide = ProgressionService.get_for_record(new, threshold=0.10)
        self.assertEqual(default["status"], ProgressionService.INCREASED_RISK)
        self.assertEqual(wide["status"], ProgressionService.STABLE)


class ProgressionPersistenceAPITests(ProgressionDBMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_root.cleanup()

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tech = user_model.objects.create_user(
            username="prog-api-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Api",
            last_name="Patient",
            date_of_birth="1994-05-05",
            sex="F",
            contact_number="09170000005",
        )

    def test_persisted_snapshots_are_saved_per_case_and_returned_in_order(self):
        base = timezone.now() - timedelta(minutes=30)
        first = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="history-1.png",
        )
        self._create_ai_result(first, 0.20, model_version="m1")
        self._set_upload_timestamp(first, base)

        second = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="history-2.png",
        )
        self._create_ai_result(second, 0.60, model_version="m2")
        self._set_upload_timestamp(second, base + timedelta(minutes=5))

        third = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="history-3.png",
        )
        self._create_ai_result(third, 0.58, model_version="m3")
        self._set_upload_timestamp(third, base + timedelta(minutes=10))

        for record in (first, second, third):
            ProgressionService.persist_for_record(record)

        self.assertEqual(ProgressionStatus.objects.filter(patient=self.patient).count(), 3)

        self.client.force_login(self.tech)
        response = self.client.get(f"/api/imaging/cases/{third.pk}/progression/")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["count"], 3)
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(
            [item["status"] for item in payload["results"]],
            [
                ProgressionService.NO_PRIOR,
                ProgressionService.INCREASED_RISK,
                ProgressionService.STABLE,
            ],
        )
        self.assertEqual(payload["results"][0]["transaction_id"], str(first.transaction_id))
        self.assertEqual(payload["results"][1]["previous_transaction_id"], str(first.transaction_id))
        self.assertIn("recorded_at", payload["results"][0])

    def test_paginated_history_supports_longer_histories(self):
        base = timezone.now() - timedelta(minutes=30)
        records = []
        for i, score in enumerate((0.20, 0.30, 0.55, 0.80, 0.76)):
            record = self._create_xray_record(
                patient=self.patient,
                uploader=self.tech,
                filename=f"history-long-{i}.png",
            )
            self._create_ai_result(record, score, model_version=f"m{i}")
            self._set_upload_timestamp(record, base + timedelta(minutes=i * 5))
            ProgressionService.persist_for_record(record)
            records.append(record)

        self.client.force_login(self.tech)
        response = self.client.get(
            f"/api/imaging/cases/{records[-1].pk}/progression/?page=1&page_size=2"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 5)
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["status"], ProgressionService.NO_PRIOR)
        self.assertEqual(payload["results"][1]["status"], ProgressionService.INCREASED_RISK)

    def test_manual_override_requires_non_empty_clinical_note(self):
        radiologist = get_user_model().objects.create_user(
            username="override-radiologist",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        record = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="override-empty-note.png",
        )
        self._create_ai_result(record, 0.30, model_version="m-override")
        ProgressionService.persist_for_record(record)

        self.client.force_login(radiologist)
        response = self.client.post(
            f"/api/imaging/cases/{record.pk}/progression/override/",
            {"status": ProgressionService.DECREASED_RISK, "clinical_note": "   "},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("clinical_note", response.json())

    def test_manual_override_creates_audit_log_entry(self):
        radiologist = get_user_model().objects.create_user(
            username="override-radiologist-audit",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        record = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="override-audit.png",
        )
        self._create_ai_result(record, 0.80, model_version="m-override")
        ProgressionService.persist_for_record(record)

        self.client.force_login(radiologist)
        clinical_note = (
            "Radiologist reviewed the longitudinal trend and changed the "
            "classification based on clinical context."
        )
        response = self.client.post(
            f"/api/imaging/cases/{record.pk}/progression/override/",
            {
                "status": ProgressionService.DECREASED_RISK,
                "clinical_note": clinical_note,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        audit_log = ProgressionOverrideAuditLog.objects.get(xray_record=record)
        self.assertEqual(audit_log.previous_status, ProgressionService.NO_PRIOR)
        self.assertEqual(audit_log.new_status, ProgressionService.DECREASED_RISK)
        self.assertEqual(audit_log.clinical_note, clinical_note)
        self.assertEqual(audit_log.radiologist_id, radiologist.id)

    def test_manual_override_persists_status_and_audit_entry(self):
        radiologist = get_user_model().objects.create_user(
            username="override-radiologist-valid",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        record = self._create_xray_record(
            patient=self.patient,
            uploader=self.tech,
            filename="override-valid.png",
        )
        self._create_ai_result(record, 0.80, model_version="m-override")
        ProgressionService.persist_for_record(record)

        self.client.force_login(radiologist)
        response = self.client.post(
            f"/api/imaging/cases/{record.pk}/progression/override/",
            {
                "status": ProgressionService.DECREASED_RISK,
                "clinical_note": "Radiologist reviewed the current lesion trend and downgraded the risk based on clinical context.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], ProgressionService.DECREASED_RISK)
        self.assertTrue(payload["is_overridden"])
        self.assertEqual(payload["source"], "manual_override")
        self.assertEqual(payload["overridden_by"], radiologist.id)

        progression = ProgressionStatus.objects.get(xray_record=record)
        self.assertTrue(progression.is_overridden)
        self.assertEqual(progression.clinical_note, payload["clinical_note"])
        self.assertEqual(progression.status, ProgressionService.DECREASED_RISK)
        self.assertEqual(progression.overridden_by_id, radiologist.id)
        self.assertIsNotNone(progression.override_timestamp)

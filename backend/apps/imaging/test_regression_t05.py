"""T05 regression suite — Imaging Radiologist Queue & Review Lock.

Executable encoding of the manual regression plan batch T05
(F-2.1.1 - F-2.2.3). Test method names carry the plan case IDs so a run
can be mapped 1:1 back to the plan.

Scope note: the plan is written for manual execution in Chrome. Every
case that is observable through the HTTP contract is asserted here at the
API level via Django's test client. The remaining UI-only cases (Q-02
rendering, E-01 empty state, C-01 warning banner, C-02 read-only gate)
are proxied here by their backing API contract and validated separately
against the frontend components.
"""

from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import AIResult, Annotation, Report, XrayRecord

QUEUE_URL = None  # resolved lazily inside tests (URL names require app registry)
DETAIL_URL_NAME = "imaging:xray-detail"
QUEUE_URL_NAME = "imaging:radiologist-queue"
ANNOTATE_URL_NAME = "imaging:annotate_xray"
REPORT_URL_NAME = "imaging:report_detail"


class _T05Base(TestCase):
    """Shared fixtures: media temp dir, two radiologists, a tech, a physician."""

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
        user = get_user_model()
        cls.rad_a = user.objects.create_user(
            username="t05-rad-a", password="password123", role=UserRole.RADIOLOGIST
        )
        cls.rad_b = user.objects.create_user(
            username="t05-rad-b", password="password123", role=UserRole.RADIOLOGIST
        )
        cls.tech = user.objects.create_user(
            username="t05-tech", password="password123", role=UserRole.RADIOLOGIC_TECH
        )
        cls.physician = user.objects.create_user(
            username="t05-physician", password="password123", role=UserRole.PHYSICIAN
        )
        cls.patient_alpha = Patient.objects.create(
            first_name="John",
            last_name="Alpha",
            date_of_birth="1970-01-01",
            sex="M",
            contact_number="09170000001",
        )
        cls.patient_beta = Patient.objects.create(
            first_name="Maria",
            last_name="Beta",
            date_of_birth="1980-02-02",
            sex="F",
            contact_number="09170000002",
        )

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _image_file(filename="t05.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def _make_record(
        cls,
        patient=None,
        uploader=None,
        filename="t05.png",
        status="PENDING",
        risk=None,
        score=0.5,
        uploaded_at=None,
    ):
        record = XrayRecord.objects.create(
            patient=patient or cls.patient_alpha,
            uploader=uploader or cls.tech,
            raw_image=cls._image_file(filename),
            status=status,
            file_format="png",
        )
        if uploaded_at is not None:
            XrayRecord.objects.filter(pk=record.pk).update(upload_timestamp=uploaded_at)
            record.refresh_from_db()
        if risk is not None:
            AIResult.objects.create(
                xray_record=record,
                risk_score=score,
                risk_label=risk,
                model_version="v-t05",
            )
            record.refresh_from_db()
        return record

    @classmethod
    def _queue_url(cls):
        return reverse(QUEUE_URL_NAME)

    @classmethod
    def _detail_url(cls, record):
        return reverse(DETAIL_URL_NAME, kwargs={"transaction_id": str(record.transaction_id)})

    @classmethod
    def _annotate_url(cls, record):
        return reverse(ANNOTATE_URL_NAME, kwargs={"transaction_id": str(record.transaction_id)})

    @classmethod
    def _report_url(cls, record):
        return reverse(REPORT_URL_NAME, kwargs={"transaction_id": str(record.transaction_id)})

    def _get_queue(self, **params):
        return self.client.get(self._queue_url(), params)

    def _txids(self, response):
        return [row["transaction_id"] for row in response.json()["results"]]


# ---------------------------------------------------------------------------
# 3. Test Cases — Queue retrieval (F-2.1.1)
# ---------------------------------------------------------------------------


class QueueRetrievalTests(_T05Base):
    def test_Q01_queue_retrieval_ordered_paginated_page_size_20(self):
        base = timezone.now() - timedelta(hours=30)
        expected = []
        for i in range(25):
            record = self._make_record(
                filename=f"q01-{i:02d}.png",
                uploaded_at=base + timedelta(minutes=i),
            )
            expected.append(str(record.transaction_id))

        self.client.force_login(self.rad_a)
        response = self._get_queue()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 25)
        self.assertEqual(len(payload["results"]), 20, "default page size must be 20")
        self.assertEqual(self._txids(response), expected[:20], "ordered by upload time (asc)")
        # fields the dashboard renders
        first = payload["results"][0]
        for key in ("transaction_id", "patient", "status", "upload_timestamp"):
            self.assertIn(key, first)
        self.assertIn("patient_id", first["patient"])

    def test_Q02_queue_payload_supports_queue_rendering(self):
        record = self._make_record(
            patient=self.patient_beta,
            risk=AIResult.RiskLabel.HIGH,
            score=0.91,
            filename="q02.png",
        )
        self.client.force_login(self.rad_a)
        response = self._get_queue(search=str(record.transaction_id))

        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        # transaction id, patient, status, AI score — the dashboard columns
        self.assertEqual(row["transaction_id"], str(record.transaction_id))
        self.assertEqual(row["patient"]["patient_id"], self.patient_beta.patient_id)
        self.assertEqual(row["patient"]["first_name"], "Maria")
        self.assertEqual(row["patient"]["last_name"], "Beta")
        self.assertEqual(row["status"], "PENDING")
        self.assertEqual(row["ai_result"]["risk_label"], "HIGH")
        self.assertAlmostEqual(row["ai_result"]["risk_score"], 0.91, places=2)
        self.assertEqual(row["uploader"]["username"], self.tech.username)

    def test_Q03_page_two_is_consistent_and_non_overlapping(self):
        base = timezone.now() - timedelta(hours=30)
        ordered = [
            str(
                self._make_record(
                    filename=f"q03-{i:02d}.png",
                    uploaded_at=base + timedelta(minutes=i),
                ).transaction_id
            )
            for i in range(23)
        ]

        self.client.force_login(self.rad_a)
        page1 = self._get_queue(page=1).json()["results"]
        page2_resp = self._get_queue(page=2)
        page2 = page2_resp.json()["results"]

        self.assertEqual(page2_resp.status_code, 200)
        self.assertEqual(len(page1), 20)
        self.assertEqual(len(page2), 3)
        tx1 = [r["transaction_id"] for r in page1]
        tx2 = [r["transaction_id"] for r in page2]
        self.assertEqual(tx1 + tx2, ordered, "pagination continues ordering without gap/overlap")
        self.assertEqual(set(tx1).intersection(tx2), set())


# ---------------------------------------------------------------------------
# Filters & search (F-2.1.2) and empty state (F-2.1.3)
# ---------------------------------------------------------------------------


class QueueFilterSearchTests(_T05Base):
    def _seed_statuses(self):
        statuses = ["PENDING", "IN_REVIEW", "AI_REVIEWED", "MANUAL_REVIEW", "COMPLETED"]
        return {
            status: self._make_record(filename=f"status-{status}.png", status=status)
            for status in statuses
        }

    def test_F01_filter_each_status_value(self):
        records = self._seed_statuses()
        self.client.force_login(self.rad_a)
        for status, record in records.items():
            with self.subTest(status=status):
                response = self._get_queue(status=status)
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["count"], 1)
                self.assertEqual(self._txids(response), [str(record.transaction_id)])
                self.assertTrue(all(r["status"] == status for r in payload["results"]))

    def test_F02_filter_by_risk_label_low_high(self):
        low = self._make_record(filename="risk-low.png", risk=AIResult.RiskLabel.LOW, score=0.1)
        high = self._make_record(filename="risk-high.png", risk=AIResult.RiskLabel.HIGH, score=0.9)
        self._make_record(filename="risk-none.png")  # no AI result

        self.client.force_login(self.rad_a)
        for label, record in (("LOW", low), ("HIGH", high)):
            with self.subTest(risk=label):
                response = self._get_queue(risk_label=label)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self._txids(response), [str(record.transaction_id)])

    def test_F03_search_by_patient_name(self):
        alpha = self._make_record(patient=self.patient_alpha, filename="search-alpha.png")
        beta = self._make_record(patient=self.patient_beta, filename="search-beta.png")

        self.client.force_login(self.rad_a)
        by_first = self._get_queue(search="John")
        self.assertEqual(self._txids(by_first), [str(alpha.transaction_id)])
        by_last = self._get_queue(search="Beta")
        self.assertEqual(self._txids(by_last), [str(beta.transaction_id)])

    def test_F04_search_by_transaction_id(self):
        target = self._make_record(filename="search-txid.png")
        self._make_record(filename="search-txid-other.png")

        self.client.force_login(self.rad_a)
        response = self._get_queue(search=str(target.transaction_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(self._txids(response), [str(target.transaction_id)])

    def test_F05_combined_status_risk_and_search(self):
        want = self._make_record(
            patient=self.patient_alpha,
            status="AI_REVIEWED",
            risk=AIResult.RiskLabel.HIGH,
            score=0.88,
            filename="combo-want.png",
        )
        # same search name but wrong status
        self._make_record(
            patient=self.patient_alpha,
            status="PENDING",
            risk=AIResult.RiskLabel.HIGH,
            filename="combo-status.png",
        )
        # same status+search but wrong risk
        self._make_record(
            patient=self.patient_alpha,
            status="AI_REVIEWED",
            risk=AIResult.RiskLabel.LOW,
            filename="combo-risk.png",
        )
        # same status+risk but different name
        self._make_record(
            patient=self.patient_beta,
            status="AI_REVIEWED",
            risk=AIResult.RiskLabel.HIGH,
            filename="combo-name.png",
        )

        self.client.force_login(self.rad_a)
        response = self._get_queue(status="AI_REVIEWED", risk_label="HIGH", search="Alpha")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(self._txids(response), [str(want.transaction_id)])

    def test_E01_empty_state_zero_matches(self):
        self._make_record(status="PENDING", filename="e01.png")
        self.client.force_login(self.rad_a)

        by_status = self._get_queue(status="COMPLETED")
        self.assertEqual(by_status.status_code, 200)
        self.assertEqual(by_status.json()["count"], 0)
        self.assertEqual(by_status.json()["results"], [])

        by_search = self._get_queue(search="no-such-patient-xyz")
        self.assertEqual(by_search.status_code, 200)
        self.assertEqual(by_search.json()["count"], 0)
        self.assertEqual(by_search.json()["results"], [])


# ---------------------------------------------------------------------------
# Lock acquisition (F-2.2.1) and conflict handling (F-2.2.2)
# ---------------------------------------------------------------------------


class ReviewLockTests(_T05Base):
    def test_L01_lock_acquired_on_open_and_status_in_review(self):
        record = self._make_record(status="PENDING", filename="l01.png")
        self.client.force_login(self.rad_a)

        response = self.client.get(self._detail_url(record))

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a)
        self.assertIsNotNone(record.lock_timestamp)
        self.assertEqual(record.status, "IN_REVIEW")
        self.assertEqual(response.json()["active_reviewer"], self.rad_a.username)

    def test_C01_second_radiologist_gets_409_with_reviewer_info(self):
        record = self._make_record(status="PENDING", filename="c01.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        self.client.force_login(self.rad_b)
        response = self.client.get(self._detail_url(record))

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["active_reviewer"], self.rad_a.username)
        self.assertIn("locked", payload["detail"].lower())
        self.assertIsNotNone(payload["lock_timestamp"])
        self.assertEqual(payload["transaction_id"], str(record.transaction_id))
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a, "lock owner unchanged")

    def test_C02_read_only_reviewer_cannot_mutate_locked_case(self):
        """Plan expects a save attempt by the non-owner to be blocked with no mutation.

        The UI disables the save controls, but the plan's pass criteria
        (\"no data mutation\") is also asserted at the API boundary as
        defence-in-depth. A failure here means a non-owner can persist
        changes to a locked case through direct API calls.
        """
        record = self._make_record(status="PENDING", filename="c02.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))  # A acquires lock

        self.client.force_login(self.rad_b)
        annotate_response = self.client.post(
            self._annotate_url(record),
            {"bounding_boxes": [{"x": 1, "y": 2, "width": 3, "height": 4, "label": "nodule"}]},
            content_type="application/json",
        )
        report_response = self.client.post(
            self._report_url(record),
            {
                "findings": "B findings",
                "impression": "B impression",
                "recommendation": "B recommendation",
                "severity": "MODERATE",
            },
            content_type="application/json",
        )

        record.refresh_from_db()
        self.assertIn(annotate_response.status_code, (403, 409), "annotation save must be blocked")
        self.assertIn(report_response.status_code, (403, 409), "report save must be blocked")
        self.assertFalse(
            Annotation.objects.filter(xray_record=record, radiologist=self.rad_b).exists(),
            "no annotation should be persisted by the non-owner",
        )
        self.assertFalse(
            Report.objects.filter(xray_record=record).exists(),
            "no report should be persisted by the non-owner",
        )

    def test_C03_lock_released_when_owner_leaves(self):
        """A opens then releases; B can immediately open the case (plan C-03)."""
        record = self._make_record(status="PENDING", filename="c03.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        release_url = reverse(
            "imaging:release_review_lock",
            kwargs={"transaction_id": str(record.transaction_id)},
        )
        release_response = self.client.post(release_url)
        self.assertEqual(release_response.status_code, 204)
        record.refresh_from_db()
        self.assertIsNone(record.active_reviewer)
        self.assertIsNone(record.lock_timestamp)
        self.assertEqual(record.status, "PENDING", "workflow status restored on release")

        self.client.force_login(self.rad_b)
        response = self.client.get(self._detail_url(record))
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_b)
        self.assertEqual(record.status, "IN_REVIEW")

    def test_C03_release_is_owner_only(self):
        """A non-owner cannot release someone else's lock."""
        record = self._make_record(status="PENDING", filename="c03-owner.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        self.client.force_login(self.rad_b)
        release_url = reverse(
            "imaging:release_review_lock",
            kwargs={"transaction_id": str(record.transaction_id)},
        )
        response = self.client.post(release_url)
        self.assertEqual(response.status_code, 204)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a, "B must not release A's lock")

    def test_C03_release_lock_model_helper(self):
        """release_lock() clears ownership when invoked directly."""
        record = self._make_record(status="PENDING", filename="c03-model.png")
        record.acquire_lock(self.rad_a)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a)

        record.release_lock()
        record.refresh_from_db()
        self.assertIsNone(record.active_reviewer)
        self.assertIsNone(record.lock_timestamp)


class LockLifecycleTests(_T05Base):
    """Release, status restoration, self-healing expiry and finalize behaviour."""

    def test_status_restored_for_each_pre_review_status(self):
        for status in ("PENDING", "AI_REVIEWED", "MANUAL_REVIEW"):
            with self.subTest(status=status):
                record = self._make_record(status=status, filename=f"restore-{status}.png")
                self.client.force_login(self.rad_a)
                self.client.get(self._detail_url(record))
                record.refresh_from_db()
                self.assertEqual(record.status, "IN_REVIEW")
                self.assertEqual(record.status_before_review, status)

                record.release_lock()
                record.refresh_from_db()
                self.assertEqual(record.status, status, "pre-review status restored")
                self.assertIsNone(record.status_before_review)

    def test_expired_lock_self_heals_on_queue_read(self):
        record = self._make_record(status="IN_REVIEW", filename="heal-queue.png")
        record.active_reviewer = self.rad_a
        record.lock_timestamp = timezone.now() - timedelta(minutes=61)
        record.status_before_review = "AI_REVIEWED"
        record.save(update_fields=["active_reviewer", "lock_timestamp", "status_before_review"])

        self.client.force_login(self.rad_b)
        response = self._get_queue(search=str(record.transaction_id))
        self.assertEqual(response.status_code, 200)

        record.refresh_from_db()
        self.assertIsNone(record.active_reviewer, "stale lock cleared on queue read")
        self.assertIsNone(record.lock_timestamp)
        self.assertEqual(record.status, "AI_REVIEWED", "status restored after expiry")
        self.assertEqual(response.json()["results"][0]["status"], "AI_REVIEWED")

    def test_expired_lock_self_heals_on_detail_read(self):
        record = self._make_record(status="IN_REVIEW", filename="heal-detail.png")
        record.active_reviewer = self.rad_a
        record.lock_timestamp = timezone.now() - timedelta(minutes=61)
        record.status_before_review = "MANUAL_REVIEW"
        record.save(update_fields=["active_reviewer", "lock_timestamp", "status_before_review"])

        self.client.force_login(self.rad_b)
        response = self.client.get(self._detail_url(record))
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_b)
        self.assertEqual(record.status, "IN_REVIEW")
        self.assertEqual(record.status_before_review, "MANUAL_REVIEW")

    def test_finalize_annotation_releases_lock(self):
        record = self._make_record(status="PENDING", filename="finalize-annotate.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))
        record.refresh_from_db()
        self.assertEqual(record.status, "IN_REVIEW")

        response = self.client.post(
            self._annotate_url(record),
            {"bounding_boxes": [{"x": 1, "y": 2, "width": 3, "height": 4, "label": "nodule"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        record.refresh_from_db()
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNone(record.active_reviewer, "lock released on finalize")
        self.assertIsNone(record.lock_timestamp)

    def test_report_submission_releases_lock(self):
        record = self._make_record(status="PENDING", filename="finalize-report.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        report_url = self._report_url(record)
        self.client.post(
            report_url,
            {
                "findings": "Findings",
                "impression": "Impression",
                "recommendation": "Recommendation",
                "severity": "MODERATE",
            },
            content_type="application/json",
        )
        response = self.client.patch(report_url, {"status": "SUBMITTED"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        record.refresh_from_db()
        self.assertIsNone(record.active_reviewer, "lock released when report is finalized")
        self.assertIsNone(record.lock_timestamp)

    def test_renew_endpoint_extends_owner_lock(self):
        record = self._make_record(status="PENDING", filename="renew.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        stale = timezone.now() - timedelta(minutes=10)
        XrayRecord.objects.filter(pk=record.pk).update(lock_timestamp=stale)

        renew_url = reverse(
            "imaging:renew_review_lock",
            kwargs={"transaction_id": str(record.transaction_id)},
        )
        response = self.client.post(renew_url)
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a)
        self.assertGreater(record.lock_timestamp, stale, "heartbeat advances lock_timestamp")

    def test_renew_endpoint_rejects_non_owner(self):
        record = self._make_record(status="PENDING", filename="renew-conflict.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))

        self.client.force_login(self.rad_b)
        renew_url = reverse(
            "imaging:renew_review_lock",
            kwargs={"transaction_id": str(record.transaction_id)},
        )
        response = self.client.post(renew_url)
        self.assertEqual(response.status_code, 409)
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a)

    def test_logout_releases_locks(self):
        record = self._make_record(status="PENDING", filename="logout.png")
        self.client.force_login(self.rad_a)
        self.client.get(self._detail_url(record))
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_a)

        self.client.post(reverse("accounts:logout"))
        record.refresh_from_db()
        self.assertIsNone(record.active_reviewer, "logout frees held locks")
        self.assertIsNone(record.lock_timestamp)
        self.assertEqual(record.status, "PENDING")


# ---------------------------------------------------------------------------
# Lock expiry (F-2.2.3)
# ---------------------------------------------------------------------------


class LockExpiryTests(_T05Base):
    def test_X01_lock_expired_past_60_minutes(self):
        fresh = self._make_record(status="PENDING", filename="x01-fresh.png")
        fresh.active_reviewer = self.rad_a
        fresh.lock_timestamp = timezone.now() - timedelta(minutes=59)
        fresh.save(update_fields=["active_reviewer", "lock_timestamp"])
        self.assertFalse(fresh.lock_has_expired(), "59 min lock is still active")

        stale = self._make_record(status="PENDING", filename="x01-stale.png")
        stale.active_reviewer = self.rad_a
        stale.lock_timestamp = timezone.now() - timedelta(minutes=61)
        stale.save(update_fields=["active_reviewer", "lock_timestamp"])
        self.assertTrue(stale.lock_has_expired(), "61 min lock is expired")

    def test_X02_second_radiologist_takes_over_expired_lock(self):
        record = self._make_record(status="PENDING", filename="x02.png")
        record.active_reviewer = self.rad_a
        record.lock_timestamp = timezone.now() - timedelta(minutes=61)
        record.save(update_fields=["active_reviewer", "lock_timestamp"])

        self.client.force_login(self.rad_b)
        response = self.client.get(self._detail_url(record))

        self.assertEqual(response.status_code, 200, "no 409 for an expired lock")
        record.refresh_from_db()
        self.assertEqual(record.active_reviewer, self.rad_b)
        self.assertEqual(record.status, "IN_REVIEW")
        self.assertEqual(response.json()["active_reviewer"], self.rad_b.username)


# ---------------------------------------------------------------------------
# Negative / edge cases
# ---------------------------------------------------------------------------


class QueueNegativeTests(_T05Base):
    def test_N01_queue_denied_for_radiologic_tech(self):
        self.client.force_login(self.tech)
        response = self._get_queue()
        self.assertEqual(response.status_code, 403)

    def test_N02_queue_denied_for_physician(self):
        self.client.force_login(self.physician)
        response = self._get_queue()
        self.assertEqual(response.status_code, 403)

    def test_N03_invalid_page_params_are_graceful(self):
        self._make_record(filename="n03.png")
        self.client.force_login(self.rad_a)
        for params in ({"page": "-1"}, {"page": "abc"}, {"page": "0"}, {"page": "999"}):
            with self.subTest(params=params):
                response = self._get_queue(**params)
                self.assertNotEqual(response.status_code, 500)
                self.assertIn(response.status_code, (200, 404))

    def test_N04_special_and_oversized_search_input_is_safe(self):
        target = self._make_record(patient=self.patient_alpha, filename="n04.png")
        self.client.force_login(self.rad_a)
        probes = [
            "' OR 1=1 --",
            "%; DROP TABLE imaging_xrayrecord; --",
            "x" * 5000,
            "\u00e9\u4e2d\u6587\U0001f600",
            " ', \"<script>alert(1)</script>",
        ]
        for probe in probes:
            with self.subTest(probe=probe[:20]):
                response = self._get_queue(search=probe)
                self.assertNotEqual(response.status_code, 500)
                self.assertIn(response.status_code, (200, 400))
        # table still intact and records still queryable
        self.assertTrue(XrayRecord.objects.filter(pk=target.pk).exists())

    def test_N05_unauthenticated_queue_cannot_read_records(self):
        response = self._get_queue()
        self.assertIn(response.status_code, (302, 401, 403))
        if response.status_code == 200:
            self.fail("unauthenticated request must not return queue data")

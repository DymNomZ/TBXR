from datetime import timedelta
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from PIL import Image
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import Report, XrayRecord
from .serializers import ReportCreateSerializer


class _ReportTestBase(TestCase):
    """Shared harness: media temp dir, radiologist + tech users, one COMPLETED record."""

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
        cls.rad = user_model.objects.create_user(
            username="report-rad",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        cls.tech = user_model.objects.create_user(
            username="report-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Report",
            last_name="Patient",
            date_of_birth="1985-05-15",
            sex="F",
            contact_number="09171234567",
        )
        cls.completed_record = cls._create_xray_record(cls.patient, cls.rad, "report.png", "COMPLETED")

    @classmethod
    def _image_file(cls, filename):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def _create_xray_record(cls, patient, uploader, filename, status):
        return XrayRecord.objects.create(
            patient=patient,
            uploader=uploader,
            raw_image=cls._image_file(filename),
            status=status,
            file_format="png",
        )

    def _report_url(self, transaction_id):
        return reverse("imaging:report_detail", kwargs={"transaction_id": str(transaction_id)})

    def _valid_payload(self, **overrides):
        payload = {
            "findings": "Bilateral upper lobe opacities.",
            "impression": "Suggestive of pulmonary TB.",
            "recommendation": "GeneXpert and sputum AFB.",
            "severity": "MODERATE",
        }
        payload.update(overrides)
        return payload


class ReportDetailViewTests(_ReportTestBase):
    """API-level coverage of the draft/submit state machine in report_detail (views.py)."""

    def test_get_report_not_found(self):
        """GET on a record with no report returns 404."""
        self.client.force_login(self.rad)
        response = self.client.get(self._report_url(self.completed_record.transaction_id))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Report not found for this X-ray.")

    def test_post_creates_draft(self):
        """POST with complete data creates a DRAFT report (201)."""
        self.client.force_login(self.rad)
        response = self.client.post(
            self._report_url(self.completed_record.transaction_id),
            self._valid_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertEqual(response.data["severity"], "MODERATE")
        report = Report.objects.get(xray_record=self.completed_record)
        self.assertEqual(report.status, "DRAFT")
        self.assertIsNone(report.created_by)  # drafts are not stamped as finalized

    def test_post_is_idempotent(self):
        """A second POST updates the same report row (200), no duplicate created."""
        self.client.force_login(self.rad)
        url = self._report_url(self.completed_record.transaction_id)
        self.client.post(url, self._valid_payload(), content_type="application/json")
        second = self.client.post(
            url,
            self._valid_payload(findings="Updated findings."),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Report.objects.filter(xray_record=self.completed_record).count(), 1)
        report = Report.objects.get(xray_record=self.completed_record)
        self.assertEqual(report.findings, "Updated findings.")

    def test_post_forces_draft_status(self):
        """POST cannot finalize: even a SUBMITTED status in the body is forced to DRAFT."""
        self.client.force_login(self.rad)
        response = self.client.post(
            self._report_url(self.completed_record.transaction_id),
            self._valid_payload(status="SUBMITTED"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        report = Report.objects.get(xray_record=self.completed_record)
        self.assertEqual(report.status, "DRAFT")

    def test_post_accepts_empty_fields(self):
        """Draft creation permits empty text fields and missing severity."""
        self.client.force_login(self.rad)
        response = self.client.post(
            self._report_url(self.completed_record.transaction_id),
            {"findings": "", "impression": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertEqual(response.data["severity"], "NORMAL")

    def test_post_rejects_invalid_severity(self):
        """POST with an unknown severity value returns 400 field errors."""
        self.client.force_login(self.rad)
        response = self.client.post(
            self._report_url(self.completed_record.transaction_id),
            self._valid_payload(severity="EXTREME"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("severity", response.data)

    def test_patch_without_report_returns_404(self):
        """PATCH on a record with no report returns 404."""
        self.client.force_login(self.rad)
        response = self.client.patch(
            self._report_url(self.completed_record.transaction_id),
            {"findings": "x"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Report not found for this X-ray.")

    def test_patch_preserves_untouched_fields(self):
        """Partial PATCH updates only the given field and keeps the rest."""
        self.client.force_login(self.rad)
        url = self._report_url(self.completed_record.transaction_id)
        self.client.post(url, self._valid_payload(findings="Keep me."), content_type="application/json")
        response = self.client.patch(url, {"severity": "SEVERE"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["severity"], "SEVERE")
        self.assertEqual(response.data["findings"], "Keep me.")
        self.assertEqual(response.data["status"], "DRAFT")

    def test_patch_rejected_when_finalized(self):
        """A finalized (SUBMITTED) report cannot be modified."""
        self.client.force_login(self.rad)
        Report.objects.create(
            xray_record=self.completed_record,
            findings="Final findings",
            impression="Final impression",
            recommendation="Final rec",
            severity=Report.SeverityChoices.SEVERE,
            status="SUBMITTED",
            created_by=self.rad,
        )
        response = self.client.patch(
            self._report_url(self.completed_record.transaction_id),
            {"findings": "Changed"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Cannot modify a finalized report.")

    def test_patch_submit_stamps_created_by(self):
        """Submitting via PATCH sets created_by to the acting radiologist."""
        self.client.force_login(self.rad)
        url = self._report_url(self.completed_record.transaction_id)
        self.client.post(url, self._valid_payload(), content_type="application/json")
        response = self.client.patch(url, {"status": "SUBMITTED"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        self.assertEqual(response.data["created_by"]["username"], "report-rad")
        report = Report.objects.get(xray_record=self.completed_record)
        self.assertEqual(report.created_by, self.rad)

    def test_technician_cannot_patch(self):
        """Non-radiologists are blocked by the role guard."""
        self.client.force_login(self.tech)
        response = self.client.patch(
            self._report_url(self.completed_record.transaction_id),
            {"findings": "nope"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class ReportCreateSerializerTests(_ReportTestBase):
    """Unit-level coverage of ReportCreateSerializer validation (serializers.py)."""

    def test_valid_submitted_payload_passes(self):
        serializer = ReportCreateSerializer(data=self._valid_payload(status="SUBMITTED"))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_submitted_missing_field_rejected(self):
        payload = self._valid_payload(status="SUBMITTED")
        del payload["recommendation"]
        serializer = ReportCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["recommendation"],
            ["This field is required for final submission."],
        )

    def test_empty_strings_treated_as_missing(self):
        payload = self._valid_payload(status="SUBMITTED", impression="")
        serializer = ReportCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("impression", serializer.errors)
        self.assertEqual(
            serializer.errors["impression"][0],
            "This field is required for final submission.",
        )

    def test_draft_accepts_missing_fields(self):
        serializer = ReportCreateSerializer(data={"status": "DRAFT"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_partial_update_submit_falls_back_to_instance_and_stamps_created_by(self):
        """Finalizing via PATCH uses instance values for missing fields and stamps created_by."""
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="Instance findings",
            impression="Instance impression",
            recommendation="Instance rec",
            severity=Report.SeverityChoices.MILD,
            status="DRAFT",
        )
        serializer = ReportCreateSerializer(
            instance=report,
            data={"status": "SUBMITTED"},
            partial=True,
            context={"request": SimpleNamespace(user=self.rad)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.status, "SUBMITTED")
        self.assertEqual(updated.findings, "Instance findings")  # kept from instance
        self.assertIsNotNone(updated.created_by)
        self.assertEqual(updated.created_by, self.rad)


class ReviewLockTests(_ReportTestBase):
    """Concurrency checks for radiologist case review locking."""

    def _xray_detail_url(self, transaction_id):
        return reverse("imaging:xray-detail", kwargs={"transaction_id": str(transaction_id)})

    def test_radiologist_acquires_lock_when_opening_case(self):
        self.client.force_login(self.rad)

        response = self.client.get(self._xray_detail_url(self.completed_record.transaction_id))

        self.assertEqual(response.status_code, 200)
        self.completed_record.refresh_from_db()
        self.assertEqual(self.completed_record.active_reviewer, self.rad)
        self.assertIsNotNone(self.completed_record.lock_timestamp)
        self.assertEqual(response.data["active_reviewer"], self.rad.username)

    def test_second_radiologist_is_rejected_when_lock_is_active(self):
        second_rad = get_user_model().objects.create_user(
            username="second-rad",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        self.completed_record.active_reviewer = self.rad
        self.completed_record.lock_timestamp = timezone.now()
        self.completed_record.save(update_fields=["active_reviewer", "lock_timestamp"])

        self.client.force_login(second_rad)
        response = self.client.get(self._xray_detail_url(self.completed_record.transaction_id))

        self.assertEqual(response.status_code, 409)
        self.assertIn("currently locked", response.data["detail"].lower())
        self.assertEqual(response.data["active_reviewer"], self.rad.username)
        self.assertEqual(response.data["transaction_id"], str(self.completed_record.transaction_id))

    def test_lock_expires_after_timeout(self):
        second_rad = get_user_model().objects.create_user(
            username="third-rad",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        self.completed_record.active_reviewer = self.rad
        self.completed_record.lock_timestamp = timezone.now() - timedelta(minutes=61)
        self.completed_record.save(update_fields=["active_reviewer", "lock_timestamp"])

        self.client.force_login(second_rad)
        response = self.client.get(self._xray_detail_url(self.completed_record.transaction_id))

        self.assertEqual(response.status_code, 200)
        self.completed_record.refresh_from_db()
        self.assertEqual(self.completed_record.active_reviewer, second_rad)
        self.assertIsNotNone(self.completed_record.lock_timestamp)
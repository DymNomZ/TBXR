import uuid
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import AIResult, Annotation, Notification, ProcessedImage, Report, XrayRecord


class ReportSmokeTests(TestCase):
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
            username="smoke-rad",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        cls.tech = user_model.objects.create_user(
            username="smoke-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Smoke",
            last_name="Patient",
            date_of_birth="1990-01-01",
            sex="M",
            contact_number="09171234567",
        )
        cls.completed_record = cls._create_xray_record(cls.patient, cls.rad, "completed.png", "COMPLETED")
        cls.pending_record = cls._create_xray_record(cls.patient, cls.rad, "pending.png", "PENDING")

        AIResult.objects.create(
            xray_record=cls.completed_record,
            risk_score=0.73,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="v-test",
        )
        Annotation.objects.create(
            xray_record=cls.completed_record,
            radiologist=cls.rad,
            bounding_boxes=[{"x": 10, "y": 20, "width": 30, "height": 40, "label": "nodule"}],
            notes="Review needed",
        )

    @staticmethod
    def _image_file(filename="xray.png"):
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
        return reverse("imaging:generate_report", kwargs={"transaction_id": str(transaction_id)})

    def test_completed_record_returns_pdf(self):
        self.client.force_login(self.rad)
        fake_run = SimpleNamespace(
            stdout=b"%PDF-1.4 fake pdf bytes",
            stderr=b"",
            returncode=0,
        )

        with mock.patch("apps.imaging.views.subprocess.run", return_value=fake_run) as run_mock:
            response = self.client.get(self._report_url(self.completed_record.transaction_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="tbxr_report_{self.completed_record.transaction_id}.pdf"',
        )
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"%PDF"))

        run_mock.assert_called_once()
        args, kwargs = run_mock.call_args
        self.assertEqual(args[0][0], "node")
        self.assertIs(kwargs.get("capture_output"), True)
        self.assertIs(kwargs.get("check"), True)

    def test_pending_record_returns_400(self):
        self.client.force_login(self.rad)
        response = self.client.get(self._report_url(self.pending_record.transaction_id))
        self.assertEqual(response.status_code, 400)

    def test_non_radiologist_returns_403(self):
        self.client.force_login(self.tech)
        response = self.client.get(self._report_url(self.completed_record.transaction_id))
        self.assertEqual(response.status_code, 403)

    def test_missing_record_returns_404(self):
        self.client.force_login(self.rad)
        response = self.client.get(self._report_url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)

    # --- New Report Model Tests ---

    def _report_detail_url(self, transaction_id):
        return reverse("imaging:report_detail", kwargs={"transaction_id": str(transaction_id)})

    def test_create_report_draft(self):
        """Radiologist can create a draft report (status='DRAFT')."""
        self.client.force_login(self.rad)
        url = self._report_detail_url(self.completed_record.transaction_id)
        payload = {
            "findings": "Right upper lobe opacity noted.",
            "impression": "Suggestive of active TB.",
            "recommendation": "Sputum AFB and GeneXpert recommended.",
            "severity": "MODERATE",
        }
        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertEqual(response.data["severity"], "MODERATE")
        self.assertEqual(response.data["findings"], "Right upper lobe opacity noted.")

    def test_create_report_draft_allows_empty_fields(self):
        """Draft creation allows empty required fields."""
        self.client.force_login(self.rad)
        url = self._report_detail_url(self.completed_record.transaction_id)
        payload = {}  # All fields empty
        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        # severity defaults to NORMAL
        self.assertEqual(response.data["severity"], "NORMAL")

    def test_retrieve_report(self):
        """Radiologist can retrieve an existing report."""
        self.client.force_login(self.rad)
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="Test findings",
            impression="Test impression",
            recommendation="Test recommendation",
            severity=Report.SeverityChoices.MILD,
            status="DRAFT",
        )
        url = self._report_detail_url(self.completed_record.transaction_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], report.id)
        self.assertEqual(response.data["severity"], "MILD")

    def test_update_report_draft(self):
        """Radiologist can PATCH a draft report."""
        self.client.force_login(self.rad)
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="Initial findings",
            impression="Initial impression",
            recommendation="Initial rec",
            severity=Report.SeverityChoices.NORMAL,
            status="DRAFT",
        )
        url = self._report_detail_url(self.completed_record.transaction_id)
        response = self.client.patch(url, {"severity": "SEVERE"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["severity"], "SEVERE")
        report.refresh_from_db()
        self.assertEqual(report.severity, "SEVERE")

    def test_cannot_update_finalized_report(self):
        """Finalized reports cannot be modified."""
        self.client.force_login(self.rad)
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="Findings",
            impression="Impression",
            recommendation="Rec",
            severity=Report.SeverityChoices.NORMAL,
            status="SUBMITTED",
            created_by=self.rad,
        )
        url = self._report_detail_url(self.completed_record.transaction_id)
        response = self.client.patch(url, {"findings": "Changed"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("finalized", response.data["detail"].lower())

    def test_final_submit_rejects_missing_fields(self):
        """Final submit (status='SUBMITTED') rejects missing required fields."""
        self.client.force_login(self.rad)
        # First create a draft
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="",  # missing
            impression="Impression",
            recommendation="Rec",
            severity=Report.SeverityChoices.NORMAL,
            status="DRAFT",
        )
        url = self._report_detail_url(self.completed_record.transaction_id)
        # Try to finalize with missing fields
        response = self.client.patch(url, {"status": "SUBMITTED"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        # Should have field-level errors for missing fields
        self.assertIn("findings", response.data)
        self.assertEqual(response.data["findings"][0], "This field is required for final submission.")

    def test_final_submit_succeeds_with_all_fields(self):
        """Final submit succeeds when all required fields are present."""
        self.client.force_login(self.rad)
        report = Report.objects.create(
            xray_record=self.completed_record,
            findings="Complete findings",
            impression="Complete impression",
            recommendation="Complete recommendation",
            severity=Report.SeverityChoices.MODERATE,
            status="DRAFT",
        )
        url = self._report_detail_url(self.completed_record.transaction_id)
        response = self.client.patch(url, {"status": "SUBMITTED"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        self.assertEqual(response.data["created_by"]["username"], "smoke-rad")
        report.refresh_from_db()
        self.assertEqual(report.status, "SUBMITTED")
        self.assertEqual(report.created_by, self.rad)

    def test_draft_then_finalize_workflow(self):
        """Full workflow: create draft, update, then finalize."""
        self.client.force_login(self.rad)
        url = self._report_detail_url(self.completed_record.transaction_id)
        # Create draft with minimal data
        response = self.client.post(url, {"severity": "MILD"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "DRAFT")
        # Update draft with remaining fields
        response = self.client.patch(url, {
            "findings": "Updated findings",
            "impression": "Updated impression",
            "recommendation": "Updated recommendation",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "DRAFT")
        # Finalize
        response = self.client.patch(url, {"status": "SUBMITTED"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "SUBMITTED")
        report = Report.objects.get(xray_record=self.completed_record)
        self.assertEqual(report.status, "SUBMITTED")
        self.assertEqual(report.created_by, self.rad)

    def test_tech_cannot_create_report(self):
        """Technologists cannot create reports."""
        self.client.force_login(self.tech)
        url = self._report_detail_url(self.completed_record.transaction_id)
        response = self.client.post(url, {"findings": "x", "impression": "x", "recommendation": "x", "severity": "NORMAL"}, content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_generate_report_uses_persisted_report_data(self):
        """PDF generation uses Report model fields."""
        self.client.force_login(self.rad)
        Report.objects.create(
            xray_record=self.completed_record,
            findings="Persistent findings",
            impression="Persistent impression",
            recommendation="Persistent rec",
            severity=Report.SeverityChoices.CRITICAL,
            status="SUBMITTED",
            created_by=self.rad,
        )
        fake_run = SimpleNamespace(
            stdout=b"%PDF-1.4 fake pdf bytes",
            stderr=b"",
            returncode=0,
        )
        url = reverse("imaging:generate_report", kwargs={"transaction_id": str(self.completed_record.transaction_id)})
        with mock.patch("apps.imaging.views.subprocess.run", return_value=fake_run):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class PhysicianDashboardSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.physician = user_model.objects.create_user(
            username="smoke-physician",
            password="password123",
            role=UserRole.PHYSICIAN,
        )
        cls.radiologist = user_model.objects.create_user(
            username="smoke-rad-physician",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        cls.technologist = user_model.objects.create_user(
            username="smoke-tech-physician",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )

        patient = Patient.objects.create(
            first_name="Physician",
            last_name="Smoke",
            date_of_birth="1992-06-06",
            sex="F",
            contact_number="09170001111",
        )

        xray_record = XrayRecord.objects.create(
            patient=patient,
            uploader=cls.technologist,
            raw_image=ReportSmokeTests._image_file("physician-smoke.png"),
            status="COMPLETED",
            file_format="png",
        )

        AIResult.objects.create(
            xray_record=xray_record,
            risk_score=0.89,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="smoke-v1",
        )
        Report.objects.create(
            xray_record=xray_record,
            findings="Dense right upper lobe infiltrate.",
            impression="Highly suspicious for active TB.",
            recommendation="Urgent physician follow-up.",
            severity=Report.SeverityChoices.CRITICAL,
            status="SUBMITTED",
            created_by=cls.radiologist,
        )
        Notification.objects.create(
            recipient=cls.physician,
            message=f"Report ready for Physician Smoke (case {xray_record.transaction_id}).",
            read_status=False,
        )

    def test_physician_dashboard_smoke_flow(self):
        self.client.force_login(self.physician)

        response = self.client.get("/api/physician/dashboard", {"severity": "CRITICAL"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["summary"]["finalized_report_count"], 1)
        self.assertIn("pending_alerts", payload)
        self.assertTrue(any("Report ready" in item["message"] for item in payload["pending_alerts"]))


class AIFailureRetrySmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.technologist = user_model.objects.create_user(
            username="smoke-tech-retry",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.patient = Patient.objects.create(
            first_name="Retry",
            last_name="Smoke",
            date_of_birth="1993-03-03",
            sex="M",
            contact_number="09170002222",
        )
        cls.xray_record = XrayRecord.objects.create(
            patient=cls.patient,
            uploader=cls.technologist,
            raw_image=ReportSmokeTests._image_file("retry-smoke.png"),
            status="PENDING",
            file_format="png",
        )
        ProcessedImage.objects.create(
            xray_record=cls.xray_record,
            processed_image=ReportSmokeTests._image_file("retry-processed.png"),
            preprocessing_metadata={"source": "smoke_test"},
        )

    def test_ai_failure_then_retry_succeeds(self):
        self.client.force_login(self.technologist)
        endpoint = reverse("imaging:analyse_xray", kwargs={"transaction_id": str(self.xray_record.transaction_id)})

        failing_inference = SimpleNamespace(
            MODEL_VERSION="smoke-v1",
            predict=mock.Mock(side_effect=RuntimeError("TIMEOUT: model runner unavailable")),
            generate_heatmap=mock.Mock(return_value=""),
        )

        with mock.patch("apps.imaging.views._get_inference_module", return_value=failing_inference):
            failed_response = self.client.post(endpoint, content_type="application/json")

        self.assertEqual(failed_response.status_code, 202)
        self.assertEqual(failed_response.data["status"], "MANUAL_REVIEW")
        self.assertIn("errors", failed_response.data)

        retry_inference = SimpleNamespace(
            MODEL_VERSION="smoke-v1",
            predict=mock.Mock(return_value={"risk_score": 0.62, "risk_label": "Moderate"}),
            generate_heatmap=mock.Mock(return_value=""),
        )

        with mock.patch("apps.imaging.views._get_inference_module", return_value=retry_inference):
            retry_response = self.client.post(endpoint, content_type="application/json")

        self.assertIn(retry_response.status_code, (200, 201))
        self.assertEqual(retry_response.data["risk_label"], "MODERATE")
        self.xray_record.refresh_from_db()
        self.assertEqual(self.xray_record.status, "AI_REVIEWED")

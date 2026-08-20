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

from .models import AIResult, Annotation, XrayRecord


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

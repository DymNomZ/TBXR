from datetime import timedelta
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import AIResult, Notification, Report, XrayRecord


class PhysicianDashboardTests(TestCase):
    endpoint = "/api/physician/dashboard"

    @classmethod
    def _image_file(cls, filename="xray.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.physician = user_model.objects.create_user(
            username="physician-one",
            password="password123",
            role=UserRole.PHYSICIAN,
            first_name="Ana",
            last_name="Reyes",
        )
        cls.radiologist = user_model.objects.create_user(
            username="rad-one",
            password="password123",
            role=UserRole.RADIOLOGIST,
            first_name="Marco",
            last_name="Santos",
        )
        cls.technologist = user_model.objects.create_user(
            username="tech-one",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.other_physician = user_model.objects.create_user(
            username="physician-two",
            password="password123",
            role=UserRole.PHYSICIAN,
        )

        cls.patient_one = Patient.objects.create(
            first_name="Juan",
            last_name="Dela Cruz",
            date_of_birth="1990-01-01",
            sex="M",
            contact_number="09171234567",
        )
        cls.patient_two = Patient.objects.create(
            first_name="Maria",
            last_name="Santos",
            date_of_birth="1991-02-02",
            sex="F",
            contact_number="09179876543",
        )

        cls.case_recent = XrayRecord.objects.create(
            patient=cls.patient_one,
            uploader=cls.technologist,
            raw_image=cls._image_file("recent.png"),
            status="COMPLETED",
            file_format="png",
        )
        cls.case_older = XrayRecord.objects.create(
            patient=cls.patient_two,
            uploader=cls.technologist,
            raw_image=cls._image_file("older.png"),
            status="COMPLETED",
            file_format="png",
        )
        cls.case_draft = XrayRecord.objects.create(
            patient=cls.patient_one,
            uploader=cls.technologist,
            raw_image=cls._image_file("draft.png"),
            status="IN_REVIEW",
            file_format="png",
        )

        AIResult.objects.create(
            xray_record=cls.case_recent,
            risk_score=0.71,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=cls.case_older,
            risk_score=0.43,
            risk_label=AIResult.RiskLabel.MODERATE,
            model_version="v-test",
        )

        cls.report_recent = Report.objects.create(
            xray_record=cls.case_recent,
            findings="Upper lobe opacity.",
            impression="Likely pulmonary TB.",
            recommendation="Immediate physician review.",
            severity=Report.SeverityChoices.CRITICAL,
            status="SUBMITTED",
            created_by=cls.radiologist,
        )
        cls.report_older = Report.objects.create(
            xray_record=cls.case_older,
            findings="Mild infiltrates.",
            impression="Needs correlation.",
            recommendation="Follow-up radiography.",
            severity=Report.SeverityChoices.MODERATE,
            status="SUBMITTED",
            created_by=cls.radiologist,
        )
        Report.objects.create(
            xray_record=cls.case_draft,
            findings="Draft findings.",
            impression="Draft impression.",
            recommendation="Draft recommendation.",
            severity=Report.SeverityChoices.SEVERE,
            status="DRAFT",
            created_by=cls.radiologist,
        )

        now = timezone.now()
        Report.objects.filter(pk=cls.report_recent.pk).update(updated_at=now - timedelta(days=1))
        Report.objects.filter(pk=cls.report_older.pk).update(updated_at=now - timedelta(days=10))

        Notification.objects.create(
            recipient=cls.physician,
            message="Report ready for Juan Dela Cruz.",
            read_status=False,
        )
        Notification.objects.create(
            recipient=cls.physician,
            message="Already read alert.",
            read_status=True,
        )
        Notification.objects.create(
            recipient=cls.other_physician,
            message="Other physician alert.",
            read_status=False,
        )

    def test_physician_dashboard_returns_summary_blocks(self):
        self.client.force_login(self.physician)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertIn("filters", payload)
        self.assertIn("summary", payload)
        self.assertIn("finalized_cases", payload)
        self.assertIn("recent_reports", payload)
        self.assertIn("report_ready_items", payload)
        self.assertIn("pending_alerts", payload)
        self.assertIn("patient_progress", payload)

        self.assertEqual(payload["summary"]["finalized_report_count"], 2)
        self.assertEqual(payload["summary"]["pending_alert_count"], 1)
        self.assertEqual(len(payload["pending_alerts"]), 1)
        self.assertEqual(payload["pending_alerts"][0]["message"], "Report ready for Juan Dela Cruz.")

        # Only SUBMITTED reports should appear in physician report sections.
        self.assertEqual(len(payload["finalized_cases"]), 2)
        severities = {item["severity"] for item in payload["finalized_cases"]}
        self.assertSetEqual(severities, {"CRITICAL", "MODERATE"})

        first_case = payload["finalized_cases"][0]
        self.assertIn("transaction_id", first_case)
        self.assertIn("patient", first_case)
        self.assertIn("radiologist", first_case)
        self.assertIn("ai_result", first_case)

    def test_physician_dashboard_filters_by_date_and_severity(self):
        self.client.force_login(self.physician)

        start = (timezone.now() - timedelta(days=2)).date().isoformat()
        end = timezone.now().date().isoformat()
        response = self.client.get(
            self.endpoint,
            {
                "severity": "CRITICAL",
                "date_from": start,
                "date_to": end,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["summary"]["finalized_report_count"], 1)
        self.assertEqual(len(payload["finalized_cases"]), 1)
        self.assertEqual(payload["finalized_cases"][0]["severity"], "CRITICAL")
        self.assertEqual(payload["filters"]["severity"], "CRITICAL")
        self.assertEqual(payload["filters"]["date_from"], start)
        self.assertEqual(payload["filters"]["date_to"], end)

    def test_non_physicians_cannot_access_physician_dashboard(self):
        for user in (self.radiologist, self.technologist):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(self.endpoint)
                self.assertEqual(response.status_code, 403)

    def test_invalid_filters_return_400(self):
        self.client.force_login(self.physician)

        invalid_severity = self.client.get(self.endpoint, {"severity": "EXTREME"})
        self.assertEqual(invalid_severity.status_code, 400)

        invalid_date = self.client.get(self.endpoint, {"date_from": "2026/01/01"})
        self.assertEqual(invalid_date.status_code, 400)

        invalid_range = self.client.get(
            self.endpoint,
            {"date_from": "2026-09-10", "date_to": "2026-09-01"},
        )
        self.assertEqual(invalid_range.status_code, 400)


class PhysicianDashboardEmptyStateTests(TestCase):
    endpoint = "/api/physician/dashboard"

    def test_empty_state_returns_consistent_schema(self):
        physician = get_user_model().objects.create_user(
            username="physician-empty",
            password="password123",
            role=UserRole.PHYSICIAN,
        )
        self.client.force_login(physician)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["finalized_report_count"], 0)
        self.assertEqual(payload["summary"]["pending_alert_count"], 0)
        self.assertEqual(payload["finalized_cases"], [])
        self.assertEqual(payload["recent_reports"], [])
        self.assertEqual(payload["report_ready_items"], [])
        self.assertEqual(payload["pending_alerts"], [])
        self.assertEqual(payload["patient_progress"], [])

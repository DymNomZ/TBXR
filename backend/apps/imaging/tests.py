import json
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import AIResult, Annotation, ProcessedImage, XrayRecord, Report


class ImagingAccessTests(TestCase):
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
        cls.tech_one = user_model.objects.create_user(
            username="tech-one",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.tech_two = user_model.objects.create_user(
            username="tech-two",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        cls.rad = user_model.objects.create_user(
            username="rad-one",
            password="password123",
            role=UserRole.RADIOLOGIST,
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

        cls.tech_one_record = cls._create_xray_record(
            patient=cls.patient_one,
            uploader=cls.tech_one,
            filename="tech-one.png",
        )
        cls.tech_two_record = cls._create_xray_record(
            patient=cls.patient_two,
            uploader=cls.tech_two,
            filename="tech-two.png",
        )

    @staticmethod
    def _image_file(filename="xray.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def _create_xray_record(cls, patient, uploader, filename):
        return XrayRecord.objects.create(
            patient=patient,
            uploader=uploader,
            raw_image=cls._image_file(filename),
            status="PENDING",
            file_format="png",
        )

    @staticmethod
    def _annotation_payload():
        return {
            "bounding_boxes": [
                {"x": 10, "y": 20, "width": 30, "height": 40, "label": "nodule"}
            ],
            "notes": "Review needed",
        }

    @staticmethod
    def _dicom_file(filename="xray.dcm"):
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.1'
        file_meta.MediaStorageSOPInstanceUID = "1.2.3"
        file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

        ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

        ds.PatientName = "Secret^Identity"
        ds.PatientID = "000000"
        ds.PatientSex = "M"
        ds.PatientAge = "030Y"
        ds.InstitutionName = "Test Hospital"
        ds.ReferringPhysicianName = "Dr. Classified"
        ds.StudyDate = "20230101"
        ds.AccessionNumber = "ACC123"

        ds.Rows = 2
        ds.Columns = 2
        ds.SamplesPerPixel = 1
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelData = b"\x00\xff\x00\xff"

        ds.is_little_endian = True
        ds.is_implicit_VR = True

        buffer = BytesIO()
        ds.save_as(buffer)
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="application/dicom")

    def test_upload_dicom_strips_pii(self):
        fake_inference = SimpleNamespace(
            MODEL_VERSION="v-test",
            predict=mock.Mock(return_value={"risk_score": 0.41, "risk_label": "Low Risk"}),
            generate_heatmap=mock.Mock(return_value=""),
        )

        self.client.force_login(self.tech_one)

        with mock.patch("apps.imaging.views._get_inference_module", return_value=fake_inference):
            response = self.client.post(
                reverse(
                    "imaging:upload_xray",
                    kwargs={"patient_id": self.patient_one.patient_id},
                ),
                data={"raw_image": self._dicom_file("test.dcm")},
            )

        self.assertEqual(response.status_code, 200)

        payload = response.json()
        xray_record = XrayRecord.objects.get(transaction_id=payload["transaction_id"])

        xray_record.raw_image.seek(0)
        saved_ds = pydicom.dcmread(xray_record.raw_image)

        tags_to_strip = [
            "PatientName", "PatientID", "PatientBirthDate",
            "PatientSex", "PatientAge", "InstitutionName",
            "ReferringPhysicianName", "StudyDate", "AccessionNumber"
        ]

        for tag in tags_to_strip:
            self.assertFalse(hasattr(saved_ds, tag), f"Tag {tag} was not stripped!")

        xray_record.raw_image.close()

    def test_technologist_dashboard_shows_only_own_records(self):
        self.client.force_login(self.tech_one)

        response = self.client.get(reverse("imaging:technologist_dashboard"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(
            [result["transaction_id"] for result in payload["results"]],
            [str(self.tech_one_record.transaction_id)],
        )

    def test_radiologist_queue_shows_all_records(self):
        self.client.force_login(self.rad)

        response = self.client.get(reverse("imaging:radiologist-queue"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertCountEqual(
            [result["transaction_id"] for result in payload["results"]],
            [str(self.tech_one_record.transaction_id), str(self.tech_two_record.transaction_id)],
        )

    def test_report_template_includes_clinical_disclaimer(self):
        html = render_to_string(
            "reports/xray_report.html",
            {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "upload_date": "2026-08-19 14:30",
                "generated_at": "2026-08-19 15:00",
                "patient_name": "Juan Dela Cruz",
                "patient_age": "35",
                "patient_sex": "M",
                "facility_name": "Cebu General Hospital",
                "ai_risk_score": "0.82",
                "ai_risk_label": "HIGH",
                "heatmap_base64": "",
                "radiologist_annotations": ["Left upper lobe opacity"],
                "diagnostic_notes": "No diagnostic notes provided.",
                "clinical_impression": "Suspicious for tuberculosis.",
                "recommendations": "Follow-up imaging and specialist review.",
                "ai_summary": "AI model flagged as HIGH risk.",
            },
        )

        self.assertIn(
            "AI-generated assessments are assistive only and are not a definitive diagnosis.",
            html,
        )
        self.assertIn(
            "Final clinical decisions remain with licensed medical professionals.",
            html,
        )

    def test_radiologist_queue_filters_by_severity_levels(self):
        self.client.force_login(self.rad)

        low_record = self._create_xray_record(
            patient=self.patient_one,
            uploader=self.tech_one,
            filename="low-risk.png",
        )
        moderate_record = self._create_xray_record(
            patient=self.patient_two,
            uploader=self.tech_two,
            filename="moderate-risk.png",
        )
        AIResult.objects.create(
            xray_record=low_record,
            risk_score=0.20,
            risk_label=AIResult.RiskLabel.LOW,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=moderate_record,
            risk_score=0.55,
            risk_label=AIResult.RiskLabel.MODERATE,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=self.tech_two_record,
            risk_score=0.85,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="v-test",
        )

        for filter_value, expected in [
            ("LOW", [str(low_record.transaction_id)]),
            ("MODERATE", [str(moderate_record.transaction_id)]),
            ("HIGH", [str(self.tech_two_record.transaction_id)]),
        ]:
            with self.subTest(filter_value=filter_value):
                response = self.client.get(
                    reverse("imaging:radiologist-queue"),
                    {"risk_label": filter_value},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["count"], len(expected))
                self.assertEqual(
                    [result["transaction_id"] for result in payload["results"]],
                    expected,
                )

    def test_xray_detail_is_accessible_to_all_roles(self):
        detail_url = reverse(
            "imaging:xray-detail",
            kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
        )

        for user in (self.tech_one, self.rad):
            self.client.force_login(user)
            response = self.client.get(detail_url)
            self.assertEqual(response.status_code, 200)

    def test_xray_detail_sets_in_review_when_radiologist_opens_case(self):
        self.tech_one_record.status = "PENDING"
        self.tech_one_record.save(update_fields=["status"])

        self.client.force_login(self.rad)
        detail_url = reverse(
            "imaging:xray-detail",
            kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
        )

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        self.tech_one_record.refresh_from_db()
        self.assertEqual(self.tech_one_record.status, "IN_REVIEW")

    def test_radiologist_annotation_submission_creates_annotation_and_completes_record(self):
        self.client.force_login(self.rad)

        response = self.client.post(
            reverse(
                "imaging:annotate_xray",
                kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
            ),
            data=json.dumps(self._annotation_payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Annotation.objects.filter(
                xray_record=self.tech_one_record,
                radiologist=self.rad,
            ).count(),
            1,
        )

        self.tech_one_record.refresh_from_db()
        self.assertEqual(self.tech_one_record.status, "COMPLETED")
        self.assertEqual(response.json()["status"], "COMPLETED")

    def test_non_radiologists_cannot_submit_annotations(self):
        annotate_url = reverse(
            "imaging:annotate_xray",
            kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
        )

        for user in (self.tech_one,):
            self.client.force_login(user)
            response = self.client.post(
                annotate_url,
                data=json.dumps(self._annotation_payload()),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 403)

        self.assertEqual(
            Annotation.objects.filter(xray_record=self.tech_one_record).count(),
            0,
        )

    def test_ai_inference_endpoint_creates_ai_result_with_valid_values(self):
        ProcessedImage.objects.create(
            xray_record=self.tech_one_record,
            processed_image=self._image_file("processed.png"),
            preprocessing_metadata={"source": "test"},
        )

        fake_inference = SimpleNamespace(
            MODEL_VERSION="v-test",
            predict=mock.Mock(return_value={"risk_score": 0.73, "risk_label": "High Risk"}),
            generate_heatmap=mock.Mock(return_value=""),
        )

        self.client.force_login(self.tech_one)
        with mock.patch("apps.imaging.views._get_inference_module", return_value=fake_inference):
            response = self.client.post(
                reverse(
                    "imaging:analyse_xray",
                    kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
                ),
            )

        self.assertIn(response.status_code, (200, 201))
        self.assertEqual(AIResult.objects.filter(xray_record=self.tech_one_record).count(), 1)

        ai_result = AIResult.objects.get(xray_record=self.tech_one_record)
        self.assertGreaterEqual(ai_result.risk_score, 0.0)
        self.assertLessEqual(ai_result.risk_score, 1.0)
        self.assertIn(ai_result.risk_label, AIResult.RiskLabel.values)
        self.assertEqual(ai_result.model_version, "v-test")

    def test_ai_inference_endpoint_rejects_out_of_range_risk_score(self):
        ProcessedImage.objects.create(
            xray_record=self.tech_one_record,
            processed_image=self._image_file("processed-out-of-range.png"),
            preprocessing_metadata={"source": "test"},
        )

        fake_inference = SimpleNamespace(
            MODEL_VERSION="v-test",
            predict=mock.Mock(return_value={"risk_score": 1.25, "risk_label": "High Risk"}),
            generate_heatmap=mock.Mock(return_value=""),
        )

        self.client.force_login(self.tech_one)
        with mock.patch("apps.imaging.views._get_inference_module", return_value=fake_inference):
            response = self.client.post(
                reverse(
                    "imaging:analyse_xray",
                    kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
                ),
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "MANUAL_REVIEW")
        self.assertIn("errors", response.data)
        self.assertIn("inference", response.data["errors"])
        self.assertIn("Risk score must be between 0.0 and 1.0", response.data["errors"]["inference"][0])
        self.assertFalse(AIResult.objects.filter(xray_record=self.tech_one_record).exists())

        self.tech_one_record.refresh_from_db()
        self.assertEqual(self.tech_one_record.status, "MANUAL_REVIEW")

    def test_upload_triggers_ai_analysis_automatically(self):
        fake_inference = SimpleNamespace(
            MODEL_VERSION="v-test",
            predict=mock.Mock(return_value={"risk_score": 0.41, "risk_label": "Low Risk"}),
            generate_heatmap=mock.Mock(return_value=""),
        )

        self.client.force_login(self.tech_one)
        with mock.patch("apps.imaging.views._get_inference_module", return_value=fake_inference):
            response = self.client.post(
                reverse(
                    "imaging:upload_xray",
                    kwargs={"patient_id": self.patient_one.patient_id},
                ),
                data={"raw_image": self._image_file("auto-upload.png")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        xray_record = XrayRecord.objects.get(transaction_id=payload["transaction_id"])
        self.assertEqual(AIResult.objects.filter(xray_record=xray_record).count(), 1)
        self.assertEqual(xray_record.status, "AI_REVIEWED")
        self.assertEqual(AIResult.objects.count(), 1)

    def test_patient_history_returns_records_in_chronological_order(self):
        patient = Patient.objects.create(
            first_name="Chrono",
            last_name="Patient",
            date_of_birth="1992-03-03",
            sex="M",
            contact_number="09170000000",
        )
        first = self._create_xray_record(patient=patient, uploader=self.tech_one, filename="first.png")
        second = self._create_xray_record(patient=patient, uploader=self.tech_one, filename="second.png")
        third = self._create_xray_record(patient=patient, uploader=self.tech_one, filename="third.png")

        base_time = timezone.now() - timedelta(minutes=3)
        for offset, record in enumerate((first, second, third)):
            XrayRecord.objects.filter(pk=record.pk).update(
                upload_timestamp=base_time + timedelta(minutes=offset),
            )

        self.client.force_login(self.rad)
        response = self.client.get(
            reverse("imaging:patient_history", kwargs={"patient_id": patient.patient_id})
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 3)
        self.assertEqual(
            [item["transaction_id"] for item in payload],
            [str(first.transaction_id), str(second.transaction_id), str(third.transaction_id)],
        )


class AnalyticsSummaryTests(TestCase):
    endpoint = "/api/analytics/summary/"

    @classmethod
    def _image_file(cls, filename="xray.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.radiologist = user_model.objects.create_user(
            username="rad-analytics",
            password="password123",
            role=UserRole.RADIOLOGIST,
        )
        cls.physician = user_model.objects.create_user(
            username="phys-analytics",
            password="password123",
            role=UserRole.PHYSICIAN,
        )
        cls.technologist = user_model.objects.create_user(
            username="tech-analytics",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
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
        cls.patient_three = Patient.objects.create(
            first_name="Pedro",
            last_name="Garcia",
            date_of_birth="1985-03-03",
            sex="M",
            contact_number="09175555555",
        )

        base_time = timezone.now() - timedelta(days=30)

        # Create X-ray records with different statuses and dates
        cls.case_1 = XrayRecord.objects.create(
            patient=cls.patient_one,
            uploader=cls.technologist,
            raw_image=cls._image_file("case1.png"),
            status="PENDING",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_1.pk).update(upload_timestamp=base_time + timedelta(days=1))

        cls.case_2 = XrayRecord.objects.create(
            patient=cls.patient_one,
            uploader=cls.technologist,
            raw_image=cls._image_file("case2.png"),
            status="AI_REVIEWED",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_2.pk).update(upload_timestamp=base_time + timedelta(days=5))

        cls.case_3 = XrayRecord.objects.create(
            patient=cls.patient_two,
            uploader=cls.technologist,
            raw_image=cls._image_file("case3.png"),
            status="IN_REVIEW",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_3.pk).update(upload_timestamp=base_time + timedelta(days=10))

        cls.case_4 = XrayRecord.objects.create(
            patient=cls.patient_two,
            uploader=cls.technologist,
            raw_image=cls._image_file("case4.png"),
            status="COMPLETED",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_4.pk).update(upload_timestamp=base_time + timedelta(days=15))

        cls.case_5 = XrayRecord.objects.create(
            patient=cls.patient_three,
            uploader=cls.technologist,
            raw_image=cls._image_file("case5.png"),
            status="COMPLETED",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_5.pk).update(upload_timestamp=base_time + timedelta(days=20))

        cls.case_6 = XrayRecord.objects.create(
            patient=cls.patient_three,
            uploader=cls.technologist,
            raw_image=cls._image_file("case6.png"),
            status="MANUAL_REVIEW",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_6.pk).update(upload_timestamp=base_time + timedelta(days=25))

        # AI results for some cases
        AIResult.objects.create(
            xray_record=cls.case_1,
            risk_score=0.15,
            risk_label=AIResult.RiskLabel.LOW,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=cls.case_2,
            risk_score=0.65,
            risk_label=AIResult.RiskLabel.MODERATE,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=cls.case_3,
            risk_score=0.85,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="v-test",
        )
        AIResult.objects.create(
            xray_record=cls.case_4,
            risk_score=0.72,
            risk_label=AIResult.RiskLabel.HIGH,
            model_version="v-test",
        )
        # case_5 and case_6 have no AI results

        # Reports for completed cases with different severities
        cls.report_1 = Report.objects.create(
            xray_record=cls.case_4,
            findings="Findings 1",
            impression="Impression 1",
            recommendation="Recommendation 1",
            severity=Report.SeverityChoices.CRITICAL,
            status="SUBMITTED",
            created_by=cls.radiologist,
        )
        Report.objects.filter(pk=cls.report_1.pk).update(
            created_at=base_time + timedelta(days=16),
            updated_at=base_time + timedelta(days=16)
        )

        cls.report_2 = Report.objects.create(
            xray_record=cls.case_5,
            findings="Findings 2",
            impression="Impression 2",
            recommendation="Recommendation 2",
            severity=Report.SeverityChoices.MODERATE,
            status="SUBMITTED",
            created_by=cls.radiologist,
        )
        Report.objects.filter(pk=cls.report_2.pk).update(
            created_at=base_time + timedelta(days=21),
            updated_at=base_time + timedelta(days=21)
        )

        # Create a new case for the third report (DRAFT)
        cls.case_7 = XrayRecord.objects.create(
            patient=cls.patient_three,
            uploader=cls.technologist,
            raw_image=cls._image_file("case7.png"),
            status="COMPLETED",
            file_format="png",
        )
        XrayRecord.objects.filter(pk=cls.case_7.pk).update(upload_timestamp=base_time + timedelta(days=22))

        cls.report_3 = Report.objects.create(
            xray_record=cls.case_7,
            findings="Findings 3",
            impression="Impression 3",
            recommendation="Recommendation 3",
            severity=Report.SeverityChoices.NORMAL,
            status="DRAFT",
            created_by=cls.radiologist,
        )
        Report.objects.filter(pk=cls.report_3.pk).update(
            created_at=base_time + timedelta(days=22),
            updated_at=base_time + timedelta(days=22)
        )

    def test_analytics_summary_requires_auth(self):
        response = self.client.get(self.endpoint)
        # Django's @login_required redirects to login page (302) rather than returning 401
        self.assertIn(response.status_code, [302, 401])

    def test_analytics_summary_requires_radiologist_or_physician(self):
        self.client.force_login(self.technologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_analytics_summary_radiologist_access(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_analytics_summary_physician_access(self):
        self.client.force_login(self.physician)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_analytics_summary_response_structure(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("filters", payload)
        self.assertIn("cases", payload)
        self.assertIn("reports", payload)

        # Check filters structure
        self.assertIn("date_from", payload["filters"])
        self.assertIn("date_to", payload["filters"])
        self.assertIn("severity", payload["filters"])

        # Check cases structure
        self.assertIn("total", payload["cases"])
        self.assertIn("by_status", payload["cases"])
        self.assertIn("by_ai_risk_label", payload["cases"])

        # Check reports structure
        self.assertIn("total", payload["reports"])
        self.assertIn("by_severity", payload["reports"])
        self.assertIn("by_status", payload["reports"])

    def test_analytics_summary_total_counts_match_raw_data(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()

        # Total cases should match XrayRecord count (7)
        self.assertEqual(payload["cases"]["total"], 7)

        # Total reports should match Report count (3)
        self.assertEqual(payload["reports"]["total"], 3)

    def test_analytics_summary_status_breakdown(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        by_status = payload["cases"]["by_status"]

        # Verify each status count
        self.assertEqual(by_status.get("PENDING", 0), 1)
        self.assertEqual(by_status.get("AI_REVIEWED", 0), 1)
        self.assertEqual(by_status.get("IN_REVIEW", 0), 1)
        self.assertEqual(by_status.get("COMPLETED", 0), 3)
        self.assertEqual(by_status.get("MANUAL_REVIEW", 0), 1)

        # Sum should equal total
        self.assertEqual(sum(by_status.values()), payload["cases"]["total"])

    def test_analytics_summary_ai_risk_label_breakdown(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        by_risk = payload["cases"]["by_ai_risk_label"]

        self.assertEqual(by_risk.get("LOW", 0), 1)
        self.assertEqual(by_risk.get("MODERATE", 0), 1)
        self.assertEqual(by_risk.get("HIGH", 0), 2)

        # Sum should equal AI results count (4, since 2 cases have no AI result)
        self.assertEqual(sum(by_risk.values()), 4)

    def test_analytics_summary_report_severity_breakdown(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        by_severity = payload["reports"]["by_severity"]

        self.assertEqual(by_severity.get("CRITICAL", 0), 1)
        self.assertEqual(by_severity.get("MODERATE", 0), 1)
        self.assertEqual(by_severity.get("NORMAL", 0), 1)

        # Sum should equal total reports
        self.assertEqual(sum(by_severity.values()), payload["reports"]["total"])

    def test_analytics_summary_report_status_breakdown(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        by_status = payload["reports"]["by_status"]

        self.assertEqual(by_status.get("SUBMITTED", 0), 2)
        self.assertEqual(by_status.get("DRAFT", 0), 1)

        # Sum should equal total reports
        self.assertEqual(sum(by_status.values()), payload["reports"]["total"])

    def test_analytics_summary_date_from_filter(self):
        self.client.force_login(self.radiologist)
        # Filter to last 20 days (should include cases 3, 4, 5, 6, 7 - days 10, 15, 20, 25, 22)
        date_from = (timezone.now() - timedelta(days=20)).date().isoformat()
        response = self.client.get(self.endpoint, {"date_from": date_from})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        # Cases 3, 4, 5, 6, 7 fall in this range
        self.assertEqual(payload["cases"]["total"], 5)

        # Reports 1, 2, 3 fall in this range (created at days 16, 21, 22)
        self.assertEqual(payload["reports"]["total"], 3)

    def test_analytics_summary_date_to_filter(self):
        self.client.force_login(self.radiologist)
        # Filter to first 10 days (should include cases 1, 2, 3)
        date_to = (timezone.now() - timedelta(days=20)).date().isoformat()
        response = self.client.get(self.endpoint, {"date_to": date_to})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        # Cases 1, 2, 3 fall in this range
        self.assertEqual(payload["cases"]["total"], 3)

        # No reports fall in this range (earliest report at day 16)
        self.assertEqual(payload["reports"]["total"], 0)

    def test_analytics_summary_date_range_filter(self):
        self.client.force_login(self.radiologist)
        base_time = timezone.now() - timedelta(days=30)
        date_from = (base_time + timedelta(days=5)).date().isoformat()
        date_to = (base_time + timedelta(days=20)).date().isoformat()
        response = self.client.get(self.endpoint, {"date_from": date_from, "date_to": date_to})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        # Cases 2, 3, 4, 5 fall in this range (days 5, 10, 15, 20)
        self.assertEqual(payload["cases"]["total"], 4)

        # Reports 1, 2 fall in this range (days 16, 21 - wait, day 21 is outside)
        # Actually report 1 at day 16, report 2 at day 21 (outside), report 3 at day 22 (outside)
        self.assertEqual(payload["reports"]["total"], 1)

    def test_analytics_summary_invalid_date_range(self):
        self.client.force_login(self.radiologist)
        date_from = "2026-09-10"
        date_to = "2026-09-01"
        response = self.client.get(self.endpoint, {"date_from": date_from, "date_to": date_to})
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_analytics_summary_invalid_date_format(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint, {"date_from": "2026/01/01"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_analytics_summary_severity_filter(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint, {"severity": "CRITICAL"})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["reports"]["total"], 1)
        self.assertEqual(payload["reports"]["by_severity"].get("CRITICAL", 0), 1)
        self.assertEqual(payload["filters"]["severity"], "CRITICAL")

    def test_analytics_summary_invalid_severity(self):
        self.client.force_login(self.radiologist)
        response = self.client.get(self.endpoint, {"severity": "EXTREME"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_analytics_summary_combined_filters(self):
        self.client.force_login(self.radiologist)
        base_time = timezone.now() - timedelta(days=30)
        date_from = (base_time + timedelta(days=10)).date().isoformat()
        date_to = (base_time + timedelta(days=25)).date().isoformat()
        response = self.client.get(
            self.endpoint,
            {"date_from": date_from, "date_to": date_to, "severity": "MODERATE"},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        # Only report_2 (MODERATE, day 21) should match
        self.assertEqual(payload["reports"]["total"], 1)
        self.assertEqual(payload["reports"]["by_severity"].get("MODERATE", 0), 1)

    def test_analytics_summary_empty_result_set(self):
        self.client.force_login(self.radiologist)
        # Future date range with no data
        future_date = (timezone.now() + timedelta(days=30)).date().isoformat()
        response = self.client.get(self.endpoint, {"date_from": future_date})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["cases"]["total"], 0)
        self.assertEqual(payload["reports"]["total"], 0)
        self.assertEqual(payload["cases"]["by_status"], {})
        self.assertEqual(payload["cases"]["by_ai_risk_label"], {})
        self.assertEqual(payload["reports"]["by_severity"], {})
        self.assertEqual(payload["reports"]["by_status"], {})

    def test_analytics_summary_filters_echoed_in_response(self):
        self.client.force_login(self.radiologist)
        # Use fixed dates that are valid and will work with test data
        # Test data spans from ~30 days ago to ~5 days ago
        date_from = "2024-01-01"
        date_to = "2030-12-31"
        severity = "CRITICAL"  # Valid report severity
        response = self.client.get(
            self.endpoint, {"date_from": date_from, "date_to": date_to, "severity": severity}
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["filters"]["date_from"], date_from)
        self.assertEqual(payload["filters"]["date_to"], date_to)
        self.assertEqual(payload["filters"]["severity"], severity)

    def test_analytics_export_csv(self):
        self.client.force_login(self.radiologist)
        response = self.client.post("/api/analytics/export/", {"format": "csv", "filters": {"severity": "CRITICAL"}}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="analytics_export.csv"', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn("Category,Metric,Value", content)
        self.assertIn("Reports,Total Reports,1", content)
        self.assertIn("Reports,Severity: CRITICAL,1", content)

    def test_analytics_export_pdf(self):
        self.client.force_login(self.radiologist)
        response = self.client.post("/api/analytics/export/", {"format": "pdf", "filters": {"severity": "MODERATE"}}, content_type="application/json")
        if response.status_code != 200:
            print("PDF generation error:", response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="analytics_export.pdf"', response['Content-Disposition'])
        content = b''.join(response.streaming_content)
        self.assertTrue(content.startswith(b'%PDF'))
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

from .models import AIResult, Annotation, ProcessedImage, XrayRecord


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

		self.assertEqual(response.status_code, 500)
		self.assertJSONEqual(
			response.content,
			{"errors": {"risk_score": ["Risk score must be between 0.0 and 1.0."]}},
		)
		self.assertFalse(AIResult.objects.filter(xray_record=self.tech_one_record).exists())

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
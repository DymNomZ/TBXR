import json
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import Annotation, XrayRecord


class ImagingAccessTests(TestCase):
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
		cls.phys = user_model.objects.create_user(
			username="phys-one",
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

	def test_xray_detail_is_accessible_to_all_roles(self):
		detail_url = reverse(
			"imaging:xray-detail",
			kwargs={"transaction_id": str(self.tech_one_record.transaction_id)},
		)

		for user in (self.tech_one, self.rad, self.phys):
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

		for user in (self.tech_one, self.phys):
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

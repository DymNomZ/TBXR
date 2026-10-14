"""T06 regression suite — Interactive Annotation and Submission.

Executable encoding of the manual regression plan batch T06
(F-2.3.1 - F-2.5.2). Test method names carry the plan case IDs so a run can
be mapped 1:1 back to the plan.

Scope note: the plan is written for manual execution in Chrome. Every case
observable through the HTTP contract is asserted here at the API level via
Django's test client. The canvas-only interactions (drawing preview, undo
stack, zoom/pan) are validated separately against the frontend components in
``frontend/src/components/imaging/AnnotationCanvas.test.jsx`` and
``frontend/src/pages/AnnotationReviewPage.test.jsx``.
"""

from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .models import Annotation, XrayRecord

ANNOTATE_URL_NAME = "imaging:annotate_xray"
DETAIL_URL_NAME = "imaging:xray-detail"


class _T06Base(TestCase):
    """Shared fixtures: media temp dir, a radiologist, tech and physician."""

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
        cls.radiologist = user.objects.create_user(
            username="t06-rad", password="password123", role=UserRole.RADIOLOGIST
        )
        cls.tech = user.objects.create_user(
            username="t06-tech", password="password123", role=UserRole.RADIOLOGIC_TECH
        )
        cls.physician = user.objects.create_user(
            username="t06-physician", password="password123", role=UserRole.PHYSICIAN
        )
        cls.patient = Patient.objects.create(
            first_name="T06",
            last_name="Patient",
            date_of_birth="1975-05-05",
            sex="F",
            contact_number="09170000006",
        )

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _image_file(filename="t06.png"):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        buffer.seek(0)
        return SimpleUploadedFile(filename, buffer.getvalue(), content_type="image/png")

    @classmethod
    def _make_record(cls, filename="t06.png", status="PENDING"):
        return XrayRecord.objects.create(
            patient=cls.patient,
            uploader=cls.tech,
            raw_image=cls._image_file(filename),
            status=status,
            file_format="png",
        )

    @classmethod
    def _annotate_url(cls, record):
        return reverse(
            ANNOTATE_URL_NAME, kwargs={"transaction_id": str(record.transaction_id)}
        )

    @classmethod
    def _detail_url(cls, record):
        return reverse(
            DETAIL_URL_NAME, kwargs={"transaction_id": str(record.transaction_id)}
        )

    @staticmethod
    def _three_shape_payload():
        """One rectangle, one circle and one freehand ROI in normalized space."""
        return {
            "bounding_boxes": [
                {"x": 0.10, "y": 0.12, "width": 0.20, "height": 0.18, "label": "nodule", "shape": "rectangle"},
                {"x": 0.45, "y": 0.30, "width": 0.15, "height": 0.20, "label": "cavity", "shape": "circle"},
                {
                    "x": 0.60,
                    "y": 0.55,
                    "width": 0.22,
                    "height": 0.16,
                    "label": "opacity",
                    "shape": "freehand",
                    "points": [
                        {"x": 0.60, "y": 0.55},
                        {"x": 0.70, "y": 0.63},
                        {"x": 0.82, "y": 0.58},
                        {"x": 0.76, "y": 0.71},
                    ],
                },
            ],
            "notes": "Left upper lobe opacity with surrounding consolidation.",
        }


class AnnotationSubmissionTests(_T06Base):
    """F-2.3.1 / F-2.3.2 / F-2.5.1 — draw, persist and submit ROIs."""

    def test_F231_F232_F251_submits_three_shapes_with_labels_and_notes(self):
        record = self._make_record(status="PENDING", filename="t06-three.png")
        self.client.force_login(self.radiologist)

        response = self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "COMPLETED")

        record.refresh_from_db()
        self.assertEqual(record.status, "COMPLETED")

        annotation = Annotation.objects.get(xray_record=record, radiologist=self.radiologist)
        boxes = annotation.bounding_boxes
        self.assertEqual(len(boxes), 3)

        by_label = {box["label"]: box for box in boxes}
        self.assertEqual(set(by_label), {"nodule", "cavity", "opacity"})
        self.assertEqual(by_label["nodule"]["shape"], "rectangle")
        self.assertEqual(by_label["cavity"]["shape"], "circle")
        self.assertEqual(by_label["opacity"]["shape"], "freehand")
        self.assertEqual(len(by_label["opacity"]["points"]), 4)

        # F-2.3.2 — coordinates are stored normalized (0..1), not pixel space.
        for box in boxes:
            for field in ("x", "y", "width", "height"):
                self.assertGreaterEqual(box[field], 0.0)
                self.assertLessEqual(box[field], 1.0)
            self.assertIn("label", box)

        # F-2.3.2 — clinical note is attached to the annotation record.
        self.assertEqual(
            annotation.notes,
            "Left upper lobe opacity with surrounding consolidation.",
        )

    def test_F232_annotation_is_readable_back_through_detail_endpoint(self):
        record = self._make_record(status="PENDING", filename="t06-readback.png")
        self.client.force_login(self.radiologist)
        self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )

        detail = self.client.get(self._detail_url(record))
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["status"], "COMPLETED")
        self.assertEqual(len(body["annotations"]), 1)
        self.assertEqual(len(body["annotations"][0]["bounding_boxes"]), 3)
        self.assertEqual(
            body["annotations"][0]["notes"],
            "Left upper lobe opacity with surrounding consolidation.",
        )

    def test_F232_multiple_rois_all_persisted(self):
        record = self._make_record(status="PENDING", filename="t06-multi.png")
        self.client.force_login(self.radiologist)
        response = self.client.post(
            self._annotate_url(record),
            {
                "bounding_boxes": [
                    {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2, "label": f"roi-{i}"}
                    for i in range(5)
                ],
                "notes": "five regions",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        annotation = Annotation.objects.get(xray_record=record)
        self.assertEqual(len(annotation.bounding_boxes), 5)

    def test_F251_status_moves_to_completed_and_lock_released(self):
        record = self._make_record(status="AI_REVIEWED", filename="t06-complete.png")
        self.client.force_login(self.radiologist)
        # Open the case first, as the UI does, so the lock is acquired.
        self.client.get(self._detail_url(record))
        record.refresh_from_db()
        self.assertEqual(record.status, "IN_REVIEW")

        response = self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        record.refresh_from_db()
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNone(record.active_reviewer)
        self.assertIsNone(record.lock_timestamp)


class AnnotationValidationTests(_T06Base):
    """F-2.5.2 and input validation edges."""

    def test_F252_empty_canvas_is_rejected_with_400(self):
        record = self._make_record(status="PENDING", filename="t06-empty.png")
        self.client.force_login(self.radiologist)
        response = self.client.post(
            self._annotate_url(record),
            {"bounding_boxes": [], "notes": "No findings"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bounding_boxes", response.json().get("errors", {}))
        record.refresh_from_db()
        self.assertEqual(record.status, "PENDING", "record must not be completed")
        self.assertFalse(Annotation.objects.filter(xray_record=record).exists())

    def test_missing_bounding_boxes_is_rejected_with_400(self):
        record = self._make_record(status="PENDING", filename="t06-missing.png")
        self.client.force_login(self.radiologist)
        response = self.client.post(
            self._annotate_url(record),
            {"notes": "No findings"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_freehand_without_points_is_rejected_with_400(self):
        record = self._make_record(status="PENDING", filename="t06-fh.png")
        self.client.force_login(self.radiologist)
        response = self.client.post(
            self._annotate_url(record),
            {
                "bounding_boxes": [
                    {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2, "label": "x", "shape": "freehand"}
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_shape_is_rejected_with_400(self):
        record = self._make_record(status="PENDING", filename="t06-shape.png")
        self.client.force_login(self.radiologist)
        response = self.client.post(
            self._annotate_url(record),
            {
                "bounding_boxes": [
                    {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2, "label": "x", "shape": "triangle"}
                ]
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class AnnotationPermissionTests(_T06Base):
    """Negative / edge-case plan cases for role enforcement."""

    def test_negative_radiologic_tech_forbidden_403(self):
        record = self._make_record(status="PENDING", filename="t06-tech.png")
        self.client.force_login(self.tech)
        response = self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Annotation.objects.filter(xray_record=record).exists())

    def test_negative_physician_forbidden_403(self):
        record = self._make_record(status="PENDING", filename="t06-phys.png")
        self.client.force_login(self.physician)
        response = self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Annotation.objects.filter(xray_record=record).exists())

    def test_negative_unauthenticated_is_redirected(self):
        record = self._make_record(status="PENDING", filename="t06-anon.png")
        response = self.client.post(
            self._annotate_url(record),
            self._three_shape_payload(),
            content_type="application/json",
        )
        self.assertIn(response.status_code, (302, 403))
        self.assertFalse(Annotation.objects.filter(xray_record=record).exists())

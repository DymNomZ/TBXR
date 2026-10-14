import base64
import tempfile
import subprocess
import math
from django.conf import settings
from datetime import date
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.template.loader import render_to_string
from django.http import FileResponse

import json
import cv2
import numpy as np
import importlib.util
import sys
import pydicom
from io import BytesIO
from pathlib import Path
from collections import Counter

from PIL import Image
from django.core.files import File
from django.core.files.base import ContentFile
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.pagination import PageNumberPagination

from apps.accounts.decorators import role_required
from apps.accounts.enums import UserRole
from apps.patients.models import Patient

from .preprocessing import preprocess_xray
from .models import Annotation, XrayRecord, ProcessedImage, AIResult, ProgressionStatus, ProgressionOverrideAuditLog, Report, Notification
from django.db import models
from .serializers import (
    XrayRecordUploadSerializer,
    XrayRecordSerializer,
    TechDashboardRecordSerializer,
    RadiologistQueueSerializer,
    XrayRecordDetailSerializer,
    XrayRecordHistorySerializer,
    AIResultSerializer,
    PatientHistorySerializer,
    ProgressionStatusSerializer,
    ProgressionOverrideAuditLogSerializer,
    ReportSerializer,
    ReportCreateSerializer,
)
from .services import ProgressionService

_INFERENCE_MODULE = None


def _trigger_report_submission_notification(report):
    """Create a one-time notification for the assigned physician after successful final submission."""
    physician = get_user_model().objects.filter(role=UserRole.PHYSICIAN).order_by('id').first()
    if physician is None:
        return None

    patient = report.xray_record.patient
    patient_name = f"{patient.first_name} {patient.last_name}".strip()
    message = (
        f"Report ready for {patient_name} "
        f"(case {report.xray_record.transaction_id})."
    )

    if Notification.objects.filter(recipient=physician, message=message).exists():
        return None

    return Notification.objects.create(
        recipient=physician,
        message=message,
        read_status=False,
    )


def _trigger_manual_review_notification(xray_record, error_message):
    """Create notifications for all radiologists when AI processing fails and manual review is required."""
    radiologists = get_user_model().objects.filter(role=UserRole.RADIOLOGIST)
    if not radiologists.exists():
        return []

    patient = xray_record.patient
    patient_name = f"{patient.first_name} {patient.last_name}".strip()
    message = (
        f"Manual review required for {patient_name} "
        f"(case {xray_record.transaction_id}). AI processing failed: {error_message}"
    )

    notifications = []
    for radiologist in radiologists:
        if not Notification.objects.filter(recipient=radiologist, message=message).exists():
            notifications.append(Notification(
                recipient=radiologist,
                message=message,
                read_status=False,
            ))

    return Notification.objects.bulk_create(notifications)


def _get_inference_module():
    global _INFERENCE_MODULE
    if _INFERENCE_MODULE is not None:
        return _INFERENCE_MODULE

    inference_path = (
        Path(__file__).resolve().parents[3] / "ai" / "scripts" / "inference.py"
    )
    if not inference_path.exists():
        raise FileNotFoundError(f"Inference script not found: {inference_path}")

    spec = importlib.util.spec_from_file_location("tbxr_inference", inference_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load inference module.")

    module = importlib.util.module_from_spec(spec)
    inference_dir = str(inference_path.parent)
    if inference_dir not in sys.path:
        sys.path.insert(0, inference_dir)
    spec.loader.exec_module(module)
    _INFERENCE_MODULE = module
    return module


import time
import logging

logger = logging.getLogger(__name__)


class ProgressionHistoryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


def _serialize_physician_report(report):
    patient = report.xray_record.patient
    ai_result = getattr(report.xray_record, "ai_result", None)
    radiologist = report.created_by

    return {
        "report_id": report.id,
        "transaction_id": str(report.xray_record.transaction_id),
        "reported_at": report.updated_at.isoformat(),
        "severity": report.severity,
        "patient": {
            "patient_id": patient.patient_id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
        },
        "radiologist": {
            "id": radiologist.id if radiologist else None,
            "username": radiologist.username if radiologist else None,
            "first_name": radiologist.first_name if radiologist else None,
            "last_name": radiologist.last_name if radiologist else None,
        },
        "ai_result": {
            "risk_label": ai_result.risk_label if ai_result else None,
            "risk_score": ai_result.risk_score if ai_result else None,
        },
        "status": report.xray_record.status,
    }


def _serialize_physician_alert(alert):
    return {
        "id": alert.id,
        "message": alert.message,
        "read_status": alert.read_status,
        "created_at": alert.created_at.isoformat(),
        "updated_at": alert.updated_at.isoformat(),
    }


def _apply_physician_dashboard_filters(request, queryset):
    severity = request.query_params.get("severity", "").strip().upper()
    date_from_raw = request.query_params.get("date_from", "").strip()
    date_to_raw = request.query_params.get("date_to", "").strip()

    if severity:
        if severity not in Report.SeverityChoices.values:
            return None, Response(
                {
                    "detail": (
                        f"Invalid severity '{severity}'. Allowed values: "
                        f"{', '.join(Report.SeverityChoices.values)}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            ), None
        queryset = queryset.filter(severity=severity)

    date_from = None
    date_to = None

    if date_from_raw:
        date_from = parse_date(date_from_raw)
        if date_from is None:
            return None, Response(
                {"detail": "Invalid date_from format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            ), None
        queryset = queryset.filter(updated_at__date__gte=date_from)

    if date_to_raw:
        date_to = parse_date(date_to_raw)
        if date_to is None:
            return None, Response(
                {"detail": "Invalid date_to format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            ), None
        queryset = queryset.filter(updated_at__date__lte=date_to)

    if date_from and date_to and date_from > date_to:
        return None, Response(
            {"detail": "date_from cannot be later than date_to."},
            status=status.HTTP_400_BAD_REQUEST,
        ), None

    return queryset, None, {
        "severity": severity or None,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }


def _run_ai_inference(xray_record, processed_img, force_proceed=False):
    """
    Run AI inference on the processed image.
    Returns (ai_result, created, error_message) where error_message is None on success.
    """
    try:
        inference = _get_inference_module()
    except (FileNotFoundError, ImportError) as exc:
        error_msg = f"AI inference module unavailable: {exc}"
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    image_path = processed_img.processed_image.path

    try:
        prediction = inference.predict(image_path)
    except Exception as exc:
        error_msg = f"AI prediction failed: {exc}"
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    if isinstance(prediction, dict) and "error" in prediction:
        error_msg = f"AI prediction error: {prediction['error'].get('message', 'Unknown error')}"
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    quality_check = prediction.get("quality_check")
    if quality_check and quality_check.get("status") == "LOW_QUALITY":
        if not force_proceed:
            return None, False, None, quality_check
        else:
            # Persist the override
            metadata = processed_img.preprocessing_metadata
            metadata["low_quality_proceed"] = True
            metadata["low_quality_score"] = quality_check.get("score")
            processed_img.preprocessing_metadata = metadata
            processed_img.save(update_fields=["preprocessing_metadata"])

    try:
        heatmap_path = inference.generate_heatmap(image_path)
    except Exception as exc:
        error_msg = f"AI heatmap generation failed: {exc}"
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    try:
        risk_score = float(prediction.get("risk_score"))
    except (TypeError, ValueError) as exc:
        error_msg = "Invalid risk score from inference."
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    if not 0.0 <= risk_score <= 1.0:
        error_msg = "Risk score must be between 0.0 and 1.0."
        xray_record.status = "MANUAL_REVIEW"
        xray_record.save(update_fields=["status"])
        _trigger_manual_review_notification(xray_record, error_msg)
        return None, False, error_msg, None

    raw_label = str(prediction.get("risk_label", "")).strip().lower()
    if not raw_label:
        risk_label = (
            AIResult.RiskLabel.HIGH if risk_score >= 0.5 else AIResult.RiskLabel.LOW
        )
    elif "high" in raw_label:
        risk_label = AIResult.RiskLabel.HIGH
    elif "moderate" in raw_label:
        risk_label = AIResult.RiskLabel.MODERATE
    else:
        risk_label = AIResult.RiskLabel.LOW

    model_version = getattr(inference, "MODEL_VERSION", "unknown")

    ai_result, created = AIResult.objects.update_or_create(
        xray_record=xray_record,
        defaults={
            "risk_score": risk_score,
            "risk_label": risk_label,
            "model_version": model_version,
        },
    )

    if heatmap_path:
        heatmap_path_obj = Path(heatmap_path)
        if heatmap_path_obj.exists():
            with heatmap_path_obj.open("rb") as handle:
                ai_result.heatmap_image.save(
                    heatmap_path_obj.name,
                    File(handle),
                    save=False,
                )

    ai_result.save()

    xray_record.status = "AI_REVIEWED"
    xray_record.save(update_fields=["status"])

    return ai_result, created, None, None


@extend_schema(
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "raw_image": {
                    "type": "string",
                    "format": "binary"
                }
            }
        }
    }
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@role_required(UserRole.RADIOLOGIC_TECH)
def upload_xray(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    serializer = XrayRecordUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    raw_image = serializer.validated_data["raw_image"]
    file_suffix = Path(raw_image.name).suffix.lower().lstrip(".")
    file_format = file_suffix if file_suffix else "unknown"

    save_kwargs = {
        "patient": patient,
        "uploader": request.user,
        "status": "PENDING",
        "file_format": file_format,
    }

    if file_format == "dcm":
        try:
            raw_image.seek(0)
            ds = pydicom.dcmread(raw_image)

            tags_to_strip = [
                "PatientName", "PatientID", "PatientBirthDate",
                "PatientSex", "PatientAge", "InstitutionName",
                "ReferringPhysicianName", "StudyDate", "AccessionNumber"
            ]

            for tag in tags_to_strip:
                if hasattr(ds, tag):
                    delattr(ds, tag)

            buffer = BytesIO()
            ds.save_as(buffer)
            buffer.seek(0)

            save_kwargs["raw_image"] = ContentFile(buffer.read(), name=raw_image.name)

        except Exception as e:
            return Response(
                {"errors": {"raw_image": [f"Invalid DICOM file or failed to anonymize: {str(e)}"]}},
                status=status.HTTP_400_BAD_REQUEST
            )

    xray_record = serializer.save(**save_kwargs)

    try:
        processed_img = ProcessedImage.objects.filter(xray_record=xray_record).first()

        if processed_img:
            source_path = processed_img.processed_image.path
        else:
            source_path = xray_record.raw_image.path

        if source_path.lower().endswith(".dcm"):
            ds = pydicom.dcmread(source_path)
            pixel_array = ds.pixel_array
            img_cv = cv2.normalize(pixel_array, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        else:
            img_cv = cv2.imread(source_path, cv2.IMREAD_GRAYSCALE)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_img_cv = clahe.apply(img_cv)
        enhanced_pil = Image.fromarray(enhanced_img_cv)
        buffer = BytesIO()
        enhanced_pil.save(buffer, format="PNG")
        clahe_filename = f"{xray_record.transaction_id}_clahe.png"
        clahe_metadata = {
            "source": "clahe_enhancement",
            "clahe_settings": {"clipLimit": 2.0, "tileGridSize": [8, 8]},
            "ai_tensor_ready": False
        }

        if processed_img:
            processed_img.processed_image.save(clahe_filename, ContentFile(buffer.getvalue()), save=False)
            processed_img.preprocessing_metadata.update(clahe_metadata)
            processed_img.save()
        else:
            processed_img = ProcessedImage.objects.create(
                xray_record=xray_record,
                processed_image=ContentFile(buffer.getvalue(), name=clahe_filename),
                preprocessing_metadata=clahe_metadata
            )

        npy_output_path = preprocess_xray(processed_img.processed_image.path)
        metadata = processed_img.preprocessing_metadata
        metadata["ai_tensor_path"] = npy_output_path
        metadata["ai_tensor_ready"] = True

        processed_img.preprocessing_metadata = metadata
        processed_img.save()

    except Exception as e:
        xray_record.delete()
        return Response(
            {"errors": {"preprocessing": [f"Pipeline failed: {str(e)}"]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    force_proceed = str(request.data.get("force_proceed", "false")).lower() == "true"
    ai_result, created, error_msg, quality_info = _run_ai_inference(xray_record, processed_img, force_proceed=force_proceed)
    
    if quality_info:
        return Response({
            "status": "quality_check_failed",
            "message": "Uploaded image may be too low quality for reliable AI interpretation.",
            "quality_score": quality_info.get("score"),
            "requires_confirmation": True,
            "can_proceed": True,
            "transaction_id": str(xray_record.transaction_id)
        }, status=status.HTTP_200_OK)

    if error_msg:
        xray_record.refresh_from_db()
        serializer = XrayRecordSerializer(xray_record, context={'request': request})
        return Response(
            {
                "status": "MANUAL_REVIEW",
                "message": f"AI processing failed; case flagged for manual review: {error_msg}",
                "record": serializer.data
            },
            status=status.HTTP_202_ACCEPTED,
        )

    xray_record.refresh_from_db()
    serializer = XrayRecordSerializer(xray_record, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH)
def upload_confirm(request, patient_id, transaction_id):
    xray_record = get_object_or_404(
        XrayRecord,
        transaction_id=transaction_id,
        patient__patient_id=patient_id,
    )
    serializer = XrayRecordSerializer(xray_record)
    return Response(serializer.data)


@api_view(["POST"])
@role_required(UserRole.RADIOLOGIC_TECH)
def analyse_xray(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)
    processed_img = get_object_or_404(ProcessedImage, xray_record=xray_record)

    if not processed_img.processed_image:
        return Response(
            {"errors": {"processed_image": ["Processed image not found."]}},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        force_proceed = str(request.data.get("force_proceed", "false")).lower() == "true"
        ai_result, created, error_msg, quality_info = _run_ai_inference(xray_record, processed_img, force_proceed=force_proceed)
    except Exception as exc:
        return Response(
            {"errors": {"inference": [f"Inference failed: {exc}"]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if quality_info:
        return Response({
            "status": "quality_check_failed",
            "message": "Uploaded image may be too low quality for reliable AI interpretation.",
            "quality_score": quality_info.get("score"),
            "requires_confirmation": True,
            "can_proceed": True,
            "transaction_id": str(xray_record.transaction_id)
        }, status=status.HTTP_200_OK)

    if error_msg:
        return Response(
            {"errors": {"inference": [error_msg]}, "status": "MANUAL_REVIEW"},
            status=status.HTTP_202_ACCEPTED,
        )

    serializer = AIResultSerializer(ai_result, context={"request": request})
    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )

@api_view(["POST"])
@role_required(UserRole.RADIOLOGIST)
def annotate_xray(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)

    xray_record.clear_if_expired()
    if _lock_blocks_user(xray_record, request.user):
        return _lock_conflict_response(xray_record)

    if xray_record.active_reviewer_id != request.user.id:
        if not xray_record.acquire_lock(request.user):
            return _lock_conflict_response(xray_record)

    bounding_boxes = request.data.get("bounding_boxes")
    notes = request.data.get("notes", "")

    if isinstance(bounding_boxes, str):
        try:
            bounding_boxes = json.loads(bounding_boxes)
        except json.JSONDecodeError:
            return Response(
                {"errors": {"bounding_boxes": "Must be a JSON array."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if bounding_boxes is None:
        return Response(
            {"errors": {"bounding_boxes": "This field is required."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(bounding_boxes, list):
        return Response(
            {"errors": {"bounding_boxes": "Must be a JSON array."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not bounding_boxes:
        return Response(
            {"errors": {"bounding_boxes": "At least one annotation is required."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if notes is None:
        notes = ""

    if not isinstance(notes, str):
        return Response(
            {"errors": {"notes": "Must be a string."}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_keys = {"x", "y", "width", "height", "label", "shape", "points"}
    normalized_boxes = []
    box_errors = {}

    def _is_valid_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    for index, box in enumerate(bounding_boxes):
        path = f"bounding_boxes[{index}]"
        current_errors = []

        if not isinstance(box, dict):
            box_errors[path] = ["Each annotation must be an object."]
            continue

        unexpected_keys = sorted(set(box.keys()) - allowed_keys)
        if unexpected_keys:
            current_errors.append(f"Unexpected keys: {', '.join(unexpected_keys)}")

        shape = box.get("shape", "rectangle")
        if shape not in {"rectangle", "circle", "freehand"}:
            current_errors.append("shape must be one of: rectangle, circle, freehand.")

        for field in ("x", "y", "width", "height"):
            value = box.get(field)
            if not _is_valid_number(value):
                current_errors.append(f"{field} must be a finite number.")

        if _is_valid_number(box.get("width")) and box["width"] <= 0:
            current_errors.append("width must be greater than 0.")
        if _is_valid_number(box.get("height")) and box["height"] <= 0:
            current_errors.append("height must be greater than 0.")

        label = box.get("label", "")
        if label is None:
            label = ""
        if not isinstance(label, str):
            current_errors.append("label must be a string.")

        points = box.get("points")
        normalized_points = None

        if shape == "freehand":
            if not isinstance(points, list) or len(points) < 2:
                current_errors.append("freehand annotations require at least two points.")
            else:
                normalized_points = []
                for point_index, point in enumerate(points):
                    if not isinstance(point, dict):
                        current_errors.append(f"points[{point_index}] must be an object with x and y.")
                        continue
                    point_keys = sorted(set(point.keys()) - {"x", "y"})
                    if point_keys:
                        current_errors.append(
                            f"points[{point_index}] has unexpected keys: {', '.join(point_keys)}"
                        )
                    px = point.get("x")
                    py = point.get("y")
                    if not _is_valid_number(px) or not _is_valid_number(py):
                        current_errors.append(f"points[{point_index}] requires finite numeric x and y.")
                        continue
                    normalized_points.append({"x": float(px), "y": float(py)})
        elif points is not None:
            current_errors.append("points is only allowed when shape is freehand.")

        if current_errors:
            box_errors[path] = current_errors
            continue

        normalized_box = {
            "x": float(box["x"]),
            "y": float(box["y"]),
            "width": float(box["width"]),
            "height": float(box["height"]),
            "label": label,
            "shape": shape,
        }

        if shape == "freehand":
            normalized_box["points"] = normalized_points

        normalized_boxes.append(normalized_box)

    if box_errors:
        return Response(
            {"errors": {"bounding_boxes": box_errors}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    annotation = (
        Annotation.objects.filter(
            xray_record=xray_record,
            radiologist=request.user,
        )
        .order_by("-submitted_at")
        .first()
    )

    if annotation:
        annotation.bounding_boxes = normalized_boxes
        annotation.notes = notes
        annotation.save(update_fields=["bounding_boxes", "notes"])
        created = False
    else:
        annotation = Annotation.objects.create(
            xray_record=xray_record,
            radiologist=request.user,
            bounding_boxes=normalized_boxes,
            notes=notes,
        )
        created = True

    xray_record.status = "COMPLETED"
    xray_record.save(update_fields=["status"])

    # Case finalized — the review lock is no longer needed.
    xray_record.release_lock()

    return Response(
        {
            "transaction_id": str(xray_record.transaction_id),
            "annotation_id": annotation.id,
            "status": xray_record.status,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def patient_xrays(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    records = XrayRecord.objects.filter(
        patient=patient
    ).order_by('-upload_timestamp')
    serializer = XrayRecordSerializer(records, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH)
def technologist_dashboard(request):
    records = XrayRecord.objects.filter(
        uploader=request.user
    ).order_by('-upload_timestamp')

    # --- Search ---
    search = request.query_params.get('search', '').strip()
    if search:
        records = records.filter(
            models.Q(patient__first_name__icontains=search) |
            models.Q(patient__last_name__icontains=search)  |
            models.Q(transaction_id__icontains=search)
        )

    # --- Status filter ---
    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        records = records.filter(status=status_filter)
    
    risk_label_filter = request.query_params.get('risk_label', '').strip()
    if risk_label_filter:
        records = records.filter(ai_result__risk_label=risk_label_filter)

    paginator = PageNumberPagination()
    paginator.page_size = 20

    page = paginator.paginate_queryset(records, request)
    serializer = TechDashboardRecordSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIST)
def radiologist_queue(request):
    # Self-heal: release abandoned locks so the queue does not show stale IN_REVIEW rows.
    XrayRecord.clear_expired_locks()

    records = XrayRecord.objects.all().order_by('upload_timestamp')

    search = request.query_params.get('search', '').strip()
    if search:
        records = records.filter(
            models.Q(patient__first_name__icontains=search) |
            models.Q(patient__last_name__icontains=search)  |
            models.Q(transaction_id__icontains=search)
        )

    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        records = records.filter(status=status_filter)

    risk_label_filter = request.query_params.get('risk_label', '').strip()
    if risk_label_filter:
        records = records.filter(ai_result__risk_label=risk_label_filter)

    paginator = PageNumberPagination()
    paginator.page_size = 20

    page = paginator.paginate_queryset(records, request)
    serializer = RadiologistQueueSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@role_required(UserRole.PHYSICIAN)
def physician_dashboard(request):
    finalized_reports = (
        Report.objects.filter(status="SUBMITTED")
        .select_related("xray_record__patient", "xray_record__ai_result", "created_by")
        .order_by("-updated_at")
    )

    finalized_reports, filter_error, filter_meta = _apply_physician_dashboard_filters(
        request,
        finalized_reports,
    )
    if filter_error is not None:
        return filter_error

    finalized_report_count = finalized_reports.count()

    recent_reports = list(finalized_reports[:5])
    report_ready_items = list(finalized_reports[:10])
    finalized_cases = list(finalized_reports[:20])

    unread_alerts = (
        Notification.objects.filter(recipient=request.user, read_status=False)
        .order_by("-created_at")
    )

    patient_progress = []
    grouped_by_patient = {}
    for report in finalized_reports:
        patient_id = report.xray_record.patient.patient_id
        if patient_id not in grouped_by_patient:
            grouped_by_patient[patient_id] = {
                "patient": {
                    "patient_id": patient_id,
                    "first_name": report.xray_record.patient.first_name,
                    "last_name": report.xray_record.patient.last_name,
                },
                "total_finalized_reports": 0,
                "latest_transaction_id": str(report.xray_record.transaction_id),
                "latest_reported_at": report.updated_at.isoformat(),
                "latest_severity": report.severity,
                "latest_status": report.xray_record.status,
            }
        grouped_by_patient[patient_id]["total_finalized_reports"] += 1

    patient_progress = sorted(
        grouped_by_patient.values(),
        key=lambda item: item["latest_reported_at"],
        reverse=True,
    )[:10]

    return Response(
        {
            "filters": filter_meta,
            "summary": {
                "finalized_report_count": finalized_report_count,
                "recent_report_count": len(recent_reports),
                "pending_alert_count": unread_alerts.count(),
                "report_ready_count": len(report_ready_items),
                "patient_progress_count": len(patient_progress),
            },
            "finalized_cases": [_serialize_physician_report(report) for report in finalized_cases],
            "recent_reports": [_serialize_physician_report(report) for report in recent_reports],
            "report_ready_items": [_serialize_physician_report(report) for report in report_ready_items],
            "pending_alerts": [_serialize_physician_alert(alert) for alert in unread_alerts[:20]],
            "patient_progress": patient_progress,
        }
    )

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def xray_detail(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)

    if request.user.role == UserRole.RADIOLOGIST:
        # Drop a stale lock before deciding ownership so status/fields stay truthful.
        xray_record.clear_if_expired()

        if xray_record.active_reviewer_id and xray_record.active_reviewer_id != request.user.id and not xray_record.lock_has_expired():
            serializer = XrayRecordDetailSerializer(xray_record, context={'request': request})
            return Response(
                {
                    **serializer.data,
                    "detail": "This case is currently locked by another radiologist.",
                    "active_reviewer": xray_record.active_reviewer.username,
                    "lock_timestamp": xray_record.lock_timestamp.isoformat() if xray_record.lock_timestamp else None,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Acquire/renew the lock and enter the active review state.
        xray_record.start_review(request.user)

    serializer = XrayRecordDetailSerializer(xray_record, context={'request': request})
    return Response(serializer.data)


def _lock_blocks_user(xray_record, user):
    """True when a *fresh* lock is held by someone other than ``user``."""
    return bool(
        xray_record.active_reviewer_id
        and xray_record.active_reviewer_id != user.id
        and not xray_record.lock_has_expired()
    )


def _lock_conflict_response(xray_record):
    return Response(
        {
            "detail": "This case is currently locked by another radiologist.",
            "active_reviewer": xray_record.active_reviewer.username,
            "lock_timestamp": xray_record.lock_timestamp.isoformat() if xray_record.lock_timestamp else None,
        },
        status=status.HTTP_409_CONFLICT,
    )


@api_view(["POST"])
@role_required(UserRole.RADIOLOGIST)
def release_review_lock(request, transaction_id):
    """Release the caller's own review lock. Idempotent; never touches others' locks."""
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)
    if xray_record.active_reviewer_id == request.user.id:
        xray_record.release_lock()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@role_required(UserRole.RADIOLOGIST)
def renew_review_lock(request, transaction_id):
    """Heartbeat: renew the caller's lock, or acquire it if free/expired."""
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)
    xray_record.clear_if_expired()

    if _lock_blocks_user(xray_record, request.user):
        return _lock_conflict_response(xray_record)

    xray_record.start_review(request.user)
    return Response(
        {
            "transaction_id": str(xray_record.transaction_id),
            "active_reviewer": request.user.username,
            "lock_timestamp": xray_record.lock_timestamp.isoformat() if xray_record.lock_timestamp else None,
            "status": xray_record.status,
        }
    )

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def patient_history(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    records = (
        XrayRecord.objects.filter(patient=patient)
        .select_related("ai_result")
        .prefetch_related("annotations", "annotations__radiologist")
        .order_by("upload_timestamp")
    )
    serializer = PatientHistorySerializer(
        records, many=True, context={"request": request}
    )
    return Response(serializer.data)


def _resolve_case_record(case_id):
    try:
        return XrayRecord.objects.select_related("patient").get(pk=case_id)
    except (TypeError, ValueError, XrayRecord.DoesNotExist):
        try:
            return XrayRecord.objects.select_related("patient").get(transaction_id=case_id)
        except XrayRecord.DoesNotExist:
            return None


def _refresh_patient_progression_snapshots(patient):
    """Recompute persisted progression snapshots for all of a patient's records."""
    records = XrayRecord.objects.filter(patient=patient).order_by("upload_timestamp", "pk")
    for record in records:
        ProgressionService.persist_for_record(record)


@api_view(["GET"])
@login_required
def case_progression_history(request, case_id):
    case_record = _resolve_case_record(case_id)
    if case_record is None:
        return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)

    _refresh_patient_progression_snapshots(case_record.patient)

    queryset = ProgressionStatus.objects.filter(
        patient=case_record.patient
    ).select_related(
        "xray_record",
        "previous_record",
    ).order_by("xray_record__upload_timestamp", "xray_record__pk")

    paginator = ProgressionHistoryPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ProgressionStatusSerializer(page, many=True, context={"request": request}) if page is not None else ProgressionStatusSerializer(queryset, many=True, context={"request": request})
    if page is not None:
        return paginator.get_paginated_response(serializer.data)
    return Response(serializer.data)


@api_view(["POST"])
@role_required(UserRole.RADIOLOGIST)
def case_progression_override(request, case_id):
    case_record = _resolve_case_record(case_id)
    if case_record is None:
        return Response({"detail": "Case not found."}, status=status.HTTP_404_NOT_FOUND)

    status_value = request.data.get("status")
    clinical_note = request.data.get("clinical_note")
    if clinical_note is None or not str(clinical_note).strip():
        return Response({"clinical_note": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

    valid_statuses = {
        ProgressionService.NO_PRIOR,
        ProgressionService.STABLE,
        ProgressionService.DECREASED_RISK,
        ProgressionService.INCREASED_RISK,
    }
    if status_value not in valid_statuses:
        return Response({"status": ["Invalid progression status."]}, status=status.HTTP_400_BAD_REQUEST)

    progression = ProgressionStatus.objects.filter(
        patient=case_record.patient,
        xray_record=case_record,
    ).first()
    if progression is None:
        ProgressionService.persist_for_record(case_record)
        progression = ProgressionStatus.objects.get(
            patient=case_record.patient,
            xray_record=case_record,
        )

    previous_status = progression.status
    progression.status = status_value
    progression.source = "manual_override"
    progression.is_overridden = True
    progression.clinical_note = str(clinical_note).strip()
    progression.overridden_by = request.user
    progression.override_timestamp = timezone.now()
    progression.reason = "Manual override"
    progression.save(update_fields=[
        "status",
        "source",
        "clinical_note",
        "is_overridden",
        "overridden_by",
        "override_timestamp",
        "reason",
    ])

    audit_log = ProgressionOverrideAuditLog.objects.create(
        patient=case_record.patient,
        xray_record=case_record,
        radiologist=request.user,
        previous_status=previous_status,
        new_status=status_value,
        clinical_note=progression.clinical_note,
    )

    payload = ProgressionStatusSerializer(progression, context={"request": request}).data
    payload["audit_log_id"] = audit_log.id
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@login_required
def patient_progression_history(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    _refresh_patient_progression_snapshots(patient)

    queryset = ProgressionStatus.objects.filter(patient=patient).select_related(
        "xray_record",
        "previous_record",
    ).order_by("xray_record__upload_timestamp", "xray_record__pk")

    paginator = ProgressionHistoryPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ProgressionStatusSerializer(page, many=True, context={"request": request}) if page is not None else ProgressionStatusSerializer(queryset, many=True, context={"request": request})
    if page is not None:
        return paginator.get_paginated_response(serializer.data)
    return Response(serializer.data)


@api_view(["GET"])
@login_required
def patient_progression_override_history(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)

    queryset = ProgressionOverrideAuditLog.objects.filter(
        patient=patient,
    ).select_related(
        "xray_record",
        "radiologist",
    ).order_by("-created_at", "-id")

    serializer = ProgressionOverrideAuditLogSerializer(
        queryset,
        many=True,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["GET"])
@login_required
def notifications(request):
    items = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    data = [{
        'id': item.id,
        'recipient': item.recipient_id,
        'message': item.message,
        'read_status': item.read_status,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    } for item in items]
    return Response(data)


@api_view(["POST"])
@login_required
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )
    notification.read_status = True
    notification.save(update_fields=['read_status', 'updated_at'])
    return Response({
        'id': notification.id,
        'recipient': notification.recipient_id,
        'message': notification.message,
        'read_status': notification.read_status,
        'created_at': notification.created_at.isoformat(),
        'updated_at': notification.updated_at.isoformat(),
    })


@api_view(["GET", "POST", "PATCH"])
@role_required(UserRole.RADIOLOGIST)
def report_detail(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)

    if request.method in {"POST", "PATCH"}:
        xray_record.clear_if_expired()
        if _lock_blocks_user(xray_record, request.user):
            return _lock_conflict_response(xray_record)

    if request.method == "GET":
        try:
            report = xray_record.report
        except Report.DoesNotExist:
            return Response(
                {"detail": "Report not found for this X-ray."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ReportSerializer(report, context={'request': request})
        return Response(serializer.data)

    elif request.method == "POST":
        report, created = Report.objects.get_or_create(
            xray_record=xray_record,
            defaults={
                'findings': '',
                'impression': '',
                'recommendation': '',
                'severity': Report.SeverityChoices.NORMAL,
                'status': 'DRAFT',
            }
        )
        # For draft creation, always pass status='DRAFT'
        data = {**request.data, 'status': 'DRAFT'}
        serializer = ReportCreateSerializer(report, data=data, partial=False)

        if serializer.is_valid():
            serializer.save()
            if report.status == 'SUBMITTED':
                _trigger_report_submission_notification(report)
            return Response(
                ReportSerializer(report, context={'request': request}).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PATCH":
        try:
            report = xray_record.report
        except Report.DoesNotExist:
            return Response(
                {"detail": "Report not found for this X-ray."},
                status=status.HTTP_404_NOT_FOUND
            )

        if report.status == 'SUBMITTED':
            return Response(
                {"detail": "Cannot modify a finalized report."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Allow client to pass status='SUBMITTED' to submit
        serializer = ReportCreateSerializer(report, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            previous_status = report.status
            report = serializer.save()
            if previous_status != 'SUBMITTED' and report.status == 'SUBMITTED':
                _trigger_report_submission_notification(report)
                # Report finalized — release the review lock on the case.
                xray_record.release_lock()
            return Response(
                ReportSerializer(report, context={'request': request}).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@role_required(UserRole.RADIOLOGIST)
def generate_report(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)

    if xray_record.status != "COMPLETED":
        return Response(
            {"detail": "PDF report can only be generated for COMPLETED X-rays."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get or create report (allow PDF generation even if not finalized)
    try:
        report = xray_record.report
    except Report.DoesNotExist:
        # Auto-create minimal report for PDF generation
        report = Report.objects.create(
            xray_record=xray_record,
            findings="Report not yet structured. See diagnostic notes below.",
            impression="Pending radiologist finalization.",
            recommendation="Clinical correlation recommended.",
            severity=Report.SeverityChoices.NORMAL,
            status='DRAFT',
        )

    patient = xray_record.patient
    ai_result = getattr(xray_record, "ai_result", None)
    annotations = xray_record.annotations.all()

    heatmap_base64 = None
    if ai_result and ai_result.heatmap_image:
        if ai_result.heatmap_image.storage.exists(ai_result.heatmap_image.name):
            with ai_result.heatmap_image.open("rb") as img_file:
                heatmap_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    radiologist_notes = []
    for ann in annotations:
        if ann.notes:
            radiologist_notes.append(ann.notes)

    diagnostic_notes_text = "\n".join(radiologist_notes) if radiologist_notes else "No diagnostic notes provided."

    def calculate_age(dob):
        if not dob: return "N/A"
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    context = {
        "transaction_id": str(xray_record.transaction_id),
        "upload_date": xray_record.upload_timestamp.strftime("%Y-%m-%d %H:%M"),
        "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M"),
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "patient_age": calculate_age(getattr(patient, 'date_of_birth', None)),
        "patient_sex": getattr(patient, 'sex', 'N/A'),
        "facility_name": "",
        "ai_risk_score": f"{ai_result.risk_score:.2f}" if ai_result else "N/A",
        "ai_risk_label": ai_result.risk_label if ai_result else "N/A",
        "heatmap_base64": heatmap_base64,
        "radiologist_annotations": radiologist_notes,
        "diagnostic_notes": diagnostic_notes_text,
        "clinical_impression": report.impression if report else "",
        "recommendations": report.recommendation if report else "",
        "ai_summary": f"AI model flagged as {ai_result.risk_label if ai_result else 'N/A'} risk."
    }
    html_content = render_to_string("reports/xray_report.html", context)
    temp_html_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as temp_html:
            temp_html.write(html_content)
            temp_html_path = temp_html.name

        script_path = settings.BASE_DIR / "pdf_scripts" / "generate.js"
        result = subprocess.run(
            ["node", str(script_path), temp_html_path],
            capture_output=True,
            check=True
        )

        pdf_bytes = result.stdout
        response = FileResponse(BytesIO(pdf_bytes), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="tbxr_report_{transaction_id}.pdf"'
        return response

    except subprocess.CalledProcessError as e:
        return Response(
            {"error": "Failed to generate PDF via Node script.", "details": e.stderr.decode()},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        if temp_html_path:
            Path(temp_html_path).unlink(missing_ok=True)


def _parse_date_param(value: str, param_name: str):
    """Parse a date string in YYYY-MM-DD format. Returns (date, error_response)."""
    parsed = parse_date(value)
    if parsed is None:
        return None, Response(
            {"detail": f"Invalid {param_name} format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return parsed, None


def _apply_date_filter(queryset, date_from, date_to, date_field: str):
    """Apply date range filter to queryset using the specified date field."""
    if date_from:
        queryset = queryset.filter(**{f"{date_field}__date__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{date_field}__date__lte": date_to})
    return queryset


def _get_analytics_data(date_from, date_to, severity):
    # Base querysets
    xray_qs = XrayRecord.objects.all()
    report_qs = Report.objects.select_related("xray_record").all()

    # Apply date filters (on X-ray upload_timestamp for cases, report created_at for reports)
    xray_qs = _apply_date_filter(xray_qs, date_from, date_to, "upload_timestamp")
    report_qs = _apply_date_filter(report_qs, date_from, date_to, "created_at")

    # Apply severity filter to reports
    if severity:
        report_qs = report_qs.filter(severity=severity)

    # Aggregate cases
    total_cases = xray_qs.count()
    status_counts = dict(
        xray_qs.values_list("status").order_by().annotate(count=models.Count("status"))
    )

    # AI risk label breakdown (only for records with AI results)
    ai_qs = AIResult.objects.filter(xray_record__in=xray_qs)
    ai_risk_counts = dict(
        ai_qs.values_list("risk_label").order_by().annotate(count=models.Count("risk_label"))
    )

    # Aggregate reports
    total_reports = report_qs.count()
    severity_counts = dict(
        report_qs.values_list("severity").order_by().annotate(count=models.Count("severity"))
    )
    report_status_counts = dict(
        report_qs.values_list("status").order_by().annotate(count=models.Count("status"))
    )

    return {
        "filters": {
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "severity": severity or None,
        },
        "cases": {
            "total": total_cases,
            "by_status": status_counts,
            "by_ai_risk_label": ai_risk_counts,
        },
        "reports": {
            "total": total_reports,
            "by_severity": severity_counts,
            "by_status": report_status_counts,
        }
    }


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="date_from",
            type=OpenApiTypes.DATE,
            description="Start date (inclusive) in YYYY-MM-DD format. Filters by X-ray upload date.",
        ),
        OpenApiParameter(
            name="date_to",
            type=OpenApiTypes.DATE,
            description="End date (inclusive) in YYYY-MM-DD format. Filters by X-ray upload date.",
        ),
        OpenApiParameter(
            name="severity",
            type=OpenApiTypes.STR,
            enum=Report.SeverityChoices.values,
            description="Filter reports by severity level.",
        ),
    ],
    responses={200: {
        "type": "object",
        "properties": {
            "filters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "format": "date", "nullable": True},
                    "date_to": {"type": "string", "format": "date", "nullable": True},
                    "severity": {"type": "string", "nullable": True},
                },
            },
            "cases": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "by_status": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "by_ai_risk_label": {"type": "object", "additionalProperties": {"type": "integer"}},
                },
            },
            "reports": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "by_severity": {"type": "object", "additionalProperties": {"type": "integer"}},
                    "by_status": {"type": "object", "additionalProperties": {"type": "integer"}},
                },
            },
        },
    }},
)
@api_view(["GET"])
@role_required(UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def analytics_summary(request):
    """
    Returns aggregate case metrics for a selected date range and severity set.
    Supports filtering by upload date range and report severity.
    """
    date_from_raw = request.query_params.get("date_from", "").strip()
    date_to_raw = request.query_params.get("date_to", "").strip()
    severity = request.query_params.get("severity", "").strip().upper()

    date_from, error = _parse_date_param(date_from_raw, "date_from") if date_from_raw else (None, None)
    if error:
        return error

    date_to, error = _parse_date_param(date_to_raw, "date_to") if date_to_raw else (None, None)
    if error:
        return error

    if date_from and date_to and date_from > date_to:
        return Response(
            {"detail": "date_from cannot be later than date_to."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if severity and severity not in Report.SeverityChoices.values:
        return Response(
            {
                "detail": (
                    f"Invalid severity '{severity}'. Allowed values: "
                    f"{', '.join(Report.SeverityChoices.values)}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = _get_analytics_data(date_from, date_to, severity)
    return Response(data)


import csv
from django.http import HttpResponse

@extend_schema(
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["csv", "pdf"]},
                "filters": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "format": "date"},
                        "date_to": {"type": "string", "format": "date"},
                        "severity": {"type": "string"}
                    }
                }
            },
            "required": ["format"]
        }
    },
    responses={
        200: OpenApiTypes.BINARY,
    }
)
@api_view(["POST"])
@role_required(UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def analytics_export(request):
    """
    Export analytics data to CSV or PDF based on requested format and filters.
    """
    format_type = request.data.get("format")
    filters = request.data.get("filters", {})

    if format_type not in ["csv", "pdf"]:
        return Response(
            {"detail": "Invalid format. Must be 'csv' or 'pdf'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    date_from_raw = filters.get("date_from", "")
    date_to_raw = filters.get("date_to", "")
    severity = filters.get("severity", "")

    # Ensure these are strings before calling strip()
    if date_from_raw is None: date_from_raw = ""
    if date_to_raw is None: date_to_raw = ""
    if severity is None: severity = ""

    date_from_raw = str(date_from_raw).strip()
    date_to_raw = str(date_to_raw).strip()
    severity = str(severity).strip().upper()

    date_from, error = _parse_date_param(date_from_raw, "date_from") if date_from_raw else (None, None)
    if error: return error

    date_to, error = _parse_date_param(date_to_raw, "date_to") if date_to_raw else (None, None)
    if error: return error

    if date_from and date_to and date_from > date_to:
        return Response(
            {"detail": "date_from cannot be later than date_to."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if severity and severity not in Report.SeverityChoices.values:
        return Response(
            {
                "detail": (
                    f"Invalid severity '{severity}'. Allowed values: "
                    f"{', '.join(Report.SeverityChoices.values)}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = _get_analytics_data(date_from, date_to, severity)

    if format_type == "csv":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="analytics_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(["Category", "Metric", "Value"])
        
        writer.writerow(["Cases", "Total Cases", data["cases"]["total"]])
        for s, c in data["cases"]["by_status"].items():
            writer.writerow(["Cases", f"Status: {s}", c])
        for r, c in data["cases"]["by_ai_risk_label"].items():
            writer.writerow(["Cases", f"AI Risk: {r}", c])
            
        writer.writerow(["Reports", "Total Reports", data["reports"]["total"]])
        for s, c in data["reports"]["by_severity"].items():
            writer.writerow(["Reports", f"Severity: {s}", c])
        for s, c in data["reports"]["by_status"].items():
            writer.writerow(["Reports", f"Status: {s}", c])
            
        return response

    elif format_type == "pdf":
        context = {
            "data": data,
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        html_content = render_to_string("reports/analytics_export.html", context)
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name

            script_path = settings.BASE_DIR / "pdf_scripts" / "generate.js"
            result = subprocess.run(
                ["node", str(script_path), temp_html_path],
                capture_output=True,
                check=True
            )

            pdf_bytes = result.stdout
            response = FileResponse(BytesIO(pdf_bytes), content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="analytics_export.pdf"'
            return response

        except subprocess.CalledProcessError as e:
            return Response(
                {"error": "Failed to generate PDF via Node script.", "details": e.stderr.decode()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
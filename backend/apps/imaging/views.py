import base64
import tempfile
import subprocess
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
import pydicom
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.core.files import File
from django.core.files.base import ContentFile
from drf_spectacular.utils import extend_schema

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
from .models import Annotation, XrayRecord, ProcessedImage, AIResult, Report, Notification
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
    ReportSerializer,
    ReportCreateSerializer,
)

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
    spec.loader.exec_module(module)
    _INFERENCE_MODULE = module
    return module


import time
import logging

logger = logging.getLogger(__name__)


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

    if notes is None:
        notes = ""

    if not isinstance(notes, str):
        return Response(
            {"errors": {"notes": "Must be a string."}},
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
        annotation.bounding_boxes = bounding_boxes
        annotation.notes = notes
        annotation.save(update_fields=["bounding_boxes", "notes"])
        created = False
    else:
        annotation = Annotation.objects.create(
            xray_record=xray_record,
            radiologist=request.user,
            bounding_boxes=bounding_boxes,
            notes=notes,
        )
        created = True

    xray_record.status = "COMPLETED"
    xray_record.save(update_fields=["status"])

    return Response(
        {
            "transaction_id": str(xray_record.transaction_id),
            "annotation_id": annotation.id,
            "status": xray_record.status,
        },
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST)
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
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST)
def xray_detail(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)

    if request.user.role == UserRole.RADIOLOGIST:
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

        xray_record.acquire_lock(request.user)

    serializer = XrayRecordDetailSerializer(xray_record, context={'request': request})
    return Response(serializer.data)

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST)
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
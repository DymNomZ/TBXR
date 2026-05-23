import json
import cv2
import importlib.util
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.core.files import File
from django.core.files.base import ContentFile
from drf_spectacular.utils import extend_schema

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
from .models import Annotation, XrayRecord, ProcessedImage, AIResult
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
)

_INFERENCE_MODULE = None


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


def _run_ai_inference(xray_record, processed_img):
    inference = _get_inference_module()
    image_path = processed_img.processed_image.path
    prediction = inference.predict(image_path)
    heatmap_path = inference.generate_heatmap(image_path)

    try:
        risk_score = float(prediction.get("risk_score"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid risk score from inference.") from exc

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

    return ai_result, created

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

    xray_record = serializer.save(
        patient=patient,
        uploader=request.user,
        status="PENDING",
        file_format=file_format,
    )

    try:
        processed_img = ProcessedImage.objects.filter(xray_record=xray_record).first()

        if processed_img:
            source_path = processed_img.processed_image.path
        else:
            source_path = xray_record.raw_image.path

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

    try:
        _run_ai_inference(xray_record, processed_img)
    except ValueError as e:
        xray_record.delete()
        return Response(
            {"errors": {"risk_score": [str(e)]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as e:
        xray_record.delete()
        return Response(
            {"errors": {"inference": [f"Inference failed: {str(e)}"]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        ai_result, created = _run_ai_inference(xray_record, processed_img)
    except ValueError as exc:
        return Response(
            {"errors": {"risk_score": [str(exc)]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        return Response(
            {"errors": {"inference": [f"Inference failed: {exc}"]}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    paginator = PageNumberPagination()
    paginator.page_size = 20

    page = paginator.paginate_queryset(records, request)
    serializer = RadiologistQueueSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def xray_detail(request, transaction_id):
    xray_record = get_object_or_404(XrayRecord, transaction_id=transaction_id)
    serializer = XrayRecordDetailSerializer(xray_record, context={'request': request})
    return Response(serializer.data)

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
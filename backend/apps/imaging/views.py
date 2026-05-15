import json
from drf_spectacular.utils import extend_schema
from pathlib import Path

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
from .models import Annotation, XrayRecord
from django.db import models
from .serializers import XrayRecordUploadSerializer, XrayRecordSerializer, TechDashboardRecordSerializer

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

    serializer = XrayRecordSerializer(xray_record)
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
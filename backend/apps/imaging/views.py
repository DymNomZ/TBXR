from drf_spectacular.utils import extend_schema
from pathlib import Path

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.reverse import reverse



from apps.accounts.decorators import role_required
from apps.accounts.enums import UserRole
from apps.patients.models import Patient
from .models import XrayRecord
from .serializers import XrayRecordUploadSerializer, XrayRecordSerializer

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

    confirm_url = reverse(
        "imaging:upload_confirm",
        kwargs={
            "patient_id": patient.patient_id,
            "transaction_id": xray_record.transaction_id,
        },
        request=request,
    )
    headers = {"Location": confirm_url}
    return Response(status=status.HTTP_303_SEE_OTHER, headers=headers)


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

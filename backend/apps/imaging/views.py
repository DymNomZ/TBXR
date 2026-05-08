import cv2
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
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

from .preprocessing import preprocess_xray
from .models import XrayRecord, ProcessedImage
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
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

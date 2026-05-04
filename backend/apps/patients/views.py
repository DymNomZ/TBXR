from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from .models import Patient
from .serializers import PatientCreateSerializer, PatientSerializer


@extend_schema(
    request=PatientCreateSerializer,
    responses={
        201: PatientSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
)
@api_view(["POST"])
def register_patient(request):
    serializer = PatientCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    patient = serializer.save()
    response_serializer = PatientSerializer(patient)
    headers = {
        "Location": reverse(
            "patients:detail",
            kwargs={"patient_id": patient.patient_id},
            request=request,
        )
    }
    return Response(
        response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
    )


@extend_schema(responses={200: PatientSerializer})
@api_view(["GET"])
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    serializer = PatientSerializer(patient)
    return Response(serializer.data)

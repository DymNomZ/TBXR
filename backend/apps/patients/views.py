from django.shortcuts import get_object_or_404
from apps.accounts.decorators import role_required
from apps.accounts.enums import UserRole
from drf_spectacular.utils import OpenApiResponse, extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django.db.models import Q

from .models import Patient
from .serializers import PatientCreateSerializer, PatientSerializer

# DRF's @api_view turns a function into an API view with request.data parsing and content negotiation.

@extend_schema(
    request=PatientCreateSerializer,
    responses={
        201: PatientSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
)
@api_view(["POST"])
@role_required(UserRole.RADIOLOGIC_TECH)
# Only technologists should register patients, radiologists and physicians only review existing records.    
# Why: They are the ones who intake patients and create records before uploading X-rays. 
# Radiologists and Physicians only review, never register.
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
    # DRF Response renders to JSON and handles status codes, similar to JsonResponse but API-aware.
    return Response(
        response_serializer.data, status=status.HTTP_201_CREATED, headers=headers
    )

@extend_schema(responses={200: PatientSerializer})
@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
# All three roles need to view a patient's profile at different stages of the workflow.
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    serializer = PatientSerializer(patient)
    return Response(serializer.data)

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="name",
            description="Search by first name or last name",
            required=False,
            type=str
        )
    ],
    responses={200: PatientSerializer(many=True)}
)
@api_view(["GET"])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
# Same reasoning. search is just the entry point to get to a patient detail, all roles need it.
def search_patients(request):
    # Get the 'name' search term from the URL
    query = request.query_params.get('name', '').strip()

    if query:
        # Find patients where first OR last name matches the query (case-insensitive)
        patients = Patient.objects.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    else:
        patients = Patient.objects.all()

    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST, UserRole.PHYSICIAN)
def patient_list(request):
    patients = Patient.objects.all().order_by('last_name', 'first_name')
    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data)
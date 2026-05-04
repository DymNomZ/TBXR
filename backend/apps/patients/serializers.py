from rest_framework import serializers

from .models import Patient

# DRF serializers define API payloads and validation, compared to plain Django views that parse request data manually. This allows for the usage of 
class PatientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "contact_number",
        ]


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "patient_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "contact_number",
            "date_created",
        ]

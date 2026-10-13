from rest_framework import serializers

from .models import Patient
from .phone_numbers import format_contact_number, normalize_contact_number

# DRF serializers define API payloads and validation, compared to plain Django views that parse request data manually. This allows for the usage of 
class PatientCreateSerializer(serializers.ModelSerializer):
    def validate_contact_number(self, value):
        try:
            return normalize_contact_number(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

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
    contact_number = serializers.SerializerMethodField()

    def get_contact_number(self, obj):
        return format_contact_number(obj.contact_number)

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

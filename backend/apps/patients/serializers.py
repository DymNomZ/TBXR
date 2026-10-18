from rest_framework import serializers

from .models import Patient
from .phone_numbers import (
    format_contact_number,
    normalize_contact_number,
    normalize_region_code,
)

# DRF serializers define API payloads and validation, compared to plain Django views that parse request data manually. This allows for the usage of 
class PatientCreateSerializer(serializers.ModelSerializer):
    def validate_country_code(self, value):
        try:
            return normalize_region_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        country_code = attrs.get("country_code") or "PH"
        attrs["country_code"] = country_code

        try:
            attrs["contact_number"] = normalize_contact_number(
                attrs.get("contact_number"),
                country_code,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"contact_number": str(exc)}) from exc

        return attrs

    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "country_code",
            "contact_number",
        ]


class PatientSerializer(serializers.ModelSerializer):
    contact_number = serializers.SerializerMethodField()

    def get_contact_number(self, obj):
        return format_contact_number(obj.contact_number, obj.country_code)

    class Meta:
        model = Patient
        fields = [
            "patient_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "sex",
            "country_code",
            "contact_number",
            "date_created",
        ]

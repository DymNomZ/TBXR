from rest_framework import serializers

from .models import XrayRecord


class XrayRecordUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = XrayRecord
        fields = ["raw_image"]


class XrayRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = XrayRecord
        fields = [
            "transaction_id",
            "patient",
            "raw_image",
            "upload_timestamp",
            "status",
            "file_format",
        ]

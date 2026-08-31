import os
import pydicom
import numpy as np
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Annotation, XrayRecord, ProcessedImage, AIResult, Report
from apps.patients.models import Patient
from django.contrib.auth import get_user_model

User = get_user_model()

class PatientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['patient_id', 'first_name', 'last_name']

class UploaderBriefSerializer(serializers.ModelSerializer):
    """Technologist who uploaded the xray."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']

class RadiologistBriefSerializer(serializers.ModelSerializer):
    """Minimal radiologist info for annotation authorship."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username']

class AIResultBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIResult
        fields = ['risk_score', 'risk_label', 'model_version']

class AnnotationSerializer(serializers.ModelSerializer):
    radiologist = RadiologistBriefSerializer(read_only=True)

    class Meta:
        model = Annotation
        fields = [
            'id',
            'radiologist',
            'bounding_boxes',
            'notes',
            'submitted_at',
        ]
        # xray_record is intentionally excluded — redundant inside a nested response

class PatientHistorySerializer(serializers.ModelSerializer):
    ai_result     = AIResultBriefSerializer(read_only=True)
    annotations   = AnnotationSerializer(many=True, read_only=True)
    display_image = serializers.SerializerMethodField()

    def get_display_image(self, obj):
        request   = self.context.get('request')
        processed = ProcessedImage.objects.filter(xray_record=obj).first()
        if processed and processed.processed_image:
            url = processed.processed_image.url
            return request.build_absolute_uri(url) if request else url
        if obj.raw_image:
            url = obj.raw_image.url
            return request.build_absolute_uri(url) if request else url
        return None

    class Meta:
        model  = XrayRecord
        fields = [
            'transaction_id',
            'display_image',
            'upload_timestamp',
            'status',
            'file_format',
            'ai_result',
            'annotations',
        ]

class AIResultSerializer(serializers.ModelSerializer):
    heatmap_url = serializers.SerializerMethodField()

    def get_heatmap_url(self, obj):
        if not obj.heatmap_image:
            return None
        request = self.context.get("request")
        url = obj.heatmap_image.url
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = AIResult
        fields = [
            "risk_score",
            "risk_label",
            "heatmap_url",    # Keeping your teammate's safe URL generator!
            "model_version",  # Your new Step 24 field
            "generated_at",   # Your new Step 24 field
        ]


class XrayRecordHistorySerializer(serializers.ModelSerializer):
    ai_result = AIResultSerializer(read_only=True)
    annotations = AnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = XrayRecord
        fields = [
            "transaction_id",
            "raw_image",
            "upload_timestamp",
            "status",
            "file_format",
            "ai_result",
            "annotations",
        ]

class TechDashboardRecordSerializer(serializers.ModelSerializer):
    # Nests the patient fields instead of just returning the FK
    patient = PatientBriefSerializer(read_only=True)
    ai_result = AIResultBriefSerializer(read_only=True)

    class Meta:
        model = XrayRecord
        fields = [
            'transaction_id',
            'patient',           # now { patient_id, first_name, last_name }
            'upload_timestamp',
            'status',
            'file_format',
            'ai_result',
        ]

class RadiologistQueueSerializer(serializers.ModelSerializer):
    """
    Used by: radiologist_queue (GET /api/imaging/queue/).
    Includes raw_image so the radiologist can open the file from the queue.
    """
    patient = PatientBriefSerializer(read_only=True)
    uploader = UploaderBriefSerializer(read_only=True)
    ai_result = AIResultBriefSerializer(read_only=True)

    class Meta:
        model = XrayRecord
        fields = [
            'transaction_id',
            'patient',
            'uploader',  
            'raw_image',
            'upload_timestamp',
            'status',
            'file_format',
            'ai_result',
        ]

class XrayRecordUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = XrayRecord
        fields = ["raw_image"]

    def validate_raw_image(self, value):

        max_size_mb = 20
        if value.size > (max_size_mb * 1024 * 1024):
            raise serializers.ValidationError(
                f"File rejected: Size exceeds the {max_size_mb}MB limit."
            )

        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.dcm']

        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"File rejected: Unsupported format '{ext}'. Accepted formats are: {', '.join(valid_extensions)}"
            )

        return value

    def create(self, validated_data):

        xray_record = super().create(validated_data)

        raw_file = validated_data['raw_image']
        ext = os.path.splitext(raw_file.name)[1].lower()

        if ext == '.dcm':
            try:
                raw_file.seek(0)
                dicom_data = pydicom.dcmread(raw_file)

                # Check to confirm that the DICOM file contains pixel data
                if not hasattr(dicom_data, 'pixel_array'):
                    xray_record.delete()
                    raise serializers.ValidationError(
                        "File rejected: DICOM file does not contain image data."
                    )

                pixel_array = dicom_data.pixel_array.astype(float)

                if 'RescaleSlope' in dicom_data and 'RescaleIntercept' in dicom_data:
                    slope = float(dicom_data.RescaleSlope)
                    intercept = float(dicom_data.RescaleIntercept)
                    pixel_array = pixel_array * slope + intercept

                if 'WindowCenter' in dicom_data and 'WindowWidth' in dicom_data:
                    window_center = dicom_data.WindowCenter
                    window_width = dicom_data.WindowWidth

                    if isinstance(window_center, pydicom.multival.MultiValue):
                        window_center = float(window_center[0])
                    else:
                        window_center = float(window_center)

                    if isinstance(window_width, pydicom.multival.MultiValue):
                        window_width = float(window_width[0])
                    else:
                        window_width = float(window_width)

                    vmin = window_center - (window_width / 2.0)
                    vmax = window_center + (window_width / 2.0)

                    pixel_array = np.clip(pixel_array, vmin, vmax)
                    image_scaled = ((pixel_array - vmin) / (vmax - vmin)) * 255.0
                else:
                    p1 = np.percentile(pixel_array, 1)
                    p99 = np.percentile(pixel_array, 99)
                    pixel_array = np.clip(pixel_array, p1, p99)
                    image_scaled = ((pixel_array - p1) / (p99 - p1)) * 255.0

                if hasattr(dicom_data,
                           'PhotometricInterpretation') and dicom_data.PhotometricInterpretation == "MONOCHROME1":
                    image_scaled = 255.0 - image_scaled

                image_uint8 = np.uint8(image_scaled)

                # Handle multi-frame or single-frame 3D arrays e.g. (1, rows, cols)
                if image_uint8.ndim == 3:
                    if image_uint8.shape[0] == 1:
                        # Single frame stored as (1, rows, cols) — safe to squeeze
                        image_uint8 = image_uint8.squeeze(0)
                    else:
                        # Multi-frame — out of scope for chest X-ray screening
                        xray_record.delete()
                        raise serializers.ValidationError(
                            "File rejected: Multi-frame DICOMs are not supported. "
                            "TB-XR accepts single-frame chest X-ray images only."
                        )

                img = Image.fromarray(image_uint8)

                buffer = BytesIO()
                img.save(buffer, format="PNG")

                png_filename = f"{xray_record.transaction_id}_converted.png"
                png_file = ContentFile(buffer.getvalue(), name=png_filename)

                ProcessedImage.objects.create(
                    xray_record=xray_record,
                    processed_image=png_file,
                    preprocessing_metadata={"source": "dcm_conversion"}
                )
            except Exception as e:
                xray_record.delete()
                raise serializers.ValidationError(f"Failed to process DICOM file: {str(e)}")

        return xray_record


class XrayRecordSerializer(serializers.ModelSerializer):
    ai_result = AIResultSerializer(read_only=True)

    class Meta:
        model = XrayRecord
        fields = [
            "transaction_id",
            "patient",
            "raw_image",
            "upload_timestamp",
            "status",
            "file_format",
            "ai_result",
        ]

class XrayRecordDetailSerializer(serializers.ModelSerializer):
    """
    Used by: future radiologist review/detail endpoint.
    """
    patient = PatientBriefSerializer(read_only=True)
    annotations = AnnotationSerializer(many=True, read_only=True)
    ai_result     = AIResultSerializer(read_only=True)
    display_image = serializers.SerializerMethodField()

    def get_display_image(self, obj):
        request = self.context.get('request')

        # Prefer the processed/converted image as this is what DCM files need,
        # and it's also the CLAHE-enhanced version for all other formats
        processed = ProcessedImage.objects.filter(xray_record=obj).first()
        if processed and processed.processed_image:
            url = processed.processed_image.url
            return request.build_absolute_uri(url) if request else url

        # Fallback to raw image (JPG/PNG uploads with no processed version)
        if obj.raw_image:
            url = obj.raw_image.url
            return request.build_absolute_uri(url) if request else url

        return None

    active_reviewer = serializers.SerializerMethodField()

    def get_active_reviewer(self, obj):
        return obj.active_reviewer.username if obj.active_reviewer else None

    class Meta:
        model = XrayRecord
        fields = [
            'transaction_id',
            'patient',
            'raw_image',       # keep, useful for download/reference
            'display_image',   # what the viewer should actually render
            'upload_timestamp',
            'status',
            'file_format',
            'annotations',
            'ai_result',
            'active_reviewer',
            'lock_timestamp',
        ]


class ReportSerializer(serializers.ModelSerializer):
    created_by = RadiologistBriefSerializer(read_only=True)
    xray_record = serializers.UUIDField(source='xray_record.transaction_id', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'xray_record', 'findings', 'impression',
            'recommendation', 'severity', 'created_by',
            'created_at', 'updated_at', 'status'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'status']


class ReportCreateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted')], required=False, default='DRAFT')

    class Meta:
        model = Report
        fields = ['findings', 'impression', 'recommendation', 'severity', 'status']
        extra_kwargs = {
            'findings': {'required': False, 'allow_blank': True},
            'impression': {'required': False, 'allow_blank': True},
            'recommendation': {'required': False, 'allow_blank': True},
            'severity': {'required': False},
        }

    def validate(self, attrs):
        status_val = attrs.get('status', 'DRAFT')

        if status_val == 'SUBMITTED':
            required_fields = ['findings', 'impression', 'recommendation', 'severity']
            # Check both attrs (incoming data) and instance (existing data for partial updates)
            missing = []
            for field in required_fields:
                value = attrs.get(field)
                if value is None and self.instance is not None:
                    value = getattr(self.instance, field, None)
                if not value:
                    missing.append(field)
            if missing:
                raise serializers.ValidationError({
                    field: "This field is required for final submission."
                    for field in missing
                })

        return attrs

    def update(self, instance, validated_data):
        status_val = validated_data.get('status', 'DRAFT')
        # If finalizing, set created_by from context (request.user)
        if status_val == 'SUBMITTED' and instance.status != 'SUBMITTED':
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                instance.created_by = request.user
        return super().update(instance, validated_data)
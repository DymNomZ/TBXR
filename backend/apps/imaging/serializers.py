import os
import pydicom
import numpy as np
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import XrayRecord, ProcessedImage


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
import uuid
from django.db import models
from django.conf import settings
from apps.patients.models import Patient

class XrayRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_REVIEW', 'In Review'),
        ('COMPLETED', 'Completed'),
    ]
    
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    raw_image = models.FileField(upload_to='raw/')
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_format = models.CharField(max_length=10)  # e.g., 'jpg', 'png', 'dcm'

    def __str__(self):
        return f"X-ray {self.transaction_id} for {self.patient}"

class ProcessedImage(models.Model):
    xray_record = models.OneToOneField(XrayRecord, on_delete=models.CASCADE)
    processed_image = models.ImageField(upload_to='xray_processed/')
    preprocessing_metadata = models.JSONField()

    def __str__(self):
        return f"Processed image for {self.xray_record}"

class Annotation(models.Model):
    xray_record   = models.ForeignKey(
        XrayRecord,
        on_delete=models.CASCADE,
        related_name='annotations',
    )
    radiologist   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='annotations',
    )
    bounding_boxes = models.JSONField(
        default=list,
        help_text='Array of {x, y, width, height, label} objects.'
    )
    notes          = models.TextField(blank=True, default='')
    submitted_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'Annotation for {self.xray_record.transaction_id} by {self.radiologist}'
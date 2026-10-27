import uuid
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.patients.models import Patient

class XrayRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_REVIEW', 'In Review'),
        ('AI_REVIEWED', 'AI Reviewed'),
        ('MANUAL_REVIEW', 'Manual Review Required'),
        ('COMPLETED', 'Completed'),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    raw_image = models.FileField(upload_to='raw/')
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_format = models.CharField(max_length=10)  # e.g., 'jpg', 'png', 'dcm'
    active_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_review_locks',
    )
    lock_timestamp = models.DateTimeField(null=True, blank=True)
    # Workflow status captured when a radiologist opens the case, so the lock can
    # be released (or expire) without leaving the record stuck on IN_REVIEW.
    status_before_review = models.CharField(max_length=20, null=True, blank=True)

    @property
    def review_lock_timeout_minutes(self):
        return getattr(settings, 'REVIEW_LOCK_TIMEOUT_MINUTES', 60)

    def lock_has_expired(self, now=None):
        if not self.lock_timestamp:
            return True
        if not self.active_reviewer:
            return True
        now = now or timezone.now()
        timeout = self.lock_timestamp + timedelta(minutes=self.review_lock_timeout_minutes)
        return now >= timeout

    def acquire_lock(self, reviewer, now=None):
        now = now or timezone.now()
        if self.active_reviewer_id == reviewer.pk:
            self.lock_timestamp = now
            self.save(update_fields=['lock_timestamp'])
            return True

        if not self.active_reviewer or self.lock_has_expired(now):
            self.active_reviewer = reviewer
            self.lock_timestamp = now
            self.save(update_fields=['active_reviewer', 'lock_timestamp'])
            return True

        return False

    def release_lock(self):
        """Clear the review lock and restore the pre-review workflow status.

        Idempotent: safe to call when no lock is held. Only the lock holder (or
        callers acting on their behalf, e.g. expiry cleanup) should invoke this.
        """
        update_fields = []

        if self.active_reviewer_id is not None:
            self.active_reviewer = None
            update_fields.append('active_reviewer')
        if self.lock_timestamp is not None:
            self.lock_timestamp = None
            update_fields.append('lock_timestamp')
        if self.status == 'IN_REVIEW':
            self.status = self.status_before_review or 'PENDING'
            update_fields.append('status')
        if self.status_before_review is not None:
            self.status_before_review = None
            update_fields.append('status_before_review')

        if update_fields:
            self.save(update_fields=update_fields)

    def start_review(self, reviewer, now=None):
        """Acquire the lock and move the record into IN_REVIEW.

        Remembers the prior workflow status so release/expiry can restore it.
        Returns True when the caller holds the lock after this call.
        """
        if not self.acquire_lock(reviewer, now):
            return False

        if self.status in {'PENDING', 'AI_REVIEWED', 'MANUAL_REVIEW'}:
            self.status_before_review = self.status
            self.status = 'IN_REVIEW'
            self.save(update_fields=['status', 'status_before_review'])

        return True

    def clear_if_expired(self, now=None):
        """Release a stale lock in place. Returns True when a lock was cleared."""
        if self.active_reviewer_id and self.lock_has_expired(now):
            self.release_lock()
            return True
        return False

    @classmethod
    def clear_expired_locks(cls, now=None):
        """Release every stale review lock and restore their workflow status.

        Called on queue reads so abandoned cases do not sit on IN_REVIEW until
        someone happens to open them.
        """
        now = now or timezone.now()
        timeout = now - timedelta(
            minutes=getattr(settings, 'REVIEW_LOCK_TIMEOUT_MINUTES', 60)
        )
        stale = cls.objects.filter(active_reviewer__isnull=False).filter(
            models.Q(lock_timestamp__isnull=True) | models.Q(lock_timestamp__lte=timeout)
        )
        for record in stale:
            record.clear_if_expired(now)

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


class AnnotationDraft(models.Model):
    xray_record = models.ForeignKey(
        XrayRecord,
        on_delete=models.CASCADE,
        related_name='annotation_drafts',
    )
    radiologist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annotation_drafts',
    )
    bounding_boxes = models.JSONField(default=list)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('xray_record', 'radiologist')]
        ordering = ['-updated_at']

    def __str__(self):
        return f'Draft annotation for {self.xray_record.transaction_id} by {self.radiologist}'
    
class AIResult(models.Model):
    class RiskLabel(models.TextChoices):
        LOW      = 'LOW',      'Low'
        MODERATE = 'MODERATE', 'Moderate'
        HIGH     = 'HIGH',     'High'

    xray_record    = models.OneToOneField(
        XrayRecord,
        on_delete=models.CASCADE,
        related_name='ai_result',
    )
    risk_score     = models.FloatField(
        help_text='TB probability between 0.0 and 1.0.'
    )
    risk_label     = models.CharField(
        max_length=10,
        choices=RiskLabel.choices,
    )
    heatmap_image  = models.ImageField(
        upload_to='heatmaps/',
        null=True,
        blank=True,
        help_text='Grad-CAM or equivalent saliency map.'
    )
    model_version  = models.CharField(
        max_length=64,
        help_text='e.g. mobilenetv3_v1',
    )
    generated_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'AIResult for {self.xray_record.transaction_id} — {self.risk_label} ({self.risk_score:.2f})'


class Report(models.Model):
    class SeverityChoices(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        MILD = 'MILD', 'Mild'
        MODERATE = 'MODERATE', 'Moderate'
        SEVERE = 'SEVERE', 'Severe'
        CRITICAL = 'CRITICAL', 'Critical'

    xray_record = models.OneToOneField(
        XrayRecord, on_delete=models.CASCADE, related_name='report'
    )
    findings = models.TextField(help_text="Detailed radiological findings")
    impression = models.TextField(help_text="Clinical impression/diagnosis")
    recommendation = models.TextField(help_text="Clinical recommendations")
    severity = models.CharField(
        max_length=20, choices=SeverityChoices.choices,
        help_text="Overall severity classification"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='reports_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20, 
        choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted')], 
        default='DRAFT'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report for {self.xray_record.transaction_id} — {self.severity}'


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    message = models.TextField()
    read_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Notification for {self.recipient} ({"read" if self.read_status else "unread"})'


class ProgressionStatus(models.Model):
    STATUS_CHOICES = [
        ('no_prior', 'No prior'),
        ('stable', 'Stable'),
        ('decreased_risk', 'Improvement'),
        ('increased_risk', 'Deterioration'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='progression_statuses',
    )
    xray_record = models.ForeignKey(
        XrayRecord,
        on_delete=models.CASCADE,
        related_name='progression_statuses',
    )
    previous_record = models.ForeignKey(
        XrayRecord,
        on_delete=models.SET_NULL,
        related_name='later_progression_statuses',
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='no_prior')
    score = models.FloatField(null=True, blank=True)
    previous_score = models.FloatField(null=True, blank=True)
    delta = models.FloatField(null=True, blank=True)
    abs_delta = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(default=0.05)
    comparison_available = models.BooleanField(default=False)
    reason = models.CharField(max_length=64, blank=True, default='')
    source = models.CharField(max_length=32, default='ai')
    clinical_note = models.TextField(blank=True, default='')
    is_overridden = models.BooleanField(default=False)
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='progression_overrides',
    )
    override_timestamp = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['xray_record__upload_timestamp', 'xray_record__pk']

    def __str__(self):
        return f'ProgressionStatus for {self.xray_record.transaction_id}: {self.status}'


class ProgressionOverrideAuditLog(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='progression_override_audit_logs',
    )
    xray_record = models.ForeignKey(
        XrayRecord,
        on_delete=models.CASCADE,
        related_name='progression_override_audit_logs',
    )
    radiologist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='progression_override_audit_logs',
    )
    previous_status = models.CharField(max_length=32, blank=True, default='')
    new_status = models.CharField(max_length=32, blank=True, default='')
    clinical_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Progression override on {self.xray_record.transaction_id} by {self.radiologist}'
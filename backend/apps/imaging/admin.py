from django.contrib import admin
from .models import Annotation, XrayRecord, ProcessedImage, AIResult

admin.site.register(XrayRecord)
admin.site.register(ProcessedImage)
admin.site.register(Annotation)

@admin.register(AIResult)
class AIResultAdmin(admin.ModelAdmin):
    list_display    = ('xray_record', 'risk_label', 'risk_score', 'model_version', 'generated_at')
    list_filter     = ('risk_label', 'model_version')
    readonly_fields = ('generated_at',)
    search_fields   = ('xray_record__transaction_id',)
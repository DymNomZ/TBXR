from django.contrib import admin
from .models import XrayRecord, ProcessedImage

admin.site.register(XrayRecord)
admin.site.register(ProcessedImage)
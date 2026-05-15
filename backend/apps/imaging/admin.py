from django.contrib import admin
from .models import Annotation, XrayRecord, ProcessedImage

admin.site.register(XrayRecord)
admin.site.register(ProcessedImage)
admin.site.register(Annotation)
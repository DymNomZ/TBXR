from django.urls import path

from . import views

app_name = 'imaging'

urlpatterns = [
    path(
        "patients/<int:patient_id>/xray/upload/",
        views.upload_xray,
        name="upload_xray",
    ),
    path(
        "patients/<int:patient_id>/xray/upload/confirm/<uuid:transaction_id>/",
        views.upload_confirm,
        name="upload_confirm",
    ),
]
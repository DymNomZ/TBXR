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
    path(
        "xray/<uuid:transaction_id>/annotate/",
        views.annotate_xray,
        name="annotate_xray",
    ),
    path(
        "xray/<uuid:transaction_id>/analyse/",
        views.analyse_xray,
        name="analyse_xray",
    ),
    path(
        "patients/<int:patient_id>/xray/",
        views.patient_xrays,
        name="patient_xrays",
    ),
    path(
        "patients/<int:patient_id>/history/",
        views.patient_history,
        name="patient_history",
    ),
    path(
        "cases/<str:case_id>/progression/",
        views.case_progression_history,
        name="case_progression_history",
    ),
    path(
        "cases/<str:case_id>/progression/override/",
        views.case_progression_override,
        name="case_progression_override",
    ),
    path(
        "patients/<int:patient_id>/progression/",
        views.patient_progression_history,
        name="patient_progression_history",
    ),
    path(
        "dashboard/technologist/",
        views.technologist_dashboard,
        name="technologist_dashboard",
    ),
    path(
        "physician/dashboard/",
        views.physician_dashboard,
        name="physician_dashboard",
    ),
    path("queue/", views.radiologist_queue, name="radiologist-queue"),
    path("xray/<str:transaction_id>/", views.xray_detail, name="xray-detail"),
    path(
        "xray/<uuid:transaction_id>/report/",
        views.report_detail,
        name="report_detail",
    ),
    path(
        "xray/<uuid:transaction_id>/report/generate/",
        views.generate_report,
        name="generate_report",
    ),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:notification_id>/mark-read/", views.notification_mark_read, name="notification_mark_read"),
    path("analytics/summary/", views.analytics_summary, name="analytics_summary"),
]
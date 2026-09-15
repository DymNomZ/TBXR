from __future__ import annotations

"""
Seed a clean SUS dataset.

What this script creates:
- 1 RADIOLOGIC_TECH user
- 1 RADIOLOGIST user
- 1 PHYSICIAN user
- 5 patients
- 2 X-ray records for physician dashboard walkthrough
- 1 submitted report and 1 pending physician notification

Run from the backend folder:

    python scripts/seed_sus_dataset.py
"""

import os
import sys
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TBXR.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import transaction
from PIL import Image

from apps.accounts.enums import UserRole
from apps.imaging.models import AIResult, Notification, ProcessedImage, Report, XrayRecord
from apps.patients.models import Patient

SEED_PASSWORD = os.environ.get("SEED_DEFAULT_PASSWORD", "seed-password-change-me")

USER_FIXTURES = [
    {
        "username": "tech1",
        "password": SEED_PASSWORD,
        "role": UserRole.RADIOLOGIC_TECH,
        "email": "tech1@example.com",
    },
    {
        "username": "rad1",
        "password": SEED_PASSWORD,
        "role": UserRole.RADIOLOGIST,
        "email": "rad1@example.com",
    },
    {
        "username": "physician1",
        "password": SEED_PASSWORD,
        "role": UserRole.PHYSICIAN,
        "email": "physician1@example.com",
    },
]

FINALIZED_TX_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
MANUAL_REVIEW_TX_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")

PATIENT_FIXTURES = [
    {
        "first_name": "Juan",
        "last_name": "Dela Cruz",
        "date_of_birth": date(1990, 1, 1),
        "sex": "M",
        "contact_number": "09170000001",
    },
    {
        "first_name": "Maria",
        "last_name": "Santos",
        "date_of_birth": date(1991, 2, 2),
        "sex": "F",
        "contact_number": "09170000002",
    },
    {
        "first_name": "Jose",
        "last_name": "Reyes",
        "date_of_birth": date(1988, 3, 3),
        "sex": "M",
        "contact_number": "09170000003",
    },
    {
        "first_name": "Anna",
        "last_name": "Cruz",
        "date_of_birth": date(1992, 4, 4),
        "sex": "F",
        "contact_number": "09170000004",
    },
    {
        "first_name": "Luis",
        "last_name": "Garcia",
        "date_of_birth": date(1987, 5, 5),
        "sex": "M",
        "contact_number": "09170000005",
    },
]


def seed_user(username: str, password: str, role: str, email: str = ""):
    user_model = get_user_model()
    user, created = user_model.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "role": role,
        },
    )
    user.email = email
    user.role = role
    user.set_password(password)
    user.save()
    return user, created


def seed_patient(payload: dict):
    patient, created = Patient.objects.update_or_create(
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        date_of_birth=payload["date_of_birth"],
        defaults={
            "sex": payload["sex"],
            "contact_number": payload["contact_number"],
        },
    )
    return patient, created


def build_png_bytes(color=(255, 255, 255)):
    image = Image.new("RGB", (1, 1), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def seed_physician_cases(technologist, radiologist, physician, patients):
    finalized_patient = patients[0][0]
    manual_review_patient = patients[1][0]

    finalized_xray, _ = XrayRecord.objects.update_or_create(
        transaction_id=FINALIZED_TX_ID,
        defaults={
            "patient": finalized_patient,
            "uploader": technologist,
            "file_format": "png",
            "status": "COMPLETED",
        },
    )
    if not finalized_xray.raw_image:
        finalized_xray.raw_image.save(
            f"sus_{FINALIZED_TX_ID.hex}.png",
            ContentFile(build_png_bytes((235, 235, 235))),
            save=True,
        )

    processed_image, _ = ProcessedImage.objects.update_or_create(
        xray_record=finalized_xray,
        defaults={
            "preprocessing_metadata": {
                "seeded": True,
                "source": "backend/scripts/seed_sus_dataset.py",
            }
        },
    )
    if not processed_image.processed_image:
        processed_image.processed_image.save(
            f"sus_{FINALIZED_TX_ID.hex}_processed.png",
            ContentFile(build_png_bytes((220, 220, 220))),
            save=True,
        )

    AIResult.objects.update_or_create(
        xray_record=finalized_xray,
        defaults={
            "risk_score": 0.66,
            "risk_label": AIResult.RiskLabel.MODERATE,
            "model_version": "sus-demo-v1",
        },
    )

    Report.objects.update_or_create(
        xray_record=finalized_xray,
        defaults={
            "findings": "Patchy upper lobe infiltrates.",
            "impression": "Suspicious for pulmonary tuberculosis.",
            "recommendation": "Correlate with microbiologic tests.",
            "severity": Report.SeverityChoices.MODERATE,
            "status": "SUBMITTED",
            "created_by": radiologist,
        },
    )

    manual_review_xray, _ = XrayRecord.objects.update_or_create(
        transaction_id=MANUAL_REVIEW_TX_ID,
        defaults={
            "patient": manual_review_patient,
            "uploader": technologist,
            "file_format": "png",
            "status": "MANUAL_REVIEW",
        },
    )
    if not manual_review_xray.raw_image:
        manual_review_xray.raw_image.save(
            f"sus_{MANUAL_REVIEW_TX_ID.hex}.png",
            ContentFile(build_png_bytes((245, 245, 245))),
            save=True,
        )

    Notification.objects.update_or_create(
        recipient=physician,
        message=f"Report ready for {finalized_patient.first_name} {finalized_patient.last_name} (case {FINALIZED_TX_ID}).",
        defaults={"read_status": False},
    )

    return finalized_xray, manual_review_xray


def seed_sus_dataset():
    call_command("migrate", interactive=False, verbosity=0)

    with transaction.atomic():
        seeded_users = [seed_user(**fixture) for fixture in USER_FIXTURES]
        seeded_patients = [seed_patient(fixture) for fixture in PATIENT_FIXTURES]

        user_by_role = {user.role: user for user, _ in seeded_users}
        seeded_cases = seed_physician_cases(
            technologist=user_by_role[UserRole.RADIOLOGIC_TECH],
            radiologist=user_by_role[UserRole.RADIOLOGIST],
            physician=user_by_role[UserRole.PHYSICIAN],
            patients=seeded_patients,
        )

    return {
        "users": seeded_users,
        "patients": seeded_patients,
        "cases": seeded_cases,
    }


def main():
    result = seed_sus_dataset()

    print("Seeded users:")
    for user, created in result["users"]:
        status = "created" if created else "updated"
        print(f"- {user.username} ({user.role}) [{status}]")

    print("Seeded patients:")
    for patient, created in result["patients"]:
        status = "created" if created else "updated"
        print(f"- {patient} [{status}]")

    finalized_case, manual_case = result["cases"]
    print("Seeded physician demo cases:")
    print(f"- Finalized case: {finalized_case.transaction_id} [{finalized_case.status}]")
    print(f"- Manual-review case: {manual_case.transaction_id} [{manual_case.status}]")


if __name__ == "__main__":
    main()
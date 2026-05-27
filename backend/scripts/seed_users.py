from __future__ import annotations

"""
Seed demo users and sample records.

Test credentials:
- tech1 / demo123 -> RADIOLOGIC_TECH
- rad1 / demo123 -> RADIOLOGIST
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
from django.db import transaction
from PIL import Image

from apps.accounts.enums import UserRole
from apps.imaging.models import ProcessedImage, XrayRecord
from apps.patients.models import Patient

SEED_PASSWORD = "demo123"
SEED_XRAY_TRANSACTION_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

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
]

PATIENT_FIXTURE = {
    "first_name": "Sample",
    "last_name": "Patient",
    "date_of_birth": date(1980, 1, 1),
    "sex": "M",
    "contact_number": "09170000000",
}

PROCESSING_METADATA = {
    "seeded": True,
    "source": "backend/scripts/seed_users.py",
}


def build_png_bytes(color: tuple[int, int, int] = (255, 255, 255)) -> bytes:
    image = Image.new("RGB", (1, 1), color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def seed_user(username: str, password: str, role: str, email: str = ""):
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(
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
    return user


def seed_sample_records(technologist_user):
    patient, _ = Patient.objects.update_or_create(
        first_name=PATIENT_FIXTURE["first_name"],
        last_name=PATIENT_FIXTURE["last_name"],
        date_of_birth=PATIENT_FIXTURE["date_of_birth"],
        defaults={
            "sex": PATIENT_FIXTURE["sex"],
            "contact_number": PATIENT_FIXTURE["contact_number"],
        },
    )

    xray, _ = XrayRecord.objects.update_or_create(
        transaction_id=SEED_XRAY_TRANSACTION_ID,
        defaults={
            "patient": patient,
            "uploader": technologist_user,
            "file_format": "png",
            "status": "PENDING",
        },
    )

    if not xray.raw_image:
        xray.raw_image.save(
            f"seed_{SEED_XRAY_TRANSACTION_ID.hex}.png",
            ContentFile(build_png_bytes()),
            save=True,
        )
    else:
        xray.patient = patient
        xray.uploader = technologist_user
        xray.file_format = "png"
        xray.status = "PENDING"
        xray.save(update_fields=["patient", "uploader", "file_format", "status"])

    processed_image, _ = ProcessedImage.objects.update_or_create(
        xray_record=xray,
        defaults={
            "preprocessing_metadata": PROCESSING_METADATA,
        },
    )

    if not processed_image.processed_image:
        processed_image.processed_image.save(
            f"seed_{SEED_XRAY_TRANSACTION_ID.hex}_processed.png",
            ContentFile(build_png_bytes()),
            save=True,
        )
    else:
        processed_image.preprocessing_metadata = PROCESSING_METADATA
        processed_image.save(update_fields=["preprocessing_metadata"])

    return patient, xray, processed_image


def seed_all(include_sample_records: bool = True):
    with transaction.atomic():
        seeded_users = {
            fixture["role"]: seed_user(
                username=fixture["username"],
                password=fixture["password"],
                role=fixture["role"],
                email=fixture["email"],
            )
            for fixture in USER_FIXTURES
        }

        seeded_sample = None
        if include_sample_records:
            seeded_sample = seed_sample_records(seeded_users[UserRole.RADIOLOGIC_TECH])

    return {
        "users": seeded_users,
        "sample": seeded_sample,
    }


def main():
    result = seed_all(include_sample_records=True)

    print("Seeded users:")
    for role, user in result["users"].items():
        print(f"- {user.username} ({role})")

    if result["sample"]:
        patient, xray, processed_image = result["sample"]
        print("Seeded sample records:")
        print(f"- Patient: {patient}")
        print(f"- XrayRecord: {xray}")
        print(f"- ProcessedImage: {processed_image}")


if __name__ == "__main__":
    main()
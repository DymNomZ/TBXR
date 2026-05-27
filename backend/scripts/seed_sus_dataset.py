from __future__ import annotations

"""
Seed a clean SUS dataset.

What this script creates:
- 1 RADIOLOGIC_TECH user
- 1 RADIOLOGIST user
- 5 patients

What this script does not create:
- X-ray records
- processed images
- AI results
- annotations

Those remain part of the manual SUS walkthrough so test participants can
upload images and drive the workflow themselves.

Run from the backend folder:

    python scripts/seed_sus_dataset.py
"""

import os
import sys
from datetime import date
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
from django.db import transaction

from apps.accounts.enums import UserRole
from apps.patients.models import Patient

SEED_PASSWORD = "demo123"

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


def seed_sus_dataset():
    with transaction.atomic():
        seeded_users = [seed_user(**fixture) for fixture in USER_FIXTURES]
        seeded_patients = [seed_patient(fixture) for fixture in PATIENT_FIXTURES]

    return {
        "users": seeded_users,
        "patients": seeded_patients,
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


if __name__ == "__main__":
    main()
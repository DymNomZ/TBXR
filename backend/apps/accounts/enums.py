from django.db import models

class UserRole(models.TextChoices):
    RADIOLOGIC_TECH = 'RADIOLOGIC_TECH', 'Radiologic Technologist'
    RADIOLOGIST = 'RADIOLOGIST', 'Radiologist'
    PHYSICIAN = 'PHYSICIAN', 'Physician'
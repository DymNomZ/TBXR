from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('RADIOLOGIC_TECH', 'Radiologic Technologist'),
        ('RADIOLOGIST', 'Radiologist'),
        ('PHYSICIAN', 'Physician'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='RADIOLOGIC_TECH',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

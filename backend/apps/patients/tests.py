import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.accounts.enums import UserRole

class PatientViewsTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        # Create users for different roles
        self.tech = self.user_model.objects.create_user(
            username='tech_test', password='password123', role=UserRole.RADIOLOGIC_TECH
        )
        self.rad = self.user_model.objects.create_user(
            username='rad_test', password='password123', role=UserRole.RADIOLOGIST
        )
        self.phys = self.user_model.objects.create_user(
            username='phys_test', password='password123', role=UserRole.PHYSICIAN
        )
        
        self.valid_payload = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "sex": "M",
            "contact_number": "09171234567",
        }

    def test_register_patient_success(self):
        """Test successful patient creation with valid data by a Technologist."""
        self.client.force_login(self.tech)
        
        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        
        # 1. Check status code
        self.assertEqual(response.status_code, 201)
        
        # 2. Check response data
        data = response.json()
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        
        # 3. Check the 'Location' header (as seen in views.py)
        # The view uses reverse('patients:detail', kwargs={'patient_id': ...})
        self.assertIn('Location', response)
        self.assertIn('/api/patients/', response['Location'])

    def test_register_patient_missing_fields(self):
        """Test rejection when required fields are missing."""
        self.client.force_login(self.tech)
        
        # Create payload missing 'first_name'
        invalid_payload = self.valid_payload.copy()
        del invalid_payload['first_name']
        
        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(invalid_payload),
            content_type='application/json',
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json())

    def test_register_patient_invalid_formats(self):
        """Test rejection on invalid field formats (e.g., bad date)."""
        self.client.force_login(self.tech)
        
        # Create payload with invalid date format
        invalid_payload = self.valid_payload.copy()
        invalid_payload['date_of_birth'] = 'not-a-date'
        
        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(invalid_payload),
            content_type='application/json',
        )
        
        self.assertEqual(response.status_code, 400)

    def test_register_patient_unauthorized_role(self):
        """Test that Radiologists and Physicians are forbidden from registering patients."""
        # Test for Radiologist
        self.client.force_login(self.rad)
        response_rad = self.client.post(
            reverse('patients:register'),
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertEqual(response_rad.status_code, 403)

        # Test for Physician
        self.client.force_login(self.phys)
        response_phys = self.client.post(
            reverse('patients:register'),
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertEqual(response_phys.status_code, 403)
import json
import re
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.accounts.enums import UserRole
from apps.patients.models import Patient

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
        """Test that Radiologists are forbidden from registering patients."""
        # Test for Radiologist
        self.client.force_login(self.rad)
        response_rad = self.client.post(
            reverse('patients:register'),
            data=json.dumps(self.valid_payload),
            content_type='application/json',
        )
        self.assertEqual(response_rad.status_code, 403)

    def test_register_patient_accepts_flexible_contact_input(self):
        """Phone values are normalized and returned in international display format."""
        self.client.force_login(self.tech)

        payload = self.valid_payload.copy()
        payload["contact_number"] = "0911 222 3333"

        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        display_value = response.json()["contact_number"]
        self.assertEqual(display_value, "+63 911 222 3333")

        patient = Patient.objects.get(first_name="John", last_name="Doe")
        self.assertEqual(patient.contact_number, "+639112223333")

    def test_register_patient_rejects_invalid_contact_input(self):
        self.client.force_login(self.tech)

        payload = self.valid_payload.copy()
        payload["contact_number"] = "123"

        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("contact_number", response.json().get("errors", {}))

    def test_register_patient_accepts_local_number_with_selected_country(self):
        self.client.force_login(self.tech)

        payload = self.valid_payload.copy()
        payload["country_code"] = "US"
        payload["contact_number"] = "2025550143"

        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["contact_number"].startswith("+1 "))

        patient = Patient.objects.get(first_name="John", last_name="Doe")
        self.assertEqual(patient.country_code, "US")
        self.assertEqual(patient.contact_number, "+12025550143")

    def test_register_patient_rejects_invalid_country_code(self):
        self.client.force_login(self.tech)

        payload = self.valid_payload.copy()
        payload["country_code"] = "XYZ"

        response = self.client.post(
            reverse('patients:register'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("country_code", response.json().get("errors", {}))

    def test_search_patients_by_name(self):
        """Search matches first or last name, case-insensitively."""
        self.client.force_login(self.tech)
        Patient.objects.create(
            first_name='Alice', last_name='Smith',
            date_of_birth='1990-01-01', sex='F', contact_number='1',
        )
        Patient.objects.create(
            first_name='Bob', last_name='Jones',
            date_of_birth='1990-01-01', sex='M', contact_number='2',
        )

        response = self.client.get(reverse('patients:search'), {'name': 'smi'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['last_name'], 'Smith')
        # Legacy values are still rendered safely if they are not parseable.
        self.assertTrue(re.match(r"^(\+|\d)", data[0]['contact_number']))

    def test_search_patients_by_patient_id(self):
        """A numeric query also matches the patient ID."""
        self.client.force_login(self.tech)
        patient = Patient.objects.create(
            first_name='Ida', last_name='Number',
            date_of_birth='1990-01-01', sex='F', contact_number='3',
        )

        response = self.client.get(
            reverse('patients:search'), {'name': str(patient.patient_id)}
        )

        self.assertEqual(response.status_code, 200)
        ids = [row['patient_id'] for row in response.json()]
        self.assertIn(patient.patient_id, ids)

    def test_search_patients_no_match_returns_empty_list(self):
        """A non-existent name returns HTTP 200 with an empty array."""
        self.client.force_login(self.tech)

        response = self.client.get(reverse('patients:search'), {'name': 'NoSuchNameXYZ'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_physician_can_view_patient_detail_for_read_only_follow_up(self):
        """Physicians should be able to open patient records from finalized-case follow-up."""
        physician = self.user_model.objects.create_user(
            username='physician_test', password='password123', role=UserRole.PHYSICIAN
        )
        patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            date_of_birth='1985-02-15',
            sex='F',
            contact_number='09181234567',
        )

        self.client.force_login(physician)
        response = self.client.get(reverse('patients:detail', kwargs={'patient_id': patient.patient_id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['patient_id'], patient.patient_id)
        self.assertEqual(response.json()['contact_number'], '+63 918 123 4567')
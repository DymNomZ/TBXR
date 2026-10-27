import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from apps.accounts.enums import UserRole

from . import views


class AccountAuthViewsTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def _create_user(self, username, password, role):
        return self.user_model.objects.create_user(
            username=username,
            password=password,
            role=role,
        )

    def test_login_redirects_radiologic_tech_to_technologist_dashboard(self):
        self._create_user('tech', 'password123', UserRole.RADIOLOGIC_TECH)
        expected_redirect = views.ROLE_FRONTEND_URLS[UserRole.RADIOLOGIC_TECH]

        response = self.client.post(
            reverse('accounts:login'),
            data=json.dumps({'username': 'tech', 'password': 'password123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'redirect': expected_redirect, 'role': UserRole.RADIOLOGIC_TECH},
        )
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_redirects_radiologist_to_radiologist_dashboard(self):
        self._create_user('rad', 'password123', UserRole.RADIOLOGIST)
        expected_redirect = views.ROLE_FRONTEND_URLS[UserRole.RADIOLOGIST]

        response = self.client.post(
            reverse('accounts:login'),
            data=json.dumps({'username': 'rad', 'password': 'password123'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'redirect': expected_redirect, 'role': UserRole.RADIOLOGIST},
        )

    def test_login_redirects_patient_to_patient_dashboard(self):
        self._create_user('patient1', 'password123', UserRole.PATIENT)
        expected_redirect = views.ROLE_FRONTEND_URLS[UserRole.PATIENT]

        response = self.client.post(
            reverse('accounts:login'),
            data=json.dumps({'username': 'patient1', 'password': 'password123'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'redirect': expected_redirect, 'role': UserRole.PATIENT},
        )

    def test_login_returns_descriptive_error_for_bad_credentials(self):
        self._create_user('tech', 'password123', UserRole.RADIOLOGIC_TECH)

        response = self.client.post(
            reverse('accounts:login'),
            data=json.dumps({'username': 'tech', 'password': 'wrong'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(response.content, {'error': 'Invalid username or password.'})

    def test_logout_clears_session_and_redirects_to_login_page(self):
        self._create_user('tech', 'password123', UserRole.RADIOLOGIC_TECH)
        self.client.login(username='tech', password='password123')

        response = self.client.post(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'detail': 'Logged out.'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_dashboard_placeholder_is_available_for_matching_role(self):
        self._create_user('tech', 'password123', UserRole.RADIOLOGIC_TECH)
        request = RequestFactory().get('/dashboard/technologist')
        request.user = self.user_model.objects.get(username='tech')

        response = views.technologist_dashboard(request)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Technologist Dashboard')

class RolePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tech = user_model.objects.create_user(
            username='tech1', password='password123', role=UserRole.RADIOLOGIC_TECH
        )
        cls.rad = user_model.objects.create_user(
            username='rad1', password='password123', role=UserRole.RADIOLOGIST
        )
        cls.respondent = user_model.objects.create_user(
            username='respondent1', password='password123', role=UserRole.PATIENT
        )
        cls.rfactory = RequestFactory()

    def _request_for_user(self, path, user):
        request = self.rfactory.get(path)
        request.user = user
        return request

    def test_unauthenticated_user_is_redirected_to_login(self):
        request = self._request_for_user('/dashboard/technologist', AnonymousUser())
        response = views.technologist_dashboard(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_authenticated_user_with_correct_role_can_access_view(self):
        response = views.technologist_dashboard(
            self._request_for_user('/dashboard/technologist', self.tech)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Technologist Dashboard')

    def test_authenticated_user_with_wrong_role_receives_403(self):
        with self.assertRaises(PermissionDenied):
            views.technologist_dashboard(self._request_for_user('/dashboard/technologist', self.rad))

    def test_patient_role_is_forbidden_from_technologist_dashboard(self):
        with self.assertRaises(PermissionDenied):
            views.technologist_dashboard(self._request_for_user('/dashboard/technologist', self.respondent))

    def test_register_patient_allows_technologist(self):
        self.client.force_login(self.tech)
        response = self.client.post(
            reverse("patients:register"),
            data=json.dumps(
                {
                    "first_name": "Test",
                    "last_name": "Patient",
                    "date_of_birth": "1990-01-01",
                    "sex": "M",
                    "contact_number": "09171234567",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_register_patient_is_inaccessible_to_radiologist(self):
        self.client.force_login(self.rad)
        response = self.client.post(
            reverse("patients:register"),
            data=json.dumps(
                {
                    "first_name": "Test",
                    "last_name": "Patient",
                    "date_of_birth": "1990-01-01",
                    "sex": "M",
                    "contact_number": "09171234567",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


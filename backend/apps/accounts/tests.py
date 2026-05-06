import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
		self._create_user('tech', 'password123', 'RADIOLOGIC_TECH')

		response = self.client.post(
			reverse('accounts:login'),
			data=json.dumps({'username': 'tech', 'password': 'password123'}),
			content_type='application/json',
		)

		self.assertRedirects(
			response,
			reverse('accounts:technologist-dashboard'),
			fetch_redirect_response=False,
		)
		self.assertIn('_auth_user_id', self.client.session)

	def test_login_redirects_radiologist_to_radiologist_dashboard(self):
		self._create_user('rad', 'password123', 'RADIOLOGIST')

		response = self.client.post(
			reverse('accounts:login'),
			data=json.dumps({'username': 'rad', 'password': 'password123'}),
			content_type='application/json',
		)

		self.assertRedirects(
			response,
			reverse('accounts:radiologist-dashboard'),
			fetch_redirect_response=False,
		)

	def test_login_redirects_physician_to_physician_dashboard(self):
		self._create_user('phys', 'password123', 'PHYSICIAN')

		response = self.client.post(
			reverse('accounts:login'),
			data=json.dumps({'username': 'phys', 'password': 'password123'}),
			content_type='application/json',
		)

		self.assertRedirects(
			response,
			reverse('accounts:physician-dashboard'),
			fetch_redirect_response=False,
		)

	def test_login_returns_descriptive_error_for_bad_credentials(self):
		self._create_user('tech', 'password123', 'RADIOLOGIC_TECH')

		response = self.client.post(
			reverse('accounts:login'),
			data=json.dumps({'username': 'tech', 'password': 'wrong'}),
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 401)
		self.assertJSONEqual(response.content, {'error': 'Invalid username or password.'})

	def test_logout_clears_session_and_redirects_to_login_page(self):
		self._create_user('tech', 'password123', 'RADIOLOGIC_TECH')
		self.client.login(username='tech', password='password123')

		response = self.client.get(reverse('accounts:logout'))

		self.assertRedirects(response, '/login', fetch_redirect_response=False)
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_dashboard_placeholder_is_available_for_matching_role(self):
		self._create_user('tech', 'password123', 'RADIOLOGIC_TECH')
		self.client.login(username='tech', password='password123')

		response = self.client.get(reverse('accounts:technologist-dashboard'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Technologist Dashboard')

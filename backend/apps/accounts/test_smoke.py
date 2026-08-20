from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.enums import UserRole


class LogoutSmokeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="smoke-tech",
            password="password123",
            role=UserRole.RADIOLOGIC_TECH,
        )
        self.url = reverse("accounts:logout")

    def test_post_logout_returns_200_and_clears_session(self):
        self.client.force_login(self.user)
        self.assertIn("_auth_user_id", self.client.session)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"detail": "Logged out."})
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_get_logout_returns_405(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

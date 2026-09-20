from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth-register")
        self.login_url = reverse("auth-login")
        self.me_url = reverse("auth-me")
        self.user_email = "architect@example.com"
        self.user_password = "SecurePassword@123"
        self.user = User.objects.create_user(
            email=self.user_email,
            password=self.user_password,
            full_name="Lead Architect",
        )

    def test_user_registration_success(self):
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPassword!2026",
            "password_confirm": "StrongPassword!2026",
            "full_name": "New Developer",
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], payload["email"])
        self.assertNotIn("password", response.data)

    def test_user_registration_password_mismatch(self):
        payload = {
            "email": "mismatch@example.com",
            "password": "StrongPassword!2026",
            "password_confirm": "DifferentPassword!2026",
            "full_name": "Test User",
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_jwt_login_success(self):
        payload = {
            "email": self.user_email,
            "password": self.user_password,
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], self.user_email)

    def test_jwt_login_invalid_credentials(self):
        payload = {
            "email": self.user_email,
            "password": "WrongPassword123",
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    def test_get_current_user_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user_email)

    def test_get_current_user_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
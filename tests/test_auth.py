import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
class TestAuthenticationEndpoints:

    def setup_method(self):
        self.client = APIClient()
        self.email = "tenant_admin@example.com"
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            email=self.email,
            password=self.password
        )

    def test_login_success_returns_jwt_tokens(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.email, "password": self.password},
            format="json"
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_failure_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.email, "password": "WrongPassword!"},
            format="json"
        )
        assert response.status_code in [400, 401]

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/api/projects/")
        assert response.status_code == 401
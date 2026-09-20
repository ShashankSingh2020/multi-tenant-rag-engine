import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.organizations.models import Organization
from apps.projects.models import Project

User = get_user_model()

@pytest.mark.django_db
class TestTenantDataIsolation:

    def setup_method(self):
        self.client_a = APIClient()
        self.client_b = APIClient()

        # Create Tenant A & User A with unique slug
        self.org_a = Organization.objects.create(name="Organization Alpha", slug="org-alpha")
        self.user_a = User.objects.create_user(
            email="alice@alpha.com",
            password="Password123!"
        )
        if hasattr(self.user_a, 'organization'):
            self.user_a.organization = self.org_a
            self.user_a.save()

        # Create Tenant B & User B with unique slug
        self.org_b = Organization.objects.create(name="Organization Beta", slug="org-beta")
        self.user_b = User.objects.create_user(
            email="bob@beta.com",
            password="Password123!"
        )
        if hasattr(self.user_b, 'organization'):
            self.user_b.organization = self.org_b
            self.user_b.save()

        # Authenticate Client A
        res_a = self.client_a.post("/api/auth/login/", {"email": "alice@alpha.com", "password": "Password123!"}, format="json")
        self.token_a = res_a.data.get("access")
        self.client_a.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # Authenticate Client B
        res_b = self.client_b.post("/api/auth/login/", {"email": "bob@beta.com", "password": "Password123!"}, format="json")
        self.token_b = res_b.data.get("access")
        self.client_b.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")

        # Create Project owned strictly by Tenant A
        self.project_a = Project.objects.create(
            name="Confidential Project Alpha",
            organization=self.org_a
        )

    def test_tenant_b_cannot_list_tenant_a_projects(self):
        """Ensure Tenant B's GET request only yields their own items."""
        response = self.client_b.get("/api/projects/")
        assert response.status_code == 200
        project_ids = [item["id"] for item in response.data] if isinstance(response.data, list) else [item["id"] for item in response.data.get("results", [])]
        assert str(self.project_a.id) not in [str(pid) for pid in project_ids]

    def test_tenant_b_cannot_access_tenant_a_project_detail(self):
        """Ensure direct IDOR attempt by Tenant B returns 404 or 403."""
        response = self.client_b.get(f"/api/projects/{self.project_a.id}/")
        assert response.status_code in [403, 404]

    def test_tenant_b_cannot_delete_tenant_a_project(self):
        """Ensure Tenant B cannot tamper with or delete Tenant A resources."""
        response = self.client_b.delete(f"/api/projects/{self.project_a.id}/")
        assert response.status_code in [403, 404]
        assert Project.objects.filter(id=self.project_a.id).exists()
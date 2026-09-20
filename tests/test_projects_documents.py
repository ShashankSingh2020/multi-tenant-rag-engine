from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import Organization, Membership
from apps.projects.models import Project
from apps.documents.models import Document
from apps.subscriptions.models import Subscription, SubscriptionPlan


class ProjectsAndDocumentsTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create Tenant Alpha
        self.org_a = Organization.objects.create(name="Tenant Alpha", slug="tenant-alpha")
        self.user_a = User.objects.create_user(
            email="alice@alpha.com",
            password="Password123!"
        )
        Membership.objects.create(
            organization=self.org_a,
            user=self.user_a,
            role="OWNER"
        )
        if hasattr(self.user_a, "organization"):
            self.user_a.organization = self.org_a
            self.user_a.save()

        # Create Tenant Beta
        self.org_b = Organization.objects.create(name="Tenant Beta", slug="tenant-beta")
        self.user_b = User.objects.create_user(
            email="bob@beta.com",
            password="Password123!"
        )
        Membership.objects.create(
            organization=self.org_b,
            user=self.user_b,
            role="OWNER"
        )
        if hasattr(self.user_b, "organization"):
            self.user_b.organization = self.org_b
            self.user_b.save()

        # Retrieve or dynamically initialize subscription plan matching existing model fields
        plan_fields = [f.name for f in SubscriptionPlan._meta.fields]
        plan_kwargs = {}
        if "name" in plan_fields:
            plan_kwargs["name"] = "Starter"
        if "max_documents" in plan_fields:
            plan_kwargs["max_documents"] = 2
        if "max_ai_requests_per_month" in plan_fields:
            plan_kwargs["max_ai_requests_per_month"] = 500
        if "price" in plan_fields:
            plan_kwargs["price"] = 19
        elif "price_monthly" in plan_fields:
            plan_kwargs["price_monthly"] = 19

        self.plan, _ = SubscriptionPlan.objects.get_or_create(**plan_kwargs)

        Subscription.objects.create(
            organization=self.org_a,
            plan=self.plan,
            is_active=True
        )

    def test_create_and_isolate_project(self):
        self.client.force_authenticate(user=self.user_a)
        
        # Provide organization context both in headers and body
        payload = {
            "name": "Alpha Alpha Project",
            "organization": str(self.org_a.id),
            "organization_id": str(self.org_a.id),
        }
        res = self.client.post(
            "/api/projects/",
            payload,
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
        )
        
        # If payload rejected extraneous keys, fall back to minimal payload
        if res.status_code == 400:
            res = self.client.post(
                "/api/projects/",
                {"name": "Alpha Alpha Project"},
                format="json",
                HTTP_X_ORGANIZATION_ID=str(self.org_a.id),
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        project_id = res.data["id"]

        # Tenant Beta cannot access Alpha's project
        self.client.force_authenticate(user=self.user_b)
        res_b = self.client.get(
            f"/api/projects/{project_id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org_b.id),
        )
        self.assertIn(res_b.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_document_upload_success_and_usage_increment(self):
        self.client.force_authenticate(user=self.user_a)
        project = Project.objects.create(organization=self.org_a, name="Default Docs")

        file_content = b"This is a test documentation file content."
        uploaded_file = SimpleUploadedFile("guide.txt", file_content, content_type="text/plain")

        upload_url = reverse("document-list-create", kwargs={"project_id": project.id})
        res = self.client.post(
            upload_url,
            {"title": "Getting Started Guide", "file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Document.objects.filter(project=project, title="Getting Started Guide").exists())

    def test_document_upload_invalid_extension_rejected(self):
        self.client.force_authenticate(user=self.user_a)
        project = Project.objects.create(organization=self.org_a, name="Security Test Docs")

        uploaded_file = SimpleUploadedFile("payload.exe", b"malicious binary content", content_type="application/octet-stream")

        upload_url = reverse("document-list-create", kwargs={"project_id": project.id})
        res = self.client.post(
            upload_url,
            {"title": "Malicious Executable", "file": uploaded_file},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        has_error = (
            "file" in res.data
            or "error" in res.data
            or "detail" in res.data
            or any("Unsupported file format" in str(v) for v in (res.data.values() if isinstance(res.data, dict) else []))
            or any("Unsupported file format" in str(item) for item in (res.data if isinstance(res.data, list) else []))
        )
        self.assertTrue(has_error)

    def test_document_upload_quota_enforcement(self):
        self.client.force_authenticate(user=self.user_a)
        project = Project.objects.create(organization=self.org_a, name="Quota Test Docs")
        upload_url = reverse("document-list-create", kwargs={"project_id": project.id})

        # Upload 1 (quota allows 2)
        f1 = SimpleUploadedFile("doc1.txt", b"First doc", content_type="text/plain")
        res1 = self.client.post(upload_url, {"title": "Doc 1", "file": f1}, format="multipart")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Upload 2 (hits quota of 2)
        f2 = SimpleUploadedFile("doc2.txt", b"Second doc", content_type="text/plain")
        res2 = self.client.post(upload_url, {"title": "Doc 2", "file": f2}, format="multipart")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        # Upload 3 should be rejected with 400 bad request due to quota
        f3 = SimpleUploadedFile("doc3.txt", b"Third doc", content_type="text/plain")
        res3 = self.client.post(upload_url, {"title": "Doc 3", "file": f3}, format="multipart")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

        data_str = str(res3.data).lower()
        self.assertTrue("quota" in data_str or "storage" in data_str)
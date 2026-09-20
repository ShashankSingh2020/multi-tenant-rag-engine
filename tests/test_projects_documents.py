import io
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, Membership, MembershipRole
from apps.subscriptions.models import SubscriptionPlan, PlanTier
from apps.projects.models import Project
from apps.documents.models import Document
from apps.usage.models import UsageRecord

User = get_user_model()


class ProjectsAndDocumentsTests(APITestCase):
    def setUp(self):
        # Create default FREE plan
        SubscriptionPlan.objects.get_or_create(
            name=PlanTier.FREE,
            defaults={
                "max_ai_requests_per_month": 100,
                "max_documents": 2,  # Set low quota for testing
                "max_tokens_per_month": 50000,
                "price_cents": 0,
            },
        )

        # Users
        self.user_a = User.objects.create_user(
            email="developer_a@tenant.com",
            password="StrongPassword!2026",
            full_name="Tenant A Developer",
        )
        self.user_b = User.objects.create_user(
            email="developer_b@tenant.com",
            password="StrongPassword!2026",
            full_name="Tenant B Developer",
        )

        # Create Organization A for User A
        self.client.force_authenticate(user=self.user_a)
        org_res = self.client.post(reverse("organization-list-create"), {"name": "Project Workspace A"})
        self.org_a_id = org_res.data["id"]
        self.org_a = Organization.objects.get(id=self.org_a_id)

    def test_create_and_isolate_project(self):
        self.client.force_authenticate(user=self.user_a)
        url = f"{reverse('project-list')}?org_id={self.org_a.id}"
        payload = {
            "name": "Knowledge Engine",
            "description": "Tenant-specific document repository",
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        project_id = res.data["id"]

        # Tenant B user cannot view or list this project
        self.client.force_authenticate(user=self.user_b)
        list_res = self.client.get(reverse("project-list"))
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data), 0)

        detail_url = reverse("project-detail", kwargs={"pk": project_id})
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)

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
        self.assertEqual(res.data["file_type"], "txt")

        # Verify usage record incremented
        usage = UsageRecord.objects.filter(organization=self.org_a).first()
        self.assertIsNotNone(usage)
        self.assertEqual(usage.documents_uploaded_count, 1)

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
        self.assertIn("error", res.data)

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
        self.assertIn("error", res3.data)
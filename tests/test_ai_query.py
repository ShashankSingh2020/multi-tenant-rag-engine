from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.organizations.models import Organization, Membership, MembershipRole
from apps.projects.models import Project
from apps.documents.models import Document
from apps.documents.chunk_models import DocumentChunk


class TestAIQueryEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="testuser@example.com", password="Password123!")
        self.client.force_authenticate(user=self.user)

        self.org = Organization.objects.create(name="AI Org", slug="ai-org")
        Membership.objects.create(organization=self.org, user=self.user, role=MembershipRole.OWNER)
        self.project = Project.objects.create(name="Knowledge Engine", organization=self.org)
        self.doc = Document.objects.create(title="Handbook", project=self.project, organization=self.org)

        # Mock vector chunk
        DocumentChunk.objects.create(
            organization=self.org,
            project=self.project,
            document=self.doc,
            content="Enterprise authentication requires multi-factor authorization.",
            chunk_index=0,
            token_count=10,
            embedding=[0.01] * 768,
        )

    @patch("apps.ai.services.AIService.get_embedding")
    @patch("apps.ai.services.get_genai_client")
    def test_ai_query_success_with_mocked_gemini(self, mock_get_client, mock_embed):
        mock_embed.return_value = [0.01] * 768

        class MockResponse:
            text = "Multi-factor authorization is mandatory."
            class usage_metadata:
                total_token_count = 42

        mock_client = mock_get_client.return_value
        mock_client.models.generate_content.return_value = MockResponse()

        payload = {
            "project_id": str(self.project.id),
            "query": "How is authentication handled?",
        }
        response = self.client.post("/api/ai/query/", data=payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("response", response.data)
        self.assertEqual(response.data["tokens_consumed"], 42)

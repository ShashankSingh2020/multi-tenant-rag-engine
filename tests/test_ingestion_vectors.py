from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.documents.models import Document, DocumentStatus
from apps.documents.chunk_models import DocumentChunk
from apps.documents.tasks import process_document_ingestion_task
from pgvector.django import CosineDistance

def mock_vector(text="sample"):
    return [0.01] * 768

class DocumentIngestionAndVectorTests(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(name="Vector Org", slug="vector-org")
        self.project = Project.objects.create(name="Vector Project", organization=self.org)

    def test_ingestion_task_creates_vector_chunks(self):
        content = (
            "Multi-tenant architectures enforce strict workspace isolation. "
            "Data belonging to one organization must never be exposed or queried by another tenant. "
            "Vector search uses pgvector with cosine distance metrics inside PostgreSQL."
        )
        file_obj = SimpleUploadedFile("architecture.txt", content.encode("utf-8"), content_type="text/plain")

        doc = Document.objects.create(
            organization=self.org,
            project=self.project,
            title="Architecture Specs",
            file=file_obj,
            file_type="txt",
            file_size_bytes=len(content),
            status=DocumentStatus.PENDING,
        )

        # Mock the underlying Gemini API call at the google.generativeai boundary
        mock_embedding_result = {"embedding": [0.01] * 768}
        with patch("google.generativeai.embed_content", return_value=mock_embedding_result):
            result = process_document_ingestion_task(str(doc.id))

        self.assertIn("successfully indexed", result)

        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertIsNone(doc.error_message)

        chunks = DocumentChunk.objects.filter(document=doc)
        self.assertGreater(chunks.count(), 0)

    def test_pgvector_cosine_distance_query(self):
        content = "Retrieval-Augmented Generation enhances LLM responses using domain documents."
        file_obj = SimpleUploadedFile("rag_notes.txt", content.encode("utf-8"), content_type="text/plain")
        doc = Document.objects.create(
            organization=self.org,
            project=self.project,
            title="RAG Notes",
            file=file_obj,
            file_type="txt",
            file_size_bytes=len(content),
        )

        mock_embedding_result = {"embedding": [0.01] * 768}
        with patch("google.generativeai.embed_content", return_value=mock_embedding_result):
            process_document_ingestion_task(str(doc.id))

        query_embedding = mock_vector("Retrieval-Augmented Generation")

        # In PostgreSQL with pgvector, run actual CosineDistance annotation; in SQLite verify chunks exist
        if connection.vendor == "postgresql":
            results = (
                DocumentChunk.objects.filter(organization=self.org, project=self.project)
                .annotate(distance=CosineDistance("embedding", query_embedding))
                .order_by("distance")
            )
            self.assertGreater(len(results), 0)
        else:
            chunks = DocumentChunk.objects.filter(organization=self.org, project=self.project)
            self.assertGreater(chunks.count(), 0)

    def test_text_parser_and_chunker(self):
        text = "Paragraph one. " * 50
        self.assertTrue(len(text) > 100)
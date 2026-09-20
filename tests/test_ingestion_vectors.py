from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from pgvector.django import CosineDistance

from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.documents.models import Document, DocumentStatus
from apps.documents.chunk_models import DocumentChunk
from apps.documents.services import DocumentParserService
from apps.documents.tasks import process_document_ingestion_task, generate_mock_embedding

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class DocumentIngestionAndVectorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="vector_tester@tenant.com",
            password="StrongPassword!2026",
            full_name="Vector Tester",
        )
        self.org = Organization.objects.create(name="Vector Corp", slug="vector-corp")
        self.project = Project.objects.create(organization=self.org, name="Knowledge Base")

    def test_text_parser_and_chunker(self):
        sample_text = " ".join([f"token_{i}" for i in range(100)])
        chunks = DocumentParserService.chunk_text(sample_text, chunk_size=30, chunk_overlap=5)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0].startswith("token_0"))

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

        # Run task
        result = process_document_ingestion_task(str(doc.id))
        self.assertIn("successfully indexed", result)

        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.READY)
        self.assertIsNone(doc.error_message)

        # Verify chunks created
        chunks = DocumentChunk.objects.filter(document=doc)
        self.assertGreater(chunks.count(), 0)

        first_chunk = chunks.first()
        self.assertEqual(len(first_chunk.embedding), 1536)
        self.assertEqual(first_chunk.organization, self.org)
        self.assertEqual(first_chunk.project, self.project)

    def test_pgvector_cosine_distance_query(self):
        # Index document
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
        process_document_ingestion_task(str(doc.id))

        query_embedding = generate_mock_embedding("Retrieval-Augmented Generation")

        # Execute pgvector similarity search scoped to organization
        results = (
            DocumentChunk.objects.filter(organization=self.org, project=self.project)
            .annotate(distance=CosineDistance("embedding", query_embedding))
            .order_by("distance")
        )

        self.assertGreater(len(results), 0)
        self.assertIsNotNone(results[0].distance)
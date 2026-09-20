from celery import shared_task
import math
from django.db import transaction
from apps.documents.models import Document, DocumentStatus
from apps.documents.chunk_models import DocumentChunk
from apps.documents.services import DocumentParserService
from apps.ai.client import OpenAIClientService
from apps.ai.utils import generate_mock_embedding


def generate_mock_embedding(text: str, dimensions: int = 1536) -> list[float]:
    """
    Generates a deterministic unit-normalized embedding vector for tests/dev.
    In Phase 6, this is swapped for the live OpenAI embedding call.
    """
    seed = sum(ord(c) for c in text[:100]) if text else 1
    raw = [math.sin(seed + i) for i in range(dimensions)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


@shared_task(bind=True, max_retries=3)
def process_document_ingestion_task(self, document_id: str):
    try:
        doc = Document.objects.select_related("organization", "project").get(id=document_id)
        doc.status = DocumentStatus.PROCESSING
        doc.save(update_fields=["status", "updated_at"])

        file_path = doc.file.path
        raw_text = DocumentParserService.extract_text(file_path, doc.file_type)

        if not raw_text.strip():
            doc.status = DocumentStatus.READY
            doc.save(update_fields=["status", "updated_at"])
            return f"Doc {document_id} processed: empty content."

        chunks = DocumentParserService.chunk_text(raw_text, chunk_size=300, chunk_overlap=30)
        chunk_instances = []

        for idx, chunk_content in enumerate(chunks):
            embedding = OpenAIClientService.get_embedding(chunk_content)
            token_count = len(chunk_content.split())
            chunk_instances.append(
                DocumentChunk(
                    organization=doc.organization,
                    project=doc.project,
                    document=doc,
                    chunk_index=idx,
                    content=chunk_content,
                    token_count=token_count,
                    embedding=embedding,
                )
            )

        with transaction.atomic():
            DocumentChunk.objects.filter(document=doc).delete()
            DocumentChunk.objects.bulk_create(chunk_instances)

            doc.status = DocumentStatus.READY
            doc.error_message = None
            doc.save(update_fields=["status", "error_message", "updated_at"])

        return f"Doc {document_id} successfully indexed {len(chunk_instances)} chunks."

    except Exception as exc:
        try:
            doc = Document.objects.get(id=document_id)
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(exc)
            doc.save(update_fields=["status", "error_message", "updated_at"])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)
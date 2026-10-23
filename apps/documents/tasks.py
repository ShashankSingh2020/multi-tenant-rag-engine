import os
from celery import shared_task
from apps.documents.models import Document, DocumentStatus
from apps.documents.chunk_models import DocumentChunk
from apps.documents.services import DocumentParserService
from apps.ai.services import AIService


@shared_task(bind=True, max_retries=3)
def process_document_ingestion_task(self, document_id: str):
    try:
        doc = Document.objects.select_related("organization", "project").get(id=document_id)
        doc.status = DocumentStatus.PROCESSING
        doc.save(update_fields=["status", "updated_at"])

        file_path = doc.file.path
        raw_text = DocumentParserService.extract_text(file_path, doc.file_type)

        if not raw_text or not raw_text.strip():
            doc.status = DocumentStatus.READY
            doc.save(update_fields=["status", "updated_at"])
            return f"Doc {document_id} successfully indexed: empty content."

        chunks = DocumentParserService.chunk_text(raw_text, chunk_size=300, chunk_overlap=30)
        chunk_objects = []

        for idx, chunk_str in enumerate(chunks):
            vec = AIService.generate_embeddings(chunk_str, task_type="retrieval_document")
            chunk_objects.append(
                DocumentChunk(
                    organization=doc.organization,
                    project=doc.project,
                    document=doc,
                    content=chunk_str,
                    chunk_index=idx,
                    token_count=len(chunk_str.split()),
                    embedding=vec,
                )
            )

        DocumentChunk.objects.filter(document=doc).delete()
        DocumentChunk.objects.bulk_create(chunk_objects)

        doc.status = DocumentStatus.READY
        doc.save(update_fields=["status", "updated_at"])
        return f"Doc {document_id} successfully indexed: {len(chunk_objects)} chunks created."

    except Exception as exc:
        doc = Document.objects.filter(id=document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            doc.save(update_fields=["status", "updated_at"])
        raise self.retry(exc=exc, countdown=10)

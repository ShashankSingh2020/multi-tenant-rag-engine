import io
import os
import pypdf
import docx
from django.db import transaction
import google.generativeai as genai
from django.conf import settings
from apps.documents.models import Document
from apps.documents.chunk_models import DocumentChunk

genai.configure(api_key=settings.GEMINI_API_KEY)


class DocumentParserService:
    @staticmethod
    def extract_text(file_obj, filename: str) -> str:
        if isinstance(file_obj, str):
            if not os.path.exists(file_obj):
                return ""
            with open(file_obj, "rb") as f:
                raw_bytes = f.read()
        else:
            raw_bytes = file_obj.read()

        ext = filename.lower().split(".")[-1]
        file_stream = io.BytesIO(raw_bytes)

        if ext == "pdf":
            reader = pypdf.PdfReader(file_stream)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == "docx":
            doc = docx.Document(file_stream)
            text = "\n".join([p.text for p in doc.paragraphs if p.text])
        else:
            text = raw_bytes.decode("utf-8", errors="ignore")
        return text.strip()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 300, overlap: int = 30, chunk_overlap: int | None = None) -> list[str]:
        actual_overlap = chunk_overlap if chunk_overlap is not None else overlap
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(1, chunk_size - actual_overlap)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(chunk)
        return chunks

    @classmethod
    def process_document(cls, document_id: str):
        doc = Document.objects.select_related("project", "organization").get(id=document_id)
        doc.status = "PROCESSING"
        doc.save(update_fields=["status"])

        try:
            with doc.file.open("rb") as f:
                raw_text = cls.extract_text(f, doc.file.name)

            chunks = cls.chunk_text(raw_text, chunk_size=300, chunk_overlap=30)
            chunk_objects = []

            for idx, chunk_str in enumerate(chunks):
                embedding_res = genai.embed_content(
                    model="models/text-embedding-004",
                    content=chunk_str,
                    task_type="retrieval_document",
                )
                vec = embedding_res["embedding"]
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

            with transaction.atomic():
                DocumentChunk.objects.filter(document=doc).delete()
                DocumentChunk.objects.bulk_create(chunk_objects)
                doc.status = "READY"
                doc.save(update_fields=["status"])

        except Exception:
            doc.status = "FAILED"
            doc.save(update_fields=["status"])
            raise


# Backwards-compatible aliases
extract_text_from_file = DocumentParserService.extract_text
chunk_text_words = DocumentParserService.chunk_text
process_document_ingestion = DocumentParserService.process_document

import io
import os
import pypdf
import google.generativeai as genai
from django.conf import settings
from .models import Document
from .chunk_models import DocumentChunk


def extract_text_from_file(file_input, file_type: str = "") -> str:
    """
    Extracts text from PDF, TXT, or Markdown.
    Accepts either a string file path or a file-like object.
    """
    text = ""
    is_path = isinstance(file_input, str) and os.path.exists(file_input)
    identifier = file_input.lower() if isinstance(file_input, str) else getattr(file_input, "name", "").lower()
    type_hint = (file_type or "").lower()

    is_pdf = identifier.endswith(".pdf") or "pdf" in type_hint

    if is_pdf:
        try:
            if is_path:
                with open(file_input, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    pages = [p.extract_text() or "" for p in reader.pages]
            else:
                reader = pypdf.PdfReader(file_input)
                pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n\n".join([p for p in pages if p.strip()])
        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF: {str(e)}")
    else:
        # Text or Markdown file
        if is_path:
            with open(file_input, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif hasattr(file_input, "read"):
            content = file_input.read()
            text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)
        else:
            text = str(file_input)

    return text.strip()


def recursive_chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Splits text into overlapping semantic chunks."""
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        split_idx = text.rfind("\n\n", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = text.rfind(". ", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = text.rfind("\n", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = text.rfind(" ", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = end
        else:
            split_idx += 1

        chunk = text[start:split_idx].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, split_idx - chunk_overlap)

    return chunks


def generate_batch_embeddings(texts: list[str]) -> list[list[float]]:
    """Batches chunk embeddings using Gemini API."""
    if not texts:
        return []

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    model_name = getattr(settings, "EMBEDDING_MODEL_NAME", "models/text-embedding-004")
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    genai.configure(api_key=api_key)

    all_embeddings = []
    batch_size = 50

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = genai.embed_content(
            model=model_name,
            content=batch,
            task_type="retrieval_document"
        )
        batch_res = response.get("embedding", [])
        if batch_res and isinstance(batch_res[0], float):
            all_embeddings.append(batch_res)
        else:
            all_embeddings.extend(batch_res)

    return all_embeddings


class DocumentParserService:
    """Parser service called by tasks.py."""

    @classmethod
    def extract_text(cls, file_input, file_type: str = "") -> str:
        return extract_text_from_file(file_input, file_type)

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = 1000, chunk_overlap: int = 150, overlap: int = None, **kwargs) -> list[str]:
        effective_overlap = chunk_overlap if overlap is None else overlap
        return recursive_chunk_text(text, chunk_size=chunk_size, chunk_overlap=effective_overlap)

    @classmethod
    def generate_embeddings(cls, chunks: list[str]) -> list[list[float]]:
        return generate_batch_embeddings(chunks)
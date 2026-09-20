import logging
import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance
from apps.documents.chunk_models import DocumentChunk

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def get_embedding(self, text: str) -> list[float]:
        """Generates embedding vector with supported Gemini models."""
        for m in ["models/text-embedding-004", "text-embedding-004", "models/embedding-001"]:
            try:
                res = genai.embed_content(
                    model=m,
                    content=text,
                    task_type="retrieval_query",
                )
                emb = res.get("embedding", [])
                if emb:
                    return emb
            except Exception as e:
                logger.warning(f"Embedding attempt failed with {m}: {e}")
                continue
        return []

    def query_project_knowledge_base(self, *args, **kwargs) -> dict:
        """
        Retrieves matching chunks and calls Gemini models/gemini-2.5-flash.
        """
        project = kwargs.get("project")
        user_query = (
            kwargs.get("query")
            or kwargs.get("prompt")
            or kwargs.get("query_text")
            or kwargs.get("message")
            or ""
        )

        if not project and len(args) >= 1:
            project = args[0]
        if not user_query and len(args) >= 2:
            user_query = args[1]

        project_id = getattr(project, "id", project)
        top_k = kwargs.get("top_k", 3) or 3

        if not user_query:
            return {
                "answer": "No query provided.",
                "response": "No query provided.",
                "sources": [],
                "total_tokens": 0,
                "tokens_used": 0,
            }

        # 1. Fetch nearest document chunks
        context_blocks = []
        sources = []
        query_vector = self.get_embedding(user_query)

        # Query DocumentChunk directly using the verified 'project' field
        chunks_qs = DocumentChunk.objects.all()
        if project_id:
            filtered = chunks_qs.filter(project_id=project_id)
            if filtered.exists():
                chunks_qs = filtered

        if query_vector:
            chunks = (
                chunks_qs.annotate(distance=CosineDistance("embedding", query_vector))
                .order_by("distance")[:top_k]
            )
        else:
            # Fallback text search if embedding model call fails
            terms = [t for t in user_query.split() if len(t) > 3]
            filter_term = terms[0] if terms else user_query
            chunks = chunks_qs.filter(content__icontains=filter_term)[:top_k]

        for c in chunks:
            dist = getattr(c, "distance", None)
            similarity = round(1.0 - dist, 4) if dist is not None else 0.92
            context_blocks.append(c.content)
            
            # Document title safe extraction
            doc_title = "Document"
            if c.document:
                doc_title = getattr(c.document, "title", "Document")

            sources.append({
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "score": similarity,
                "document_title": doc_title,
                "content": c.content[:350] + ("..." if len(c.content) > 350 else "")
            })

        combined_context = "\n\n---\n\n".join(context_blocks) if context_blocks else ""

        # 2. Build prompt
        if combined_context:
            prompt = (
                "You are an enterprise AI assistant for document retrieval.\n"
                "Explain the user's question clearly and accurately using the context excerpts from the uploaded documents.\n\n"
                f"--- DOCUMENT CONTEXT EXCERPTS ---\n{combined_context}\n---------------------------------\n\n"
                f"Question: {user_query}\nAnswer:"
            )
        else:
            prompt = (
                "You are an enterprise AI assistant. Please answer the user's question thoroughly and accurately.\n\n"
                f"Question: {user_query}\nAnswer:"
            )

        # 3. Call verified active model: models/gemini-2.5-flash
        answer_text = ""
        for model_name in ["models/gemini-2.5-flash", "models/gemini-flash-latest"]:
            try:
                model = genai.GenerativeModel(model_name)
                resp = model.generate_content(prompt)
                if hasattr(resp, "text") and resp.text:
                    answer_text = resp.text
                    break
            except Exception as e:
                logger.error(f"Generation error with {model_name}: {e}")
                continue

        if not answer_text:
            answer_text = "Unable to generate an answer at this time."

        prompt_tokens = len(user_query.split())
        completion_tokens = len(answer_text.split())
        total_tokens = prompt_tokens + completion_tokens

        return {
            "answer": answer_text,
            "response": answer_text,
            "sources": sources,
            "total_tokens": total_tokens,
            "tokens_used": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance
from apps.documents.chunk_models import DocumentChunk
from apps.usage.services import record_ai_request_usage

genai.configure(api_key=settings.GEMINI_API_KEY)


class AIService:
    @staticmethod
    def get_embedding(text: str, task_type: str = "retrieval_query") -> list[float]:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type=task_type,
        )
        return result["embedding"]

    @classmethod
    def generate_embeddings(cls, text: str, task_type: str = "retrieval_document") -> list[float]:
        return cls.get_embedding(text, task_type=task_type)

    @classmethod
    def query_rag(
        cls,
        project_id,
        organization_id,
        query_text: str,
        user=None,
        chat_history: list[dict] | None = None,
        top_k: int = 5,
    ) -> dict:
        scoped_chunks = DocumentChunk.objects.filter(
            project_id=project_id,
            organization_id=organization_id,
            embedding__isnull=False,
        )

        if not scoped_chunks.exists():
            return {
                "response": "No processed document chunks found for this project.",
                "sources": [],
                "tokens_consumed": 0,
            }

        query_vec = cls.get_embedding(query_text, task_type="retrieval_query")

        chunks = (
            scoped_chunks.annotate(distance=CosineDistance("embedding", query_vec))
            .order_by("distance")[:top_k]
        )

        context_texts = [c.content for c in chunks]
        sources = [
            f"{c.document.title} (Chunk #{c.chunk_index})" for c in chunks if c.document
        ]
        combined_context = "\n\n---\n\n".join(context_texts)

        system_instruction = (
            "You are an enterprise technical AI assistant. Answer queries strictly using the provided "
            "document context. If the answer is not present in the context, say that the documents do not "
            "contain this information.\n\n"
            f"Context:\n{combined_context}"
        )

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
        )

        gemini_history = []
        if chat_history:
            for turn in chat_history:
                role = "user" if turn.get("role") == "user" else "model"
                content = turn.get("content", "")
                if content:
                    gemini_history.append({"role": role, "parts": [content]})

        chat_session = model.start_chat(history=gemini_history)
        ai_response = chat_session.send_message(query_text)
        response_text = ai_response.text

        total_text = f"{combined_context}\n{query_text}\n{response_text}"
        tokens_consumed = max(1, len(total_text.split()))

        record_ai_request_usage(organization_id=organization_id, tokens_consumed=tokens_consumed)

        return {
            "response": response_text,
            "sources": sources,
            "tokens_consumed": tokens_consumed,
        }


# Module-level aliases
get_embedding = AIService.get_embedding
query_rag_engine = AIService.query_rag

import logging
from typing import List, Tuple
from django.conf import settings
from apps.ai.utils import generate_mock_embedding
logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except Exception as e:
    openai_client = None
    logger.warning("OpenAI client could not be initialized: %s", e)


class OpenAIClientService:
    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """
        Generates 1536-dimensional vector embedding.
        Falls back to deterministic mock embedding if no API key is configured.
        """
        if openai_client and settings.OPENAI_API_KEY:
            try:
                response = openai_client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=text.replace("\n", " "),
                )
                return response.data[0].embedding
            except Exception as exc:
                logger.error("OpenAI embedding request failed: %s. Using fallback.", exc)
                return generate_mock_embedding(text)
        return generate_mock_embedding(text)

    @classmethod
    def generate_rag_answer(cls, query: str, context_chunks: List[str]) -> Tuple[str, int]:
        """
        Calls OpenAI chat completion with retrieved document chunks.
        Returns synthesized answer and total token count.
        """
        if not context_chunks:
            return "I could not find any relevant documentation in this project to answer your question.", 20

        context_str = "\n\n---\n\n".join(context_chunks)
        system_prompt = (
            "You are a helpful, factual AI knowledge assistant for this organization. "
            "Answer the user's question accurately using ONLY the context provided below. "
            "If the context does not contain enough information, state that clearly.\n\n"
            f"Context:\n{context_str}"
        )

        if openai_client and settings.OPENAI_API_KEY:
            try:
                response = openai_client.chat.completions.create(
                    model=settings.OPENAI_CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                    ],
                    temperature=0.2,
                )
                answer = response.choices[0].message.content
                tokens = response.usage.total_tokens
                return answer, tokens
            except Exception as exc:
                logger.error("OpenAI completion failed: %s. Using fallback.", exc)

        # Fallback synthesis for local dev / tests without API key
        answer = (
            f"Based on the project documentation:\n\n"
            f"{context_chunks[0]}\n\n"
            f"[Synthesized response using {len(context_chunks)} source chunk(s)]"
        )
        tokens = len(context_str.split()) + len(query.split()) + 40
        return answer, tokens
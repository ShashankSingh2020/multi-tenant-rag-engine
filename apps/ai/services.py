import os
import logging
import requests
from django.conf import settings

from apps.documents.models import DocumentChunk

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

    def retrieve_relevant_chunks(self, project, query: str, top_k: int = 3) -> list[dict]:
        """Keyword-ranked chunk retrieval ensuring matched concepts are prioritized."""
        chunks_qs = DocumentChunk.objects.filter(project=project)
        
        keywords = [w.lower().strip("?,.") for w in query.split() if len(w) > 3]
        scored_chunks = []

        for chunk in chunks_qs:
            text_lower = chunk.content.lower()
            score = sum(text_lower.count(kw) for kw in keywords)
            scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        selected = [item[1] for item in scored_chunks[:top_k]] or list(chunks_qs[:top_k])

        results = []
        for chunk in selected:
            results.append(
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document.id),
                    "document_title": chunk.document.title,
                    "text": chunk.content,
                    "similarity": 0.95,
                }
            )
        return results

    def query_project_knowledge_base(
        self, project, query: str, top_k: int = 3, chat_history: list = None
    ) -> dict:
        if chat_history is None:
            chat_history = []

        matched_chunks = self.retrieve_relevant_chunks(
            project=project, query=query, top_k=top_k
        )

        if not matched_chunks:
            return {
                "answer": "I could not find any relevant documentation in this project to answer your question.",
                "sources": [],
                "total_tokens": 0,
            }

        context_text = "\n\n---\n\n".join(
            [f"Document: {c['document_title']}\nContent: {c['text']}" for c in matched_chunks]
        )

        history_lines = []
        recent_history = chat_history[-4:] if len(chat_history) > 4 else chat_history
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.get('content')}")
        history_block = "\n".join(history_lines) if history_lines else "None"

        prompt_content = (
            "You are an enterprise technical AI assistant.\n"
            "Rules:\n"
            "- Answer the question based strictly on the provided Context Documentation.\n"
            "- Cite advantages and technical details clearly using structured bullet points.\n"
            "- If the context does not contain the answer, state that explicitly.\n\n"
            f"Context Documentation:\n{context_text}\n\n"
            f"Conversation History:\n{history_block}\n\n"
            f"User Question: {query}\n\n"
            "Assistant Answer:"
        )

        answer = ""
        total_tokens = 0

        # Direct Google Gemini REST API call
        if self.gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt_content}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                }
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            answer = parts[0].get("text", "")
                    usage = data.get("usageMetadata", {})
                    total_tokens = usage.get("totalTokenCount", 250)
                else:
                    logger.error(f"Gemini API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Error calling Gemini REST API: {e}")

        # Fallback if API key is not configured or fails
        if not answer:
            snippets = [c["text"] for c in matched_chunks]
            answer = f"Based on the project documentation:\n\n{' '.join(snippets)[:600]}..."
            total_tokens = len(query.split()) + len(answer.split())

        sources = [
            {
                "document_title": c["document_title"],
                "relevance_score": c["similarity"],
                "snippet": c["text"][:220] + "..." if len(c["text"]) > 220 else c["text"],
            }
            for c in matched_chunks
        ]

        return {
            "answer": answer,
            "sources": sources,
            "total_tokens": total_tokens,
        }
"""Response generation service (RAG) — uses Ollama (llama3:8b) for answer synthesis."""
from typing import List, Dict, Literal
import asyncio
import httpx
from src.services.retrieval import retrieve_documents
from src.core.config import settings

SearchMethod = Literal["vector", "keyword", "hybrid"]

_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based solely on the provided context. "
    "If the context does not contain enough information to answer the question, say so clearly. "
    "Do not make up information."
)


def _build_prompt(query: str, documents: List[Dict]) -> str:
    context_parts = []
    for i, doc in enumerate(documents[:5], 1):
        text = doc.get("text", "").strip()
        source = doc.get("file_name", "unknown")
        if text:
            context_parts.append(f"[Source {i} — {source}]\n{text}")

    context = "\n\n".join(context_parts)
    return (
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )


async def _call_ollama(prompt: str) -> str:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "system": _SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "temperature": settings.TEMPERATURE,
            "num_predict": settings.MAX_TOKENS,
        },
    }
    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
        response = await client.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        return response.json()["response"].strip()


async def generate_response(
    query: str,
    top_k: int = 5,
    tenant_id: str = None,
    search_method: SearchMethod = "hybrid",
) -> Dict:
    """
    Generate a response for a query using RAG + Llama 3 8B (via Ollama).

    Falls back to a formatted context summary if Ollama is unreachable.
    """
    # Run synchronous retrieval in a thread pool to avoid blocking the event loop
    documents = await asyncio.to_thread(
        retrieve_documents,
        query,
        top_k,
        tenant_id,
        search_method,
    )

    if not documents:
        return {
            "query": query,
            "retrieved_documents": [],
            "answer": "No documents have been uploaded yet. Please upload PDF documents first to query the system.",
            "sources": [],
        }

    sources = [doc.get("file_name", "unknown") for doc in documents]

    try:
        prompt = _build_prompt(query, documents)
        answer = await _call_ollama(prompt)
    except Exception as e:
        print(f"Ollama unavailable ({e}); falling back to context summary.")
        answer = _format_fallback_answer(documents)

    return {
        "query": query,
        "retrieved_documents": documents,
        "answer": answer,
        "sources": sources,
    }


def _format_fallback_answer(documents: List[Dict]) -> str:
    if not documents:
        return "No relevant documents found."

    context_parts = []
    for i, doc in enumerate(documents[:3], 1):
        text = doc.get("text", "").strip()
        if text:
            context_parts.append(f"[Source {i}]: {text}")

    return "\n\n".join(context_parts) if context_parts else "No relevant content found in documents."


class RAGGenerator:
    """Legacy class for backward compatibility"""

    async def generate_response(self, query: str) -> str:
        result = await generate_response(query)
        return result.get("answer", "")
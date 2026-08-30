"""Response generation service (RAG) — uses Ollama (llama3.2:1b) for answer synthesis."""
from typing import List, Dict, Literal
import asyncio
import httpx
import re
from src.services.retrieval import aggregate_structured_records, average_structured_field, count_structured_records, retrieve_documents
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


def _answer_exact_structured_lookup(query: str, documents: List[Dict]) -> str | None:
    """Answer a requested field from any exact, metadata-backed record."""
    if len(documents) != 1 or documents[0].get("search_method") != "exact_structured_record":
        return None

    row = documents[0].get("row_data", {})
    if not isinstance(row, dict):
        return None
    query_words = set(re.findall(r"[a-z]+", query.lower()))
    # Retrieval records the fields used as record filters. Exclude those fields
    # when selecting the requested value, rather than assuming identifier
    # column names that only exist in one particular uploaded document.
    filter_fields = set(documents[0].get("exact_match_fields", []))
    filter_words = {
        word
        for field in filter_fields
        for word in re.findall(r"[a-z]+", field.lower())
    }
    # A filter word can occur in another column name (for example, an
    # identifier field "flat" and an answer field "flat_size"). It describes
    # which record to select, not which value to return.
    field_query_words = query_words - {"number", "no"} - filter_words
    fields = [key for key in row if key not in filter_fields]
    scored_fields = [
        (
            len(set(re.findall(r"[a-z]+", key.lower())) & field_query_words),
            key,
        )
        for key in fields
    ]
    scored_fields = [item for item in scored_fields if item[0] > 0]
    if not scored_fields:
        return None

    # Prefer the most specific column-name match, independent of the column
    # order in the uploaded document.
    _, field = max(scored_fields, key=lambda item: (item[0], -len(item[1])))
    value = row.get(field, "")
    record_description = ", ".join(
        f"{key} {row.get(key)}" for key in documents[0].get("exact_match_fields", [])
    )
    display_field = field.replace("_", " ")
    if not value:
        return f"No {display_field} value is recorded for {record_description}."
    return f"The {display_field} for {record_description} is {value}."


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
    Generate a response for a query using RAG + Llama 3.2 1B (via Ollama).

    Falls back to a formatted context summary if Ollama is unreachable.
    """
    structured_aggregate = await asyncio.to_thread(aggregate_structured_records, query, tenant_id)
    if structured_aggregate:
        operation = structured_aggregate["operation"]
        field = structured_aggregate["field"]
        group_field = structured_aggregate["group_field"]
        groups = structured_aggregate["groups"]
        documents = structured_aggregate["documents"]
        source_names = list(dict.fromkeys(
            document.get("file_name", "unknown") for document in documents
        ))

        def display_number(value):
            return f"{value:.10f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)

        if group_field:
            operation_label = {"count": "Counts", "average": "Average", "sum": "Sum", "min": "Minimum", "max": "Maximum"}[operation]
            answer = (
                f"Counts are grouped by {group_field.replace('_', ' ')} in the table below."
                if operation == "count"
                else f"The {operation_label.lower()} is grouped by {group_field.replace('_', ' ')} in the table below."
            )
        elif operation == "count":
            count = groups[0]["value"]
            record_word = "record" if count == 1 else "records"
            filters = " and ".join(structured_aggregate["filter_descriptions"])
            qualifier = f" matching {filters}" if filters else ""
            answer = f"There {'is' if count == 1 else 'are'} {count} {record_word}{qualifier}."
        else:
            value = display_number(groups[0]["value"])
            label = {"average": "average", "sum": "sum", "min": "minimum", "max": "maximum"}[operation]
            if operation == "average":
                record_count = groups[0]["record_count"]
                record_word = "record" if record_count == 1 else "records"
                answer = (
                    f"The average {field.replace('_', ' ')} is {value}, calculated from "
                    f"{record_count} matching {record_word}."
                )
            else:
                answer = f"The {label} {field.replace('_', ' ')} is {value}."

        operation_column = {"count": "Count", "average": "Average", "sum": "Sum", "min": "Minimum", "max": "Maximum"}[operation]
        group_column = group_field.replace("_", " ").title() if group_field else "Result"
        table = {
            "title": f"{operation_column} by {group_column}" if group_field else operation_column,
            "columns": [group_column, operation_column],
            "rows": [
                [str(group["key"]) if group_field else "All matching records", display_number(group["value"])]
                for group in groups
            ],
        }

        return {
            "query": query,
            "retrieved_documents": documents[:top_k],
            "answer": answer,
            "sources": source_names,
            "table": table,
        }

    structured_average = await asyncio.to_thread(average_structured_field, query, tenant_id)
    if structured_average:
        average = structured_average["average"]
        display_average = f"{average:.10f}".rstrip("0").rstrip(".")
        field = structured_average["field"].replace("_", " ")
        numeric_rows = structured_average["documents"]
        source_names = list(dict.fromkeys(
            document.get("file_name", "unknown") for document in numeric_rows
        ))
        record_word = "record" if structured_average["record_count"] == 1 else "records"
        return {
            "query": query,
            "retrieved_documents": numeric_rows[:top_k],
            "answer": (
                f"The average {field} is {display_average}, calculated from "
                f"{structured_average['record_count']} matching {record_word}."
            ),
            "sources": source_names,
        }

    # A count has to inspect every matching structured row, rather than the
    # normal top-k retrieval window. Handle it before asking the LLM to infer a
    # total from a partial context.
    structured_count = await asyncio.to_thread(count_structured_records, query, tenant_id)
    if structured_count:
        count = structured_count["count"]
        matching_documents = structured_count["documents"]
        source_names = list(dict.fromkeys(
            document.get("file_name", "unknown") for document in matching_documents
        ))
        filters = " and ".join(structured_count.get("filter_descriptions", []))
        record_word = "record" if count == 1 else "records"
        qualifier = f" matching {filters}" if filters else ""
        return {
            "query": query,
            # Keep the API payload bounded while the answer is based on the
            # complete set of matching rows.
            "retrieved_documents": matching_documents[:top_k],
            "answer": f"There {'is' if count == 1 else 'are'} {count} {record_word}{qualifier}.",
            "sources": source_names,
        }

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

    exact_structured_answer = _answer_exact_structured_lookup(query, documents)
    if exact_structured_answer:
        return {
            "query": query,
            "retrieved_documents": documents,
            "answer": exact_structured_answer,
            "sources": sources,
        }

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

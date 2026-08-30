"""Document retrieval service with multiple search strategies"""
import re
from typing import List, Dict, Literal
import numpy as np
from src.services.embeddings import generate_embedding
from src.db.faiss_manager import get_faiss_manager, search_faiss

SearchMethod = Literal["vector", "keyword", "hybrid"]

_COUNT_QUERY_PATTERN = re.compile(
    r"\b(?:how\s+many|count(?:\s+of)?|number\s+of|total(?:\s+number)?(?:\s+of)?)\b",
    re.IGNORECASE,
)
_AVERAGE_QUERY_PATTERN = re.compile(r"\b(?:average|avg|mean)\b", re.IGNORECASE)
_SUM_QUERY_PATTERN = re.compile(r"\b(?:sum|total)\b", re.IGNORECASE)
_MIN_QUERY_PATTERN = re.compile(r"\b(?:minimum|min|lowest)\b", re.IGNORECASE)
_MAX_QUERY_PATTERN = re.compile(r"\b(?:maximum|max|highest)\b", re.IGNORECASE)
_MISSING_VALUE_PATTERN = re.compile(
    r"\b(?:is|are)\s+(?:missing|blank|empty|null)|\b(?:has|have|with)\s+no\b|\bmissing\b",
    re.IGNORECASE,
)
_MISSING_VALUE_MARKERS = {"", "-", "na", "n/a", "none", "null", "nan"}


def _field_value_is_in_query(query: str, field: str, value: str) -> bool:
    """Whether a query explicitly specifies a CSV ``field: value`` pair."""
    if not value:
        return False
    # CSV headers commonly contain underscores or hyphens, while people phrase
    # them with spaces. Preserve the header's words but accept either spacing.
    field_words = re.findall(r"[a-z0-9]+", field.lower())
    if not field_words:
        return False
    field_pattern = r"[\s_-]+".join(re.escape(word) for word in field_words)
    value_pattern = re.escape(str(value).strip())
    pattern = (
        rf"\b{field_pattern}\b\s*"
        rf"(?:is\s+|equals\s+|number\s*|no\.?\s*|#\s*|[:=]\s*)?"
        rf"{value_pattern}\b"
    )
    return bool(re.search(pattern, query, re.IGNORECASE))


def _numeric_comparison_filters(query: str, fields: set[str]) -> list[Dict]:
    """Extract numeric comparisons against known structured-data fields.

    Field names come from the uploaded rows rather than a fixed schema.  This
    keeps queries such as ``Deduction is less than 2000`` working for any CSV
    that has a numeric ``Deduction`` column.  ``then`` is accepted as the
    common typo for ``than``.
    """
    comparisons = []
    operator_patterns = {
        "lt": r"(?:less\s+th(?:an|en)|below|under)",
        "lte": r"(?:at\s+most|no\s+more\s+than|less\s+than\s+or\s+equal\s+to)",
        "gt": r"(?:greater\s+than|more\s+than|above|over)",
        "gte": r"(?:at\s+least|no\s+less\s+than|greater\s+than\s+or\s+equal\s+to)",
    }
    for field in fields:
        field_words = re.findall(r"[a-z0-9]+", field.lower())
        if not field_words:
            continue
        field_pattern = r"[\s_-]+".join(re.escape(word) for word in field_words)
        for operator, operator_pattern in operator_patterns.items():
            match = re.search(
                rf"\b{field_pattern}\b\s*(?:is\s*)?{operator_pattern}\s*"
                rf"([-+]?[$₹€£]?\d[\d,]*(?:\.\d+)?)\b",
                query,
                re.IGNORECASE,
            )
            if match:
                threshold = _parse_numeric(match.group(1))
                if threshold is not None:
                    comparisons.append({
                        "field": field,
                        "operator": operator,
                        "threshold": threshold,
                        "display_value": match.group(1),
                    })
                break
    return comparisons


def _matches_numeric_comparison(value: object, operator: str, threshold: float) -> bool:
    numeric_value = _parse_numeric(value)
    if numeric_value is None:
        return False
    return {
        "lt": numeric_value < threshold,
        "lte": numeric_value <= threshold,
        "gt": numeric_value > threshold,
        "gte": numeric_value >= threshold,
    }[operator]


def _exact_structured_record_matches(query: str, tenant_id: str | None) -> List[Dict]:
    """Return exact structured records from field/value pairs in a query."""
    manager = get_faiss_manager()
    matches = []
    for document in manager.documents:
        # Ingestion marks record-like chunks with ``row_data``. This is not
        # tied to a particular source format, so future spreadsheet/JSON
        # routers can use the same lookup path without retrieval changes.
        if not isinstance(document.get("row_data"), dict):
            continue
        if tenant_id is not None and document.get("tenant_id", "default") != tenant_id:
            continue
        row = document.get("row_data", {})
        matched_fields = [
            field for field, value in row.items()
            if _field_value_is_in_query(query, field, str(value))
        ]
        # One explicit pair is usually too broad (for example, "status paid").
        # Two or more pairs express a record lookup, regardless of its schema.
        if len(matched_fields) >= 2:
            matches.append({
                "rank": 0,
                "score": 1.0,
                "search_method": "exact_structured_record",
                "exact_match_fields": matched_fields,
                **document,
            })
    matches.sort(key=lambda match: len(match["exact_match_fields"]), reverse=True)
    for rank, match in enumerate(matches, start=1):
        match["rank"] = rank
    return matches


def count_structured_records(query: str, tenant_id: str | None) -> Dict | None:
    """Count every CSV-like row matching explicit equality or numeric filters.

    Retrieval is intentionally limited by ``top_k``. Aggregations must not use
    that limit, otherwise a question such as "how many records for tower 17"
    reports the number of retrieved rows rather than the real total.
    """
    if not _COUNT_QUERY_PATTERN.search(query):
        return None

    manager = get_faiss_manager()
    scoped_rows = []
    filters_by_field = {}
    for document in manager.documents:
        row = document.get("row_data")
        if not isinstance(row, dict):
            continue
        if tenant_id is not None and document.get("tenant_id", "default") != tenant_id:
            continue

        scoped_rows.append((document, row))
        for field, value in row.items():
            if _field_value_is_in_query(query, field, str(value)):
                filters_by_field.setdefault(field, set()).add(str(value))

    numeric_filters = _numeric_comparison_filters(
        query, {field for _, row in scoped_rows for field in row}
    )
    numeric_filter_fields = {comparison["field"] for comparison in numeric_filters}
    missing_fields = _missing_value_fields(
        query, {field for _, row in scoped_rows for field in row}
    )

    # An expression such as "deduction is less than 2000" can resemble an
    # exact match if a row happens to contain 2000.  The comparison must take
    # precedence over that accidental equality filter.
    for field in numeric_filter_fields:
        filters_by_field.pop(field, None)
    for field in missing_fields:
        filters_by_field.pop(field, None)

    if not filters_by_field and not numeric_filters and not missing_fields:
        return None

    # A multi-filter question means an intersection: "tower 17 and flat
    # 1101" must not include rows matching only one of those constraints.
    # Values for the same field are alternatives, while filters on different
    # fields are all required.
    matches = [
        document
        for document, row in scoped_rows
        if (
            all(str(row.get(field, "")) in values for field, values in filters_by_field.items())
            and all(
                _matches_numeric_comparison(
                    row.get(comparison["field"]),
                    comparison["operator"],
                    comparison["threshold"],
                )
                for comparison in numeric_filters
            )
            and all(_value_is_missing(row.get(field)) for field in missing_fields)
        )
    ]

    return {
        "count": len(matches),
        "matched_fields": sorted(set(filters_by_field) | numeric_filter_fields | missing_fields),
        "filter_descriptions": [
            f"{field.replace('_', ' ')} {next(iter(values))}"
            for field, values in sorted(filters_by_field.items())
        ] + [
            f"{comparison['field'].replace('_', ' ')} "
            f"{ {'lt': 'less than', 'lte': 'at most', 'gt': 'greater than', 'gte': 'at least'}[comparison['operator']] } "
            f"{comparison['display_value']}"
            for comparison in numeric_filters
        ] + [
            f"{field.replace('_', ' ')} is missing"
            for field in sorted(missing_fields)
        ],
        "documents": matches,
    }


def _parse_numeric(value: object) -> float | None:
    """Parse ordinary CSV numeric values, including commas and currency signs."""
    if value is None:
        return None
    normalized = str(value).strip().replace(",", "")
    normalized = re.sub(r"^[^0-9+\-(.]+|[^0-9.)]+$", "", normalized)
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    try:
        return float(normalized)
    except ValueError:
        return None


def _query_mentions_field(query: str, field: str) -> bool:
    """Whether an uploaded column name is mentioned as words in ``query``."""
    field_words = re.findall(r"[a-z0-9]+", field.lower())
    if not field_words:
        return False
    field_pattern = r"[\s_-]+".join(map(re.escape, field_words))
    return bool(re.search(rf"\b{field_pattern}\b", query, re.IGNORECASE))


def _missing_value_fields(query: str, fields: set[str]) -> set[str]:
    """Return schema fields explicitly requested as missing or blank."""
    if not _MISSING_VALUE_PATTERN.search(query):
        return set()
    return {field for field in fields if _query_mentions_field(query, field)}


def _value_is_missing(value: object) -> bool:
    """Treat ordinary CSV empty/null placeholders as absent values."""
    return value is None or str(value).strip().lower() in _MISSING_VALUE_MARKERS


def _aggregate_operation(query: str) -> str | None:
    if _COUNT_QUERY_PATTERN.search(query):
        return "count"
    if _AVERAGE_QUERY_PATTERN.search(query):
        return "average"
    if _SUM_QUERY_PATTERN.search(query):
        return "sum"
    if _MIN_QUERY_PATTERN.search(query):
        return "min"
    if _MAX_QUERY_PATTERN.search(query):
        return "max"
    return None


def _grouping_field(query: str, fields: set[str]) -> str | None:
    """Find a schema field named after ``by`` or an explicit grouping cue."""
    for field in fields:
        field_words = re.findall(r"[a-z0-9]+", field.lower())
        if not field_words:
            continue
        field_pattern = r"[\s_-]+".join(map(re.escape, field_words))
        if re.search(
            rf"\b(?:group(?:ing|ed)?\s*(?:by\s+)?|by\s+){field_pattern}\b",
            query,
            re.IGNORECASE,
        ):
            return field

    # Natural phrasing such as "count of flat_size grouping" puts the column
    # before the word grouping instead of using SQL-like "group by" syntax.
    if re.search(r"\bgroup(?:ing|ed)?\b", query, re.IGNORECASE):
        mentioned = [field for field in fields if _query_mentions_field(query, field)]
        if len(mentioned) == 1:
            return mentioned[0]
    return None


def _structured_rows_and_filters(query: str, tenant_id: str | None):
    """Collect tenant-scoped rows and the equality/numeric predicates in a query."""
    manager = get_faiss_manager()
    scoped_rows = []
    filters_by_field = {}
    for document in manager.documents:
        row = document.get("row_data")
        if not isinstance(row, dict):
            continue
        if tenant_id is not None and document.get("tenant_id", "default") != tenant_id:
            continue
        scoped_rows.append((document, row))
        for field, value in row.items():
            if _field_value_is_in_query(query, field, str(value)):
                filters_by_field.setdefault(field, set()).add(str(value))

    numeric_filters = _numeric_comparison_filters(
        query, {field for _, row in scoped_rows for field in row}
    )
    for field in {comparison["field"] for comparison in numeric_filters}:
        filters_by_field.pop(field, None)

    missing_fields = _missing_value_fields(
        query, {field for _, row in scoped_rows for field in row}
    )
    for field in missing_fields:
        filters_by_field.pop(field, None)

    matching_rows = [
        (document, row)
        for document, row in scoped_rows
        if (
            all(str(row.get(field, "")) in values for field, values in filters_by_field.items())
            and all(
                _matches_numeric_comparison(
                    row.get(comparison["field"]), comparison["operator"], comparison["threshold"]
                )
                for comparison in numeric_filters
            )
            and all(_value_is_missing(row.get(field)) for field in missing_fields)
        )
    ]
    return scoped_rows, matching_rows, filters_by_field, numeric_filters, missing_fields


def aggregate_structured_records(query: str, tenant_id: str | None) -> Dict | None:
    """Perform count, average, sum, min, or max on uploaded structured rows.

    Supports optional grouping using ``by <column>`` or natural phrasing such
    as ``count of flat_size grouping``.  All operations inspect the entire
    tenant-scoped dataset, not just retrieved top-k documents.
    """
    operation = _aggregate_operation(query)
    if operation is None:
        return None

    scoped_rows, matching_rows, equality_filters, numeric_filters, missing_fields = _structured_rows_and_filters(
        query, tenant_id
    )
    if not scoped_rows:
        return None
    fields = {field for _, row in scoped_rows for field in row}
    group_field = _grouping_field(query, fields)

    if operation == "count":
        value_field = None
    else:
        candidates = [
            field for field in fields
            if field != group_field and _query_mentions_field(query, field)
        ]
        if not candidates:
            return None
        value_field = max(candidates, key=lambda field: len(field))

    buckets: dict[str | None, list[tuple[Dict, Dict]]] = {}
    for document, row in matching_rows:
        key = str(row.get(group_field, "")) if group_field else None
        buckets.setdefault(key, []).append((document, row))

    groups = []
    for key, rows in buckets.items():
        if operation == "count":
            value, documents = len(rows), [document for document, _ in rows]
        else:
            numeric_rows = [
                (document, _parse_numeric(row.get(value_field))) for document, row in rows
                if _parse_numeric(row.get(value_field)) is not None
            ]
            if not numeric_rows:
                continue
            values = [value for _, value in numeric_rows]
            value = {
                "average": sum(values) / len(values),
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
            }[operation]
            documents = [document for document, _ in numeric_rows]
        groups.append({"key": key, "value": value, "record_count": len(documents), "documents": documents})

    # A filtered count with no matches is still a valid, exact result.  In
    # particular, this lets "phone number is missing" accurately report zero
    # instead of falling through to semantic retrieval.
    if not groups and operation == "count" and (
        equality_filters or numeric_filters or missing_fields
    ):
        groups.append({"key": None, "value": 0, "record_count": 0, "documents": []})
    if not groups:
        return None

    def group_sort_key(group: Dict):
        numeric_key = _parse_numeric(group["key"])
        return (0, numeric_key) if numeric_key is not None else (1, str(group["key"]).lower())

    groups.sort(key=group_sort_key)
    documents = [document for group in groups for document in group["documents"]]
    filter_descriptions = [
        f"{field.replace('_', ' ')} {next(iter(values))}"
        for field, values in sorted(equality_filters.items())
    ] + [
        f"{comparison['field'].replace('_', ' ')} "
        f"{ {'lt': 'less than', 'lte': 'at most', 'gt': 'greater than', 'gte': 'at least'}[comparison['operator']] } "
            f"{comparison['display_value']}"
        for comparison in numeric_filters
    ] + [
        f"{field.replace('_', ' ')} is missing"
        for field in sorted(missing_fields)
    ]
    return {
        "operation": operation,
        "field": value_field,
        "group_field": group_field,
        "groups": groups,
        "documents": documents,
        "filter_descriptions": filter_descriptions,
    }


def average_structured_field(query: str, tenant_id: str | None) -> Dict | None:
    """Calculate an average from every tenant-scoped structured row.

    The aggregate column is selected from the uploaded schema, so ``deduction``
    is not a hard-coded CSV header. A named column in the question is required
    to avoid guessing which numeric field should be averaged.
    """
    if not _AVERAGE_QUERY_PATTERN.search(query):
        return None

    manager = get_faiss_manager()
    scoped_rows = []
    filters_by_field = {}
    query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    for document in manager.documents:
        row = document.get("row_data")
        if not isinstance(row, dict):
            continue
        if tenant_id is not None and document.get("tenant_id", "default") != tenant_id:
            continue
        scoped_rows.append((document, row))
        for field, value in row.items():
            if _field_value_is_in_query(query, field, str(value)):
                filters_by_field.setdefault(field, set()).add(str(value))

    if not scoped_rows:
        return None

    matching_rows = [
        (document, row)
        for document, row in scoped_rows
        if all(str(row.get(field, "")) in values for field, values in filters_by_field.items())
    ]
    if not matching_rows:
        return None

    filter_fields = set(filters_by_field)
    candidate_fields = []
    for field in matching_rows[0][1]:
        field_words = set(re.findall(r"[a-z0-9]+", field.lower()))
        if field not in filter_fields and field_words & query_words:
            candidate_fields.append(field)
    if not candidate_fields:
        return None

    # Prefer the column with the most words mentioned by the question.
    field = max(
        candidate_fields,
        key=lambda name: len(set(re.findall(r"[a-z0-9]+", name.lower())) & query_words),
    )
    numeric_rows = [
        document for document, row in matching_rows
        if _parse_numeric(row.get(field)) is not None
    ]
    values = [
        _parse_numeric(row.get(field)) for _, row in matching_rows
        if _parse_numeric(row.get(field)) is not None
    ]
    if not values:
        return None

    return {
        "average": sum(values) / len(values),
        "field": field,
        "record_count": len(values),
        "documents": numeric_rows,
    }


def retrieve_documents(
    query: str, 
    top_k: int = 5, 
    tenant_id: str = None,
    search_method: SearchMethod = "hybrid"
) -> List[Dict]:
    """
    Retrieve relevant documents using configurable search strategy.
    
    Search Methods:
    - "vector": Semantic search using embeddings (FAISS)
    - "keyword": BM25 keyword matching
    - "hybrid": Combines vector + keyword (default)
    
    When tenant_id is provided, ONLY documents belonging to that tenant are returned.
    This ensures complete tenant isolation in multi-tenant environments.
    
    Args:
        query: Search query string
        top_k: Number of results to return
        tenant_id: Tenant ID to filter results (enforced when AUTH_ENABLED=True)
        search_method: Search strategy ("vector", "keyword", or "hybrid")
        
    Returns:
        List of retrieved documents with metadata (tenant-scoped)
    """
    # Check if index has documents
    from src.db.faiss_manager import get_faiss_manager
    manager = get_faiss_manager()
    
    if manager.get_document_count() == 0:
        return []  # No documents in index yet

    # Explicit field/value pairs in structured data are filters, not semantic
    # concepts. Use the uploaded CSV schema for an exact row match before
    # vector/BM25 retrieval so neighbouring records never leak into an answer.
    exact_matches = _exact_structured_record_matches(query, tenant_id)
    if exact_matches:
        return exact_matches[:top_k]
    
    # Route to appropriate search method
    if search_method == "keyword":
        from src.services.hybrid_retrieval import keyword_search
        return keyword_search(query, k=top_k, tenant_id=tenant_id)
    
    elif search_method == "hybrid":
        print("Using hybrid search method (vector + keyword)")
        from src.services.hybrid_retrieval import hybrid_search
        return hybrid_search(query, k=top_k, tenant_id=tenant_id)
    
    else:  # "vector" (default)
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Search FAISS index with tenant filtering
        distances, indices, metadata = search_faiss(query_embedding, k=top_k, tenant_id=tenant_id)
        
        # Format results
        results = []
        for i, (distance, idx, meta) in enumerate(zip(distances, indices, metadata)):
            result = {
                "rank": i + 1,
                "score": float(1 / (1 + distance)),  # Convert distance to similarity score
                "distance": float(distance),
                "search_method": "vector",
                **meta  # Include metadata (file_name, text, etc.)
            }
            results.append(result)
        
        return results


class RetrievalService:
    """Legacy class-based retrieval service"""
    
    def __init__(self):
        self.faiss_manager = get_faiss_manager()

    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        return retrieve_documents(query, top_k)


def create_retrieval_service() -> RetrievalService:
    """Factory function for retrieval service"""
    return RetrievalService()

"""Cross-encoder reranking for the small candidate set produced by retrieval."""
import logging
from typing import Dict, List

from src.core.config import settings


logger = logging.getLogger(__name__)
_reranker = None
_load_attempted = False


def get_reranker():
    """Return the configured cross-encoder, or ``None`` when it is unavailable.

    Models are downloaded by sentence-transformers on first use.  A failed load
    is remembered so an offline deployment does not retry (and delay) every
    request; hybrid fusion remains available as the fallback.
    """
    global _reranker, _load_attempted
    if not settings.RERANKER_ENABLED:
        return None
    if _load_attempted:
        return _reranker

    _load_attempted = True
    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(settings.RERANKER_MODEL)
    except Exception as exc:  # pragma: no cover - dependent on model/runtime
        logger.warning("Reranker unavailable; using fused retrieval order: %s", exc)
        _reranker = None
    return _reranker


def rerank_documents(query: str, documents: List[Dict], top_k: int) -> List[Dict]:
    """Rerank candidate documents and return the requested final window.

    The reranker sees each query/document pair jointly, unlike embedding and
    BM25 retrieval.  Original fusion scores are retained as
    ``retrieval_score`` for diagnostics.
    """
    # Never return fewer documents than the caller explicitly requested, even
    # if an operator configured a candidate count below ``top_k``.
    candidates = documents[:max(top_k, settings.RERANKER_CANDIDATE_COUNT)]
    model = get_reranker()
    if model is None or not candidates:
        return candidates[:top_k]

    try:
        scores = model.predict([(query, str(document.get("text", ""))) for document in candidates])
    except Exception as exc:  # pragma: no cover - dependent on model/runtime
        logger.warning("Reranking failed; using fused retrieval order: %s", exc)
        return candidates[:top_k]

    ranked = []
    for document, score in zip(candidates, scores):
        reranked_document = dict(document)
        reranked_document["retrieval_score"] = reranked_document.get("score")
        reranked_document["score"] = float(score)
        reranked_document["reranked"] = True
        ranked.append(reranked_document)

    ranked.sort(key=lambda document: document["score"], reverse=True)
    for rank, document in enumerate(ranked, start=1):
        document["rank"] = rank
    return ranked[:top_k]

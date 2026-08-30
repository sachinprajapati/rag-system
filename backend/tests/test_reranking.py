import numpy as np

from src.services import reranking
from src.services import hybrid_retrieval


class FakeReranker:
    def predict(self, pairs):
        assert pairs == [("which document?", "first"), ("which document?", "second")]
        return [0.2, 0.9]


def test_rerank_documents_orders_by_cross_encoder_score(monkeypatch):
    monkeypatch.setattr(reranking, "get_reranker", lambda: FakeReranker())
    documents = [
        {"rank": 1, "score": 0.8, "text": "first"},
        {"rank": 2, "score": 0.7, "text": "second"},
    ]

    results = reranking.rerank_documents("which document?", documents, top_k=1)

    assert results == [{
        "rank": 1,
        "score": 0.9,
        "retrieval_score": 0.7,
        "reranked": True,
        "text": "second",
    }]


def test_rerank_documents_keeps_fusion_order_without_model(monkeypatch):
    monkeypatch.setattr(reranking, "get_reranker", lambda: None)
    documents = [{"rank": 1, "score": 0.8, "text": "first"}]

    assert reranking.rerank_documents("query", documents, top_k=1) == documents


def test_hybrid_search_fetches_a_reranking_candidate_pool(monkeypatch):
    requested_counts = []

    class FakeBm25:
        def search(self, query, k, tenant_id):
            requested_counts.append(k)
            return [2.0], [2], [{"text": "keyword candidate"}]

    monkeypatch.setattr(hybrid_retrieval, "generate_embedding", lambda query: np.array([0.1]))
    monkeypatch.setattr(
        hybrid_retrieval,
        "search_faiss",
        lambda embedding, k, tenant_id: (requested_counts.append(k) or ([0.1], [1], [{"text": "vector candidate"}])),
    )
    monkeypatch.setattr(hybrid_retrieval, "get_bm25_engine", lambda: FakeBm25())
    monkeypatch.setattr(
        hybrid_retrieval,
        "rerank_documents",
        lambda query, documents, top_k: documents[:top_k],
    )

    results = hybrid_retrieval.hybrid_search("query", k=2)

    assert requested_counts == [20, 20]
    assert len(results) == 2

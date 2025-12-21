"""Hybrid retrieval combining vector search and keyword search"""
from typing import List, Dict, Tuple
import numpy as np
from src.services.embeddings import generate_embedding
from src.db.faiss_manager import search_faiss
from src.services.bm25_search import get_bm25_engine


def reciprocal_rank_fusion(
    results_list: List[List[Tuple[float, int, Dict]]],
    k: int = 60
) -> List[Tuple[float, int, Dict]]:
    """
    Reciprocal Rank Fusion (RRF) to combine multiple ranked lists.
    
    RRF Score = sum(1 / (k + rank)) for each list where doc appears
    
    Args:
        results_list: List of result lists, each with (score, idx, metadata)
        k: RRF constant (default: 60)
        
    Returns:
        Fused results sorted by RRF score
    """
    # Track RRF scores by document index
    rrf_scores = {}
    doc_metadata = {}
    
    for results in results_list:
        for rank, (score, idx, metadata) in enumerate(results, start=1):
            if idx not in rrf_scores:
                rrf_scores[idx] = 0
                doc_metadata[idx] = metadata
            
            # Add RRF score: 1 / (k + rank)
            rrf_scores[idx] += 1.0 / (k + rank)
    
    # Sort by RRF score (descending)
    sorted_results = sorted(
        [(score, idx, doc_metadata[idx]) for idx, score in rrf_scores.items()],
        key=lambda x: x[0],
        reverse=True
    )
    
    return sorted_results


def weighted_score_fusion(
    vector_results: List[Tuple[float, int, Dict]],
    keyword_results: List[Tuple[float, int, Dict]],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> List[Tuple[float, int, Dict]]:
    """
    Weighted score fusion combining vector and keyword search.
    
    Args:
        vector_results: Vector search results (score, idx, metadata)
        keyword_results: Keyword search results (score, idx, metadata)
        vector_weight: Weight for vector scores (default: 0.7)
        keyword_weight: Weight for keyword scores (default: 0.3)
        
    Returns:
        Fused results sorted by combined score
    """
    # Normalize scores to [0, 1] range
    def normalize_scores(results):
        if not results:
            return []
        scores = [score for score, _, _ in results]
        max_score = max(scores) if scores else 1.0
        min_score = min(scores) if scores else 0.0
        score_range = max_score - min_score if max_score > min_score else 1.0
        
        return [
            ((score - min_score) / score_range, idx, meta)
            for score, idx, meta in results
        ]
    
    # Normalize both result sets
    norm_vector = normalize_scores(vector_results)
    norm_keyword = normalize_scores(keyword_results)
    
    # Build combined scores
    combined_scores = {}
    doc_metadata = {}
    
    # Add vector scores
    for score, idx, metadata in norm_vector:
        combined_scores[idx] = vector_weight * score
        doc_metadata[idx] = metadata
    
    # Add keyword scores
    for score, idx, metadata in norm_keyword:
        if idx in combined_scores:
            combined_scores[idx] += keyword_weight * score
        else:
            combined_scores[idx] = keyword_weight * score
            doc_metadata[idx] = metadata
    
    # Sort by combined score
    sorted_results = sorted(
        [(score, idx, doc_metadata[idx]) for idx, score in combined_scores.items()],
        key=lambda x: x[0],
        reverse=True
    )
    
    return sorted_results


def hybrid_search(
    query: str,
    k: int = 5,
    tenant_id: str = None,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    fusion_method: str = "weighted"
) -> List[Dict]:
    """
    Hybrid retrieval combining vector search (semantic) and keyword search (BM25).
    
    Args:
        query: Search query
        k: Number of results to return
        tenant_id: Optional tenant filter
        vector_weight: Weight for vector search (0-1)
        keyword_weight: Weight for keyword search (0-1)
        fusion_method: "weighted" or "rrf" (Reciprocal Rank Fusion)
        
    Returns:
        List of retrieved documents with hybrid scores
    """
    # 1. Vector search (semantic)
    query_embedding = generate_embedding(query)
    vector_distances, vector_indices, vector_metadata = search_faiss(
        query_embedding, k=k*2, tenant_id=tenant_id
    )
    
    # Convert distances to similarity scores (higher is better)
    vector_results = [
        (float(1 / (1 + dist)), int(idx), meta)
        for dist, idx, meta in zip(vector_distances, vector_indices, vector_metadata)
    ]
    
    # 2. Keyword search (BM25)
    bm25_engine = get_bm25_engine()
    keyword_scores, keyword_indices, keyword_metadata = bm25_engine.search(
        query, k=k*2, tenant_id=tenant_id
    )
    
    keyword_results = [
        (float(score), int(idx), meta)
        for score, idx, meta in zip(keyword_scores, keyword_indices, keyword_metadata)
    ]
    
    # 3. Fusion
    if fusion_method == "rrf":
        fused_results = reciprocal_rank_fusion([vector_results, keyword_results])
    else:  # weighted
        fused_results = weighted_score_fusion(
            vector_results, keyword_results,
            vector_weight, keyword_weight
        )
    
    # 4. Format results
    results = []
    for i, (score, idx, meta) in enumerate(fused_results[:k], 1):
        result = {
            "rank": i,
            "score": float(score),
            "search_method": "hybrid",
            **meta
        }
        results.append(result)
    
    return results


def keyword_search(query: str, k: int = 5, tenant_id: str = None) -> List[Dict]:
    """
    Pure keyword search using BM25.
    
    Args:
        query: Search query
        k: Number of results
        tenant_id: Optional tenant filter
        
    Returns:
        List of retrieved documents
    """
    bm25_engine = get_bm25_engine()
    scores, indices, metadata = bm25_engine.search(query, k=k, tenant_id=tenant_id)
    
    results = []
    for i, (score, idx, meta) in enumerate(zip(scores, indices, metadata), 1):
        result = {
            "rank": i,
            "score": float(score),
            "search_method": "keyword",
            **meta
        }
        results.append(result)
    
    return results

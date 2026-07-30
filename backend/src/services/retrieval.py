"""Document retrieval service with multiple search strategies"""
from typing import List, Dict, Literal
import numpy as np
from src.services.embeddings import generate_embedding
from src.db.faiss_manager import get_faiss_manager, search_faiss

SearchMethod = Literal["vector", "keyword", "hybrid"]


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
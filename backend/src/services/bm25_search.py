"""BM25 keyword search implementation"""
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
import numpy as np
from src.db.faiss_manager import get_faiss_manager


class BM25SearchEngine:
    """BM25 keyword-based search engine for documents"""
    
    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []
        self._build_index()
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (lowercase + split)"""
        return text.lower().split()
    
    def _build_index(self):
        """Build BM25 index from FAISS documents"""
        manager = get_faiss_manager()
        
        if not manager.documents:
            return
        
        self.documents = manager.documents
        self.tokenized_corpus = [
            self._tokenize(doc.get("text", "")) 
            for doc in self.documents
        ]
        
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search(self, query: str, k: int = 5, tenant_id: str = None) -> Tuple[List[float], List[int], List[Dict]]:
        """
        Search using BM25 keyword matching.
        
        Args:
            query: Search query
            k: Number of results
            tenant_id: Optional tenant filter
            
        Returns:
            Tuple of (scores, indices, metadata)
        """
        if not self.bm25 or not self.documents:
            return [], [], []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices with tenant filtering
        if tenant_id:
            # Filter by tenant and get top-k
            filtered_results = []
            for idx, score in enumerate(scores):
                if idx < len(self.documents):
                    doc_tenant = self.documents[idx].get("tenant_id", "default")
                    if doc_tenant == tenant_id:
                        filtered_results.append((score, idx))
            
            # Sort by score and take top-k
            filtered_results.sort(reverse=True, key=lambda x: x[0])
            filtered_results = filtered_results[:k]
            
            result_scores = [score for score, _ in filtered_results]
            result_indices = [idx for _, idx in filtered_results]
        else:
            # No tenant filtering - get top-k globally
            top_indices = np.argsort(scores)[::-1][:k]
            result_scores = [scores[idx] for idx in top_indices]
            result_indices = top_indices.tolist()
        
        # Get metadata
        result_metadata = [
            self.documents[idx] if idx < len(self.documents) else {}
            for idx in result_indices
        ]
        
        return result_scores, result_indices, result_metadata
    
    def rebuild_index(self):
        """Rebuild BM25 index (call after documents change)"""
        self._build_index()


# Global instance
_bm25_engine = None


def get_bm25_engine() -> BM25SearchEngine:
    """Get or create global BM25 engine"""
    global _bm25_engine
    if _bm25_engine is None:
        _bm25_engine = BM25SearchEngine()
    return _bm25_engine


def rebuild_bm25_index():
    """Force rebuild of BM25 index"""
    global _bm25_engine
    if _bm25_engine:
        _bm25_engine.rebuild_index()

"""FAISS vector database manager"""
from typing import List, Tuple, Optional
import faiss
import numpy as np
import pickle
from pathlib import Path
from src.core.config import settings


class FAISSManager:
    """Manager for FAISS vector index operations"""
    
    def __init__(self, dimension: int = 384):  # all-MiniLM-L6-v2 dimension
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.documents = []  # Store document metadata
        self.index_path = Path(settings.FAISS_INDEX_PATH)
        self.index_path.mkdir(parents=True, exist_ok=True)

    def add_embeddings(self, embeddings: np.ndarray, metadata: Optional[List[dict]] = None):
        """
        Add embeddings to the index.
        
        Args:
            embeddings: numpy array of embeddings
            metadata: optional list of document metadata
        """
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        embeddings_float = embeddings.astype('float32')
        self.index.add(embeddings_float)
        
        if metadata:
            self.documents.extend(metadata)

    def search(self, query_embedding: np.ndarray, k: int = 5, tenant_id: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors with strict tenant filtering.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            tenant_id: Tenant ID to filter results (None returns all for backward compatibility)
            
        Returns:
            Tuple of (distances, indices) - ALWAYS filtered by tenant_id if provided
        """
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        query_float = query_embedding.astype('float32')
        
        # If no tenant filtering, search all (only for backward compatibility)
        if tenant_id is None:
            distances, indices = self.index.search(query_float, k)
            return distances[0], indices[0]
        
        # Search with more results to filter by tenant
        search_k = min(k * 10, self.index.ntotal)  # Get 10x results for filtering
        if search_k == 0:
            return np.array([]), np.array([])
            
        distances, indices = self.index.search(query_float, search_k)
        
        # Filter by tenant_id
        filtered_distances = []
        filtered_indices = []
        
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc_tenant = self.documents[idx].get("tenant_id", "default")
                if doc_tenant == tenant_id:
                    filtered_distances.append(dist)
                    filtered_indices.append(idx)
                    if len(filtered_indices) >= k:
                        break
        
        return np.array(filtered_distances), np.array(filtered_indices)

    def save(self, index_name: str = "vector_index"):
        """Save index and metadata to disk"""
        index_file = self.index_path / f"{index_name}.faiss"
        metadata_file = self.index_path / f"{index_name}_metadata.pkl"
        
        faiss.write_index(self.index, str(index_file))
        with open(metadata_file, 'wb') as f:
            pickle.dump(self.documents, f)

    def load(self, index_name: str = "vector_index"):
        """Load index and metadata from disk"""
        index_file = self.index_path / f"{index_name}.faiss"
        metadata_file = self.index_path / f"{index_name}_metadata.pkl"
        
        if index_file.exists():
            self.index = faiss.read_index(str(index_file))
        
        if metadata_file.exists():
            with open(metadata_file, 'rb') as f:
                self.documents = pickle.load(f)

    def reset(self):
        """Reset the index"""
        self.index.reset()
        self.documents = []
    
    def get_document_count(self) -> int:
        """Get number of vectors in index"""
        return self.index.ntotal


# Global instance
_faiss_manager = None


def get_faiss_manager() -> FAISSManager:
    """Get or create global FAISS manager instance"""
    global _faiss_manager
    if _faiss_manager is None:
        _faiss_manager = FAISSManager()
        # Try to load existing index
        try:
            _faiss_manager.load()
        except:
            pass
    return _faiss_manager


def add_embeddings_to_faiss(embeddings: np.ndarray, metadata: Optional[List[dict]] = None):
    """Add embeddings to FAISS index (standalone function)"""
    manager = get_faiss_manager()
    manager.add_embeddings(embeddings, metadata)
    manager.save()


def search_faiss(query_embedding: np.ndarray, k: int = 5, tenant_id: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, List[dict]]:
    """Search FAISS index with optional tenant filtering"""
    manager = get_faiss_manager()
    distances, indices = manager.search(query_embedding, k, tenant_id=tenant_id)
    
    # Get metadata for results
    results_metadata = []
    for idx in indices:
        if idx < len(manager.documents):
            results_metadata.append(manager.documents[idx])
        else:
            results_metadata.append({})
    
    return distances, indices, results_metadata
"""Embedding service using Sentence Transformers"""
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
from src.core.config import settings


# Global model instance
_model = None


def get_model() -> SentenceTransformer:
    """Get or initialize the embedding model"""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def generate_embeddings(texts: Union[str, List[str]]) -> np.ndarray:
    """
    Generate embeddings for one or more texts.
    
    Args:
        texts: Single text string or list of texts
        
    Returns:
        numpy array of embeddings
    """
    model = get_model()
    if isinstance(texts, str):
        texts = [texts]
    return model.encode(texts, convert_to_tensor=False, show_progress_bar=False)


def generate_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text string
        
    Returns:
        numpy array embedding vector
    """
    return generate_embeddings([text])[0]


class EmbeddingService:
    """Legacy class-based interface for embeddings"""
    
    def __init__(self):
        self.model = get_model()

    def generate_embeddings(self, texts):
        return generate_embeddings(texts)

    def generate_embedding(self, text):
        return generate_embedding(text)
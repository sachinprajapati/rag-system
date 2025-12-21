"""Document ingestion service with advanced chunking and preprocessing"""
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from src.utils.pdf_parser import parse_pdf
from src.utils.text_splitter import split_text_with_metadata, estimate_tokens
from src.services.embeddings import generate_embeddings
from src.db.faiss_manager import add_embeddings_to_faiss
from src.services.bm25_search import rebuild_bm25_index


def ingest_document(file_path: str, chunk_size: int = 650, chunk_overlap: int = 125, 
                   tenant_id: str = "default", user_id: str = None) -> Dict:
    """
    Ingest a single document with advanced chunking, deduplication, and normalization.
    
    Features:
    - Token-based chunking (500-800 tokens per chunk)
    - Smart overlap (100-150 tokens)
    - Automatic deduplication
    - Text normalization
    - Rich metadata attachment
    - Tenant isolation
    
    Args:
        file_path: Path to the document
        chunk_size: Target chunk size in tokens (default: 650, range: 500-800)
        chunk_overlap: Overlap in tokens (default: 125, range: 100-150)
        tenant_id: Tenant ID for multi-tenancy (REQUIRED for isolation)
        user_id: User ID who uploaded the document
        
    Returns:
        Dictionary with ingestion results including tenant_id and chunk statistics
    """
    try:
        # Parse the PDF
        text = parse_pdf(file_path)
        
        if not text or len(text.strip()) == 0:
            raise ValueError("No text extracted from document")
        
        # Prepare source metadata
        file_name = Path(file_path).name
        source_metadata = {
            "file_path": file_path,
            "file_name": file_name,
            "tenant_id": tenant_id,
            "uploaded_by": user_id,
            "upload_timestamp": datetime.utcnow().isoformat()
        }
        
        # Split into chunks with metadata and deduplication
        chunks_with_metadata = split_text_with_metadata(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            source_metadata=source_metadata
        )
        
        # Extract text for embedding generation
        chunk_texts = [chunk["text"] for chunk in chunks_with_metadata]
        
        # Generate embeddings for chunks
        embeddings = generate_embeddings(chunk_texts)
        
        # Add to FAISS index with full metadata
        add_embeddings_to_faiss(embeddings, chunks_with_metadata)
        
        # Rebuild BM25 index for keyword search
        rebuild_bm25_index()
        
        # Calculate statistics
        total_tokens = sum(chunk["token_count_estimate"] for chunk in chunks_with_metadata)
        avg_chunk_size = total_tokens // len(chunks_with_metadata) if chunks_with_metadata else 0
        
        return {
            "status": "success",
            "file_name": file_name,
            "chunks_processed": len(chunks_with_metadata),
            "total_characters": len(text),
            "total_tokens_estimate": total_tokens,
            "avg_chunk_tokens": avg_chunk_size,
            "chunk_size_config": chunk_size,
            "chunk_overlap_config": chunk_overlap,
            "deduplication_enabled": True,
            "normalization_enabled": True,
            "tenant_id": tenant_id
        }
        
    except Exception as e:
        return {
            "status": "error",
            "file_name": Path(file_path).name if file_path else "unknown",
            "error": str(e)
        }


def ingest_documents(file_paths: List[str]) -> List[Dict]:
    """
    Ingest multiple documents.
    
    Args:
        file_paths: List of document paths
        
    Returns:
        List of ingestion results
    """
    results = []
    for file_path in file_paths:
        result = ingest_document(file_path)
        results.append(result)
    return results
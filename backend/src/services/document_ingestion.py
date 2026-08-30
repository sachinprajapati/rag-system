"""Document ingestion service with advanced chunking and preprocessing"""
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from src.utils.document_router import route_and_chunk_document
from src.services.embeddings import generate_embeddings
from src.db.faiss_manager import add_embeddings_to_faiss
from src.services.bm25_search import rebuild_bm25_index


def ingest_document(file_path: str, chunk_size: int = 700, chunk_overlap: int = 140,
                   tenant_id: str = "default", user_id: str = None,
                   original_file_name: str | None = None) -> Dict:
    """
    Ingest a single document with advanced chunking, deduplication, and normalization.
    
    Features:
    - File-aware structural or recursive character chunking
    - 700-character chunks with 140-character overlap for prose documents
    - Parent-child table chunks for PDFs with detected tables
    - Rich metadata attachment
    - Tenant isolation
    
    Args:
        file_path: Path to the document
        chunk_size: Retained for API compatibility; prose routing uses 700.
        chunk_overlap: Retained for API compatibility; prose routing uses 140.
        tenant_id: Tenant ID for multi-tenancy (REQUIRED for isolation)
        user_id: User ID who uploaded the document
        
    Returns:
        Dictionary with ingestion results including tenant_id and chunk statistics
    """
    try:
        file_type, chunks_with_metadata, text = route_and_chunk_document(file_path)
        
        # Prepare source metadata
        file_name = original_file_name or Path(file_path).name
        source_metadata = {
            "file_path": file_path,
            "file_name": file_name,
            "tenant_id": tenant_id,
            "uploaded_by": user_id,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "file_size_bytes": Path(file_path).stat().st_size,
            "file_type": file_type,
            "source_path": file_path,
        }
        
        for chunk in chunks_with_metadata:
            chunk.update(source_metadata)
        
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
        page_numbers = [chunk.get("page_number") for chunk in chunks_with_metadata if chunk.get("page_number")]
        
        return {
            "status": "success",
            "file_name": file_name,
            "chunks_processed": len(chunks_with_metadata),
            "total_characters": len(text),
            "total_tokens_estimate": total_tokens,
            "avg_chunk_tokens": avg_chunk_size,
            "chunk_size_config": 700,
            "chunk_overlap_config": 140,
            "file_type_detected": file_type,
            "page_count": max(page_numbers) if page_numbers else None,
            "file_size_bytes": source_metadata["file_size_bytes"],
            "chunking_strategy": (
                "parent_child_tables"
                if any(chunk["chunking_strategy"] == "parent_child_tables" for chunk in chunks_with_metadata)
                else chunks_with_metadata[0]["chunking_strategy"] if chunks_with_metadata else "none"
            ),
            "deduplication_enabled": False,
            "normalization_enabled": False,
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

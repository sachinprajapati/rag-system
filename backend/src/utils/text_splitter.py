"""Advanced text splitting utilities with token-based chunking and preprocessing"""
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import hashlib
from datetime import datetime


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace and standardizing format.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    # Remove multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace from each line
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # Remove extra spaces around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    return text.strip()


def calculate_chunk_hash(text: str) -> str:
    """
    Calculate hash for deduplication.
    
    Args:
        text: Chunk text
        
    Returns:
        MD5 hash of normalized text
    """
    normalized = normalize_text(text.lower())
    return hashlib.md5(normalized.encode()).hexdigest()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: ~4 chars per token).
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    # Simple heuristic: average 4 characters per token for English
    # For more accuracy, use tiktoken library
    return len(text) // 4


def split_text(text: str, chunk_size: int = 650, chunk_overlap: int = 125) -> List[str]:
    """
    Split text into chunks using token-based splitting with overlap.
    
    Default settings:
    - chunk_size: 650 tokens (2600 chars) - middle of 500-800 range
    - chunk_overlap: 125 tokens (500 chars) - middle of 100-150 range
    
    Args:
        text: Input text to split
        chunk_size: Target size in tokens (500-800 recommended)
        chunk_overlap: Overlap in tokens (100-150 recommended)
        
    Returns:
        List of text chunks
    """
    # Normalize text first
    text = normalize_text(text)
    
    # Convert token counts to character counts (rough approximation)
    char_chunk_size = chunk_size * 4
    char_chunk_overlap = chunk_overlap * 4
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=char_chunk_size,
        chunk_overlap=char_chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],  # Prioritize semantic boundaries
        keep_separator=True
    )
    
    return text_splitter.split_text(text)


def split_text_with_metadata(
    text: str, 
    chunk_size: int = 650,
    chunk_overlap: int = 125,
    source_metadata: Optional[Dict] = None
) -> List[Dict]:
    """
    Split text into chunks with rich metadata and deduplication.
    
    Args:
        text: Input text to split
        chunk_size: Target size in tokens (500-800 recommended)
        chunk_overlap: Overlap in tokens (100-150 recommended)
        source_metadata: Additional metadata to attach to each chunk
        
    Returns:
        List of dictionaries with chunk text and metadata
    """
    # Split text into chunks
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Track seen hashes for deduplication
    seen_hashes = set()
    unique_chunks = []
    
    for i, chunk in enumerate(chunks):
        # Calculate hash for deduplication
        chunk_hash = calculate_chunk_hash(chunk)
        
        # Skip duplicate chunks
        if chunk_hash in seen_hashes:
            continue
        
        seen_hashes.add(chunk_hash)
        
        # Build metadata
        metadata = {
            "chunk_index": len(unique_chunks),
            "text": chunk,
            "char_count": len(chunk),
            "token_count_estimate": estimate_tokens(chunk),
            "chunk_hash": chunk_hash,
            "created_at": datetime.utcnow().isoformat(),
            "normalized": True
        }
        
        # Add source metadata if provided
        if source_metadata:
            metadata.update(source_metadata)
        
        unique_chunks.append(metadata)
    
    return unique_chunks


def deduplicate_chunks(chunks: List[str]) -> List[str]:
    """
    Remove duplicate chunks based on content hash.
    
    Args:
        chunks: List of text chunks
        
    Returns:
        List of unique chunks
    """
    seen_hashes = set()
    unique_chunks = []
    
    for chunk in chunks:
        chunk_hash = calculate_chunk_hash(chunk)
        if chunk_hash not in seen_hashes:
            seen_hashes.add(chunk_hash)
            unique_chunks.append(chunk)
    
    return unique_chunks
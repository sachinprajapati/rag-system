# Advanced Chunking & Preprocessing Implementation

## Overview
Implemented production-grade text chunking with token-based splitting, metadata enrichment, deduplication, and normalization.

## Configuration

### Chunk Size: 500-800 Tokens
- **Default**: 650 tokens (middle of range)
- **Character Approximation**: ~2600 characters (4 chars/token)
- **Adjustable** via `chunk_size` parameter

### Overlap: 100-150 Tokens  
- **Default**: 125 tokens (middle of range)
- **Character Approximation**: ~500 characters
- **Maintains context** between chunks

## Features Implemented

### 1. ✅ Token-Based Chunking
**File**: [text_splitter.py](backend/src/utils/text_splitter.py)

```python
def split_text(text: str, chunk_size: int = 650, chunk_overlap: int = 125):
    """
    Default: 650 tokens per chunk (range: 500-800)
    Overlap: 125 tokens (range: 100-150)
    """
```

**Token Estimation**:
- Rough approximation: 1 token ≈ 4 characters
- Configurable for different languages
- Actual count stored in metadata

### 2. ✅ Text Normalization
**Function**: `normalize_text()`

**Operations**:
- Remove multiple spaces → single space
- Limit consecutive newlines (max 2)
- Strip leading/trailing whitespace
- Fix spacing around punctuation
- Standardize formatting

**Example**:
```python
Input:  "Hello    world.\n\n\n\nNext   paragraph."
Output: "Hello world.\n\nNext paragraph."
```

### 3. ✅ Metadata Attachment
**Function**: `split_text_with_metadata()`

**Metadata Fields**:
```python
{
    "chunk_index": 0,           # Sequential index
    "text": "chunk content",    # Actual text
    "char_count": 2543,         # Character count
    "token_count_estimate": 635, # Estimated tokens
    "chunk_hash": "md5hash",    # For deduplication
    "created_at": "2025-12-21T...", # Timestamp
    "normalized": True,         # Normalization flag
    
    # Source metadata
    "file_name": "document.pdf",
    "file_path": "/path/to/doc",
    "tenant_id": "tenant-123",
    "uploaded_by": "user-456",
    "upload_timestamp": "2025-12-21T..."
}
```

### 4. ✅ Deduplication
**Function**: `deduplicate_chunks()`

**Method**:
- Calculate MD5 hash of normalized text
- Track seen hashes in set
- Skip duplicate chunks automatically
- Case-insensitive comparison

**Benefits**:
- Removes redundant information
- Reduces storage/compute costs
- Improves retrieval relevance

### 5. ✅ Smart Splitting Strategy
**Separator Priority** (semantic boundaries):
1. `\n\n` - Paragraph breaks
2. `\n` - Line breaks
3. `. ` - Sentence endings
4. ` ` - Word boundaries
5. `""` - Character level (fallback)

**Advantages**:
- Preserves semantic meaning
- Maintains readability
- Better context for embeddings

## Usage

### Basic Usage
```python
from src.utils.text_splitter import split_text

text = "Your long document text..."
chunks = split_text(text, chunk_size=650, chunk_overlap=125)
```

### With Metadata
```python
from src.utils.text_splitter import split_text_with_metadata

chunks = split_text_with_metadata(
    text,
    chunk_size=700,  # 700 tokens
    chunk_overlap=150,  # 150 token overlap
    source_metadata={
        "file_name": "report.pdf",
        "tenant_id": "acme-corp"
    }
)

# Each chunk has full metadata
chunk = chunks[0]
print(f"Text: {chunk['text']}")
print(f"Tokens: {chunk['token_count_estimate']}")
print(f"Hash: {chunk['chunk_hash']}")
```

### Document Ingestion
```python
from src.services.document_ingestion import ingest_document

result = ingest_document(
    file_path="/path/to/document.pdf",
    chunk_size=650,      # 650 tokens per chunk
    chunk_overlap=125,   # 125 token overlap
    tenant_id="tenant-123",
    user_id="user-456"
)

# Returns detailed statistics
{
    "status": "success",
    "chunks_processed": 45,
    "total_tokens_estimate": 29250,
    "avg_chunk_tokens": 650,
    "deduplication_enabled": True,
    "normalization_enabled": True
}
```

## Configuration Options

### Adjusting Chunk Size
```python
# Smaller chunks (more granular)
chunks = split_text(text, chunk_size=500, chunk_overlap=100)

# Larger chunks (more context)
chunks = split_text(text, chunk_size=800, chunk_overlap=150)
```

### Custom Overlap
```python
# Minimal overlap (faster, less redundancy)
chunks = split_text(text, chunk_size=650, chunk_overlap=100)

# Maximum overlap (better context continuity)
chunks = split_text(text, chunk_size=650, chunk_overlap=150)
```

## Performance Characteristics

### Chunk Size Impact
| Size | Chunks Created | Embedding Cost | Context Quality |
|------|---------------|----------------|-----------------|
| 500  | More          | Higher         | Focused         |
| 650  | Moderate      | Balanced       | Balanced ✅     |
| 800  | Fewer         | Lower          | Broad           |

### Overlap Impact
| Overlap | Redundancy | Context Preservation | Storage |
|---------|------------|---------------------|---------|
| 100     | Lower      | Good               | Efficient |
| 125     | Moderate   | Better ✅          | Balanced |
| 150     | Higher     | Best               | More     |

## Integration

### Document Upload Flow
```
1. PDF uploaded → parse_pdf()
2. Text extracted → normalize_text()
3. Split into chunks → split_text_with_metadata()
4. Deduplication → deduplicate_chunks() (automatic)
5. Generate embeddings → generate_embeddings()
6. Store in FAISS → add_embeddings_to_faiss()
```

### Query Flow
```
1. User query → normalize_text()
2. Generate query embedding
3. Search FAISS (with tenant filtering)
4. Retrieve chunks with metadata
5. Return results with token counts
```

## Metadata Benefits

### For Retrieval
- **chunk_index**: Reconstruct document order
- **token_count**: Filter by size constraints
- **chunk_hash**: Identify duplicates
- **file_name**: Source attribution

### For Analytics
- **created_at**: Track ingestion time
- **uploaded_by**: Audit trail
- **tenant_id**: Multi-tenant isolation
- **char_count**: Storage metrics

### For Debugging
- **normalized**: Verify preprocessing
- **token_count_estimate**: Validate chunking
- **chunk_hash**: Identify identical content

## Testing

### Test Token Counts
```python
from src.utils.text_splitter import estimate_tokens

text = "This is a test sentence with approximately ten words here."
tokens = estimate_tokens(text)  # ~14 tokens
```

### Test Deduplication
```python
text = "Same content.\n\nSame content."  # Duplicate paragraphs
chunks = split_text_with_metadata(text)
# Returns only 1 unique chunk
```

### Test Normalization
```python
from src.utils.text_splitter import normalize_text

messy = "Hello    world.\n\n\n\nNext   line."
clean = normalize_text(messy)
# "Hello world.\n\nNext line."
```

## Best Practices

### ✅ Do:
- Use 650 tokens for general documents
- Enable normalization for consistency
- Rely on automatic deduplication
- Include rich metadata for analytics
- Use semantic separators for better context

### ❌ Don't:
- Go below 500 tokens (too fragmented)
- Exceed 800 tokens (context gets diluted)
- Skip normalization (inconsistent embeddings)
- Ignore token counts (LLM context limits)

## Future Enhancements

### Token Counting
- Integrate `tiktoken` for accurate GPT token counts
- Support different tokenizers (BERT, Llama, etc.)

### Advanced Normalization
- Language-specific rules
- Custom regex patterns
- Entity preservation

### Smart Chunking
- Semantic similarity-based splitting
- Paragraph/section boundary detection
- Table/list structure preservation

## Summary

✅ **Token-based chunking**: 500-800 tokens (default: 650)
✅ **Smart overlap**: 100-150 tokens (default: 125)
✅ **Rich metadata**: 12+ fields per chunk
✅ **Automatic deduplication**: Hash-based duplicate detection
✅ **Text normalization**: Whitespace & formatting cleanup
✅ **Semantic boundaries**: Priority-based separator selection
✅ **Production-ready**: Full integration with ingestion pipeline

The system now provides enterprise-grade text preprocessing with optimal chunk sizes for embedding quality and retrieval performance.

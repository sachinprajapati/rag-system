"""Response generation service (RAG)"""
from typing import List, Dict, Literal
from src.services.retrieval import retrieve_documents

SearchMethod = Literal["vector", "keyword", "hybrid"]


def generate_response(
    query: str, 
    top_k: int = 5, 
    tenant_id: str = None,
    search_method: SearchMethod = "hybrid"
) -> Dict:
    """
    Generate a response for a query by retrieving relevant documents.
    
    Note: This is a simplified version. For full RAG with LLM generation,
    integrate with OpenAI, Anthropic, or local LLMs.
    
    Args:
        query: User query
        top_k: Number of documents to retrieve
        tenant_id: Optional tenant ID for filtering
        search_method: Search strategy ("vector", "keyword", or "hybrid")
        
    Returns:
        Dictionary with query results and context
    """
    # Retrieve relevant documents with tenant filtering and selected search method
    documents = retrieve_documents(
        query, 
        top_k=top_k, 
        tenant_id=tenant_id,
        search_method=search_method
    )
    
    # Check if any documents were retrieved
    if not documents:
        return {
            "query": query,
            "retrieved_documents": [],
            "answer": "No documents have been uploaded yet. Please upload PDF documents first to query the system.",
            "sources": []
        }
    
    # For now, return the retrieved documents as context
    # In a full RAG system, you would pass this to an LLM for generation
    response = {
        "query": query,
        "retrieved_documents": documents,
        "answer": format_simple_answer(documents),
        "sources": [doc.get("file_name", "unknown") for doc in documents]
    }
    
    return response


def format_simple_answer(documents: List[Dict]) -> str:
    """
    Format a simple answer from retrieved documents.
    
    Args:
        documents: List of retrieved documents
        
    Returns:
        Formatted answer string
    """
    if not documents:
        return "No relevant documents found."
    
    # Combine text from top documents
    context_parts = []
    for i, doc in enumerate(documents[:3], 1):
        text = doc.get("text", "")
        if text:
            context_parts.append(f"[Source {i}]: {text[:200]}...")
    
    if not context_parts:
        return "No relevant content found in documents."
    
    answer = "\n\n".join(context_parts)
    return answer


class RAGGenerator:
    """Legacy class for backward compatibility"""
    
    def generate_response(self, query: str) -> str:
        result = generate_response(query)
        return result.get("answer", "")
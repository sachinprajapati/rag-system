from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal
from src.services.retrieval import retrieve_documents
from src.services.generation import generate_response
from src.services.chat_history import get_chat_history_service
from src.core.auth import get_current_user, TokenData, get_optional_user, require_user
from src.core.config import settings

router = APIRouter()

SearchMethod = Literal["vector", "keyword", "hybrid"]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    search_method: SearchMethod = "hybrid"  # "vector", "keyword", or "hybrid"


class QueryResponse(BaseModel):
    query: str
    retrieved_documents: List[Dict]
    answer: str
    sources: List[str]
    tenant_id: Optional[str] = None


@router.post("", response_model=QueryResponse)
async def query_rag_system(
    request: QueryRequest,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Query the RAG system with configurable search method.
    
    Search Methods:
    - "vector": Semantic search using embeddings (FAISS)
    - "keyword": BM25 keyword matching  
    - "hybrid": Combines vector + keyword (default, recommended)
    
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    Results are scoped to user's tenant_id.
    Chat history is automatically stored.
    """
    try:
        # Get tenant ID for filtering (mandatory when auth enabled)
        tenant_id = user.tenant_id if user else None
        
        # Enforce tenant isolation when AUTH_ENABLED=True
        if settings.AUTH_ENABLED and not tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID required for authenticated requests")
        
        # Generate response using RAG with strict tenant filtering and selected search method
        result = generate_response(
            request.query, 
            top_k=request.top_k, 
            tenant_id=tenant_id,
            search_method=request.search_method
        )
        
        # Add tenant info if authenticated
        if user:
            result["tenant_id"] = user.tenant_id
            
            # Store in chat history
            try:
                chat_service = get_chat_history_service()
                chat_service.add_message(
                    user_id=user.user_id,
                    tenant_id=user.tenant_id,
                    query=request.query,
                    answer=result["answer"],
                    sources=result["sources"]
                )
            except Exception as e:
                # Log but don't fail the request if history storage fails
                print(f"Failed to store chat history: {e}")
        
        return QueryResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    limit: int = 50,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get chat history for the current user.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        chat_service = get_chat_history_service()
        history = chat_service.get_history(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            limit=limit
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_chat_history(
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Clear chat history for the current user.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        chat_service = get_chat_history_service()
        chat_service.clear_history(
            user_id=user.user_id,
            tenant_id=user.tenant_id
        )
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
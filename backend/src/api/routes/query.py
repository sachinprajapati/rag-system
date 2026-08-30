from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal
import traceback
from src.services.retrieval import retrieve_documents
from src.services.generation import generate_response
from src.services.chat_history import get_chat_history_service
from src.services.monitoring import get_monitoring_service
from src.core.auth import get_current_user, TokenData, get_optional_user, require_user
from src.core.config import settings

router = APIRouter()

SearchMethod = Literal["vector", "keyword", "hybrid"]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    search_method: SearchMethod = "hybrid"  # "vector", "keyword", or "hybrid"
    conversation_id: Optional[str] = None  # Optional conversation ID


class QueryResponse(BaseModel):
    query: str
    retrieved_documents: List[Dict]
    answer: str
    sources: List[str]
    tenant_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Include conversation ID in response
    table: Optional[Dict] = None


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
    Monitored for latency, errors, and hallucinations.
    """
    monitoring = get_monitoring_service()
    
    # Start overall query timer
    query_start = monitoring.start_timer()
    retrieval_latency_ms = 0
    generation_latency_ms = 0
    error_occurred = None
    
    try:
        # Get tenant ID for filtering (mandatory when auth enabled)
        tenant_id = user.tenant_id if user else None
        user_id = user.user_id if user else "default_user"
        chat_tenant_id = user.tenant_id if user else "default_tenant"
        
        # Enforce tenant isolation when AUTH_ENABLED=True
        if settings.AUTH_ENABLED and not tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID required for authenticated requests")
        
        # Track retrieval latency
        retrieval_start = monitoring.start_timer()
        
        # Generate response using RAG with strict tenant filtering and selected search method
        result = await generate_response(
            request.query, 
            top_k=request.top_k, 
            tenant_id=tenant_id,
            search_method=request.search_method
        )
        
        # Log retrieval latency
        retrieval_latency_ms = monitoring.end_timer(retrieval_start)
        monitoring.log_latency(
            operation="retrieval",
            start_time=retrieval_start,
            success=True,
            metadata={
                "search_method": request.search_method,
                "top_k": request.top_k,
                "docs_retrieved": len(result.get("retrieved_documents", []))
            }
        )
        
        # Track generation latency (approximate - included in retrieval)
        generation_latency_ms = retrieval_latency_ms * 0.3  # Estimate 30% for generation
        
        # Add tenant info if authenticated
        if user:
            result["tenant_id"] = user.tenant_id
        
        # Store in chat history with conversation support (always store, even without auth)
        try:
            chat_service = get_chat_history_service()
            message = chat_service.add_message(
                user_id=user_id,
                tenant_id=chat_tenant_id,
                query=request.query,
                answer=result["answer"],
                sources=result["sources"],
                conversation_id=request.conversation_id,
                search_method=request.search_method,
                metadata={
                    "top_k": request.top_k,
                    "retrieved_docs_count": len(result["retrieved_documents"]),
                    "table": result.get("table"),
                    # Preserve the exact passages used for the answer so a
                    # reopened conversation can still show a citation preview.
                    "citation_documents": [
                        {
                            key: document[key]
                            for key in (
                                "file_name", "text", "score", "rank", "search_method",
                                "chunk_index", "page_number", "row_number", "chunk_role",
                            )
                            if key in document
                        }
                        for document in result["retrieved_documents"]
                    ],
                }
            )
            # Include conversation_id in response
            result["conversation_id"] = message.conversation_id
        except Exception as e:
            # Log but don't fail the request if history storage fails
            print(f"Failed to store chat history: {e}")
        
        # Log overall query with monitoring
        total_latency_ms = monitoring.end_timer(query_start)
        monitoring.log_query(
            user_id=user_id,
            tenant_id=chat_tenant_id,
            query=request.query,
            answer=result["answer"],
            retrieved_docs_count=len(result["retrieved_documents"]),
            search_method=request.search_method,
            top_k=request.top_k,
            latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            sources_used=result["sources"],
            conversation_id=result.get("conversation_id"),
            error=None,
            metadata={"auth_enabled": settings.AUTH_ENABLED}
        )
        
        # Log successful query latency
        monitoring.log_latency(
            operation="query",
            start_time=query_start,
            success=True,
            metadata={
                "search_method": request.search_method,
                "has_conversation": request.conversation_id is not None
            }
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        error_occurred = str(e)
        
        # Log error with monitoring
        monitoring.log_error(
            error_type=type(e).__name__,
            error_message=str(e),
            operation="query",
            user_id=user_id if 'user_id' in locals() else "unknown",
            tenant_id=chat_tenant_id if 'chat_tenant_id' in locals() else "unknown",
            stack_trace=traceback.format_exc()
        )
        
        # Log failed query latency
        if 'query_start' in locals():
            monitoring.log_latency(
                operation="query",
                start_time=query_start,
                success=False,
                error=error_occurred
            )
        
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
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        history = chat_service.get_history(
            user_id=user_id,
            tenant_id=tenant_id,
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
    Clear all chat history for the current user.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        chat_service.clear_history(
            user_id=user_id,
            tenant_id=tenant_id
        )
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Conversation Management Endpoints

@router.post("/conversations")
async def create_conversation(
    title: Optional[str] = None,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Create a new conversation.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        conversation = chat_service.create_conversation(
            user_id=user_id,
            tenant_id=tenant_id,
            title=title
        )
        return conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations(
    limit: int = 50,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    List all conversations for the current user.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        conversations = chat_service.list_conversations(
            user_id=user_id,
            tenant_id=tenant_id,
            limit=limit
        )
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get a specific conversation with all messages.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        conversation = chat_service.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    title: str,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Update conversation title.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        success = chat_service.update_conversation_title(
            conversation_id=conversation_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_title=title
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: TokenData = Depends(require_user) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Delete a specific conversation.
    Requires USER or ADMIN role when AUTH_ENABLED=True.
    """
    # When auth is disabled, use default user/tenant
    user_id = user.user_id if user else "default_user"
    tenant_id = user.tenant_id if user else "default_tenant"
    
    try:
        chat_service = get_chat_history_service()
        success = chat_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

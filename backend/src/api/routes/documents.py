from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from src.services.document_ingestion import ingest_document
from src.services.retrieval import retrieve_documents
from src.models.document import Document
from src.models.query import Query
from src.core.auth import get_current_user, TokenData, get_optional_user, require_admin, require_viewer
from src.core.config import settings
from src.db.faiss_manager import get_faiss_manager

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Upload and ingest a document.
    Requires ADMIN role when AUTH_ENABLED=True.
    Documents are scoped to user's tenant_id.
    """
    try:
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Get tenant and user info
            tenant_id = user.tenant_id if user else "default"
            user_id = user.user_id if user else None
            
            # Ingest document with tenant info
            result = ingest_document(
                tmp_path, 
                tenant_id=tenant_id, 
                user_id=user_id
            )
            
            # Add upload info to response
            result["uploaded_by"] = user.username if user else "anonymous"
            
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_documents(
    user: TokenData = Depends(require_viewer) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    List documents for the current user's tenant with STRICT isolation.
    Requires VIEWER, USER, or ADMIN role when AUTH_ENABLED=True.
    
    Returns ONLY documents belonging to the user's tenant_id.
    """
    try:
        tenant_id = user.tenant_id if user else "default"
        
        # Get all documents from FAISS metadata
        manager = get_faiss_manager()
        
        # STRICT tenant filtering - only return documents for this tenant
        tenant_docs = {}
        for doc in manager.documents:
            doc_tenant = doc.get("tenant_id", "default")
            
            # Enforce tenant isolation
            if doc_tenant != tenant_id:
                continue  # Skip documents from other tenants
            
            file_name = doc.get("file_name", "unknown")
            if file_name not in tenant_docs:
                tenant_docs[file_name] = {
                    "file_name": file_name,
                    "tenant_id": tenant_id,
                    "uploaded_by": doc.get("uploaded_by"),
                    "chunk_count": 0
                }
            tenant_docs[file_name]["chunk_count"] += 1
        
        return {
            "tenant_id": tenant_id,
            "documents": list(tenant_docs.values()),
            "total_documents": len(tenant_docs),
            "isolation_enforced": settings.AUTH_ENABLED
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
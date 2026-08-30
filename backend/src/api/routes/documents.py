from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
from starlette.concurrency import run_in_threadpool
import hashlib
from src.services.document_ingestion import ingest_document
from src.services.bm25_search import rebuild_bm25_index
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
        # Preserve a tenant-scoped source copy so a document can be re-indexed
        # later without asking the user to find and upload the file again.
        original_file_name = file.filename or "upload.txt"
        safe_file_name = Path(original_file_name).name or "upload.txt"
        tenant_id = user.tenant_id if user else "default"
        tenant_key = hashlib.sha256(tenant_id.encode()).hexdigest()[:20]
        source_dir = Path(settings.DOCUMENT_UPLOAD_PATH) / tenant_key
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / safe_file_name
        content = await file.read()
        await run_in_threadpool(source_path.write_bytes, content)
        
        user_id = user.user_id if user else None
        # Parsing PDFs, creating embeddings, and writing FAISS data are CPU/
        # blocking operations, so keep them off the async event loop.
        result = await run_in_threadpool(
            ingest_document,
            str(source_path),
            tenant_id=tenant_id,
            user_id=user_id,
            original_file_name=original_file_name,
        )
        result["uploaded_by"] = user.username if user else "anonymous"
        return result
                
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
                    "chunk_count": 0,
                    "file_size_bytes": doc.get("file_size_bytes"),
                    "file_type": doc.get("file_type"),
                    "uploaded_at": doc.get("upload_timestamp"),
                    "page_count": 0,
                    "can_reindex": bool(doc.get("source_path")),
                }
            tenant_docs[file_name]["chunk_count"] += 1
            page_number = doc.get("page_number")
            if page_number:
                tenant_docs[file_name]["page_count"] = max(tenant_docs[file_name]["page_count"], page_number)
        
        return {
            "tenant_id": tenant_id,
            "documents": list(tenant_docs.values()),
            "total_documents": len(tenant_docs),
            "isolation_enforced": settings.AUTH_ENABLED
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex/{file_name:path}")
async def reindex_document(
    file_name: str,
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user),
):
    """Rebuild one document's chunks from its retained tenant-scoped source."""
    try:
        tenant_id = user.tenant_id if user else "default"
        manager = get_faiss_manager()
        metadata = next((doc for doc in manager.documents if doc.get("file_name") == file_name and doc.get("tenant_id", "default") == tenant_id), None)
        source_path = Path(metadata.get("source_path")) if metadata and metadata.get("source_path") else None
        if not source_path or not source_path.is_file():
            raise HTTPException(status_code=409, detail="The original source is unavailable. Upload this document again to re-index it.")

        chunks_deleted = manager.delete_document(file_name, tenant_id)
        manager.save()
        rebuild_bm25_index()
        result = await run_in_threadpool(ingest_document, str(source_path), tenant_id=tenant_id, user_id=user.user_id if user else None, original_file_name=file_name)
        if result.get("status") != "success":
            raise HTTPException(status_code=500, detail=result.get("error", "Could not re-index document"))
        result["chunks_replaced"] = chunks_deleted
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_name:path}")
async def delete_document(
    file_name: str,
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user),
):
    """Delete all indexed chunks for one document in the current tenant.

    The filename is matched exactly and the tenant constraint is applied before
    any data is removed, so a caller cannot delete another tenant's document.
    Requires ADMIN role when authentication is enabled.
    """
    try:
        tenant_id = user.tenant_id if user else "default"
        manager = get_faiss_manager()
        metadata = next((doc for doc in manager.documents if doc.get("file_name") == file_name and doc.get("tenant_id", "default") == tenant_id), None)
        chunks_deleted = manager.delete_document(file_name, tenant_id)

        # Do not reveal whether the same filename exists in another tenant.
        if chunks_deleted == 0:
            raise HTTPException(status_code=404, detail="Document not found")

        manager.save()
        rebuild_bm25_index()
        source_path = Path(metadata["source_path"]) if metadata and metadata.get("source_path") else None
        if source_path and source_path.is_file():
            source_path.unlink()

        return {
            "status": "success",
            "file_name": file_name,
            "tenant_id": tenant_id,
            "chunks_deleted": chunks_deleted,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

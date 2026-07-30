"""Monitoring API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict
from src.services.monitoring import get_monitoring_service
from src.core.auth import get_current_user, TokenData, get_optional_user, require_admin
from src.core.config import settings

router = APIRouter()


@router.get("/metrics")
async def get_system_metrics(
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get overall system metrics including:
    - Total queries processed
    - Success/failure rates
    - Latency statistics
    - Hallucination detection rates
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        metrics = monitoring.get_system_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries")
async def get_query_logs(
    limit: int = Query(50, ge=1, le=500),
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    current_user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get query logs with filtering.
    If user_id and tenant_id provided, returns logs for that user.
    Otherwise returns recent queries (admin only).
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        
        if user_id and tenant_id:
            queries = monitoring.get_user_queries(user_id, tenant_id, limit)
        else:
            # For admin: get all recent queries
            # This would require a different implementation to get all queries
            # For now, return empty if no specific user requested
            queries = []
        
        return {
            "queries": queries,
            "total": len(queries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/{query_id}")
async def get_query_log(
    query_id: str,
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get detailed log for a specific query.
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        query_log = monitoring.get_query_log(query_id)
        
        if not query_log:
            raise HTTPException(status_code=404, detail="Query log not found")
        
        return query_log
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors")
async def get_error_stats(
    operation: Optional[str] = None,
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get error statistics and recent errors.
    Optionally filter by operation (e.g., 'query', 'retrieval').
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        error_stats = monitoring.get_error_stats(operation)
        return error_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hallucinations")
async def get_hallucination_metrics(
    limit: int = Query(50, ge=1, le=500),
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get recent hallucination detections.
    
    Hallucinations are detected when:
    - Answer has no retrieved sources
    - Answer doesn't reference the sources
    - Answer appears generic or ungrounded
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        hallucinations = monitoring.get_hallucination_metrics(limit)
        
        return {
            "hallucinations": hallucinations,
            "total": len(hallucinations),
            "threshold": monitoring.hallucination_threshold
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latency/{operation}")
async def get_latency_stats(
    operation: str,
    user: TokenData = Depends(require_admin) if settings.AUTH_ENABLED else Depends(get_optional_user)
):
    """
    Get latency statistics for a specific operation.
    
    Operations: 'query', 'retrieval', 'generation'
    
    Requires ADMIN role when AUTH_ENABLED=True.
    """
    try:
        monitoring = get_monitoring_service()
        stats = monitoring._get_latency_stats(operation)
        
        return {
            "operation": operation,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def monitoring_health():
    """
    Health check for monitoring system.
    Public endpoint, no authentication required.
    """
    try:
        monitoring = get_monitoring_service()
        
        # Try to get a simple metric to verify Redis connection
        total_queries = monitoring._get_counter_value("total_queries")
        
        return {
            "status": "healthy",
            "monitoring_active": True,
            "redis_connected": True,
            "queries_tracked": total_queries
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "monitoring_active": False,
            "redis_connected": False,
            "error": str(e)
        }

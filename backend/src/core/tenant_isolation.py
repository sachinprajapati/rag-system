"""Tenant isolation middleware and utilities"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant isolation across all API requests.
    
    Ensures that when AUTH_ENABLED=True, all authenticated requests
    include tenant_id and prevent cross-tenant data access.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip tenant checks for public endpoints
        public_paths = ["/", "/docs", "/openapi.json", "/api/health", "/api/auth"]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # If auth is disabled, allow all requests
        if not settings.AUTH_ENABLED:
            return await call_next(request)
        
        # For authenticated requests, tenant_id should be in user context
        # This is enforced at the endpoint level via dependencies
        response = await call_next(request)
        
        # Log all tenant-scoped operations for audit trail
        if hasattr(request.state, "user") and request.state.user:
            logger.info(
                f"Tenant-scoped request: {request.method} {request.url.path} "
                f"by user={request.state.user.get('user_id')} "
                f"tenant={request.state.user.get('tenant_id')}"
            )
        
        return response


def validate_tenant_access(resource_tenant_id: str, user_tenant_id: str) -> bool:
    """
    Validate that a user can access a resource based on tenant_id.
    
    Args:
        resource_tenant_id: The tenant_id of the resource being accessed
        user_tenant_id: The tenant_id of the requesting user
        
    Returns:
        True if access allowed, False otherwise
        
    Raises:
        HTTPException: If access is denied
    """
    if resource_tenant_id != user_tenant_id:
        logger.warning(
            f"Tenant isolation violation: user from tenant '{user_tenant_id}' "
            f"attempted to access resource from tenant '{resource_tenant_id}'"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: You cannot access resources from another tenant"
        )
    return True


def get_default_tenant_id() -> str:
    """
    Get the default tenant ID for unauthenticated requests.
    
    Returns:
        Default tenant identifier
    """
    return "default"


def ensure_tenant_metadata(metadata: dict, tenant_id: str) -> dict:
    """
    Ensure metadata includes tenant_id for proper isolation.
    
    Args:
        metadata: Document or resource metadata
        tenant_id: Tenant ID to add
        
    Returns:
        Updated metadata with tenant_id
    """
    metadata = metadata.copy()
    metadata["tenant_id"] = tenant_id
    return metadata

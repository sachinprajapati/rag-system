"""
Authentication routes for Keycloak integration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.core.auth import (
    get_current_user,
    get_optional_user,
    require_role,
    TokenData,
)

router = APIRouter()


class UserInfo(BaseModel):
    """User information response"""
    user_id: str
    username: str
    email: str
    tenant_id: str
    roles: list[str]


class AuthStatus(BaseModel):
    """Authentication status response"""
    authenticated: bool
    user: Optional[UserInfo] = None


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: TokenData = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    Requires valid JWT token.
    """
    return UserInfo(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        tenant_id=user.tenant_id,
        roles=user.roles,
    )


@router.get("/status", response_model=AuthStatus)
async def get_auth_status(
    user: Optional[TokenData] = Depends(get_optional_user)
):
    """
    Check authentication status.
    Works with or without token.
    """
    if user:
        return AuthStatus(
            authenticated=True,
            user=UserInfo(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                tenant_id=user.tenant_id,
                roles=user.roles,
            )
        )
    
    return AuthStatus(authenticated=False)


@router.get("/admin-only")
async def admin_only_route(
    user: TokenData = Depends(require_role("admin"))
):
    """
    Example protected route requiring 'admin' role.
    """
    return {
        "message": "Admin access granted",
        "user": user.username,
        "tenant": user.tenant_id,
    }


@router.post("/logout")
async def logout(
    user: TokenData = Depends(get_current_user)
):
    """
    Logout endpoint.
    Note: JWT tokens are stateless. True logout happens client-side 
    by removing the token and optionally calling Keycloak's logout endpoint.
    """
    return {
        "message": "Logout successful",
        "note": "Clear your token on the client side"
    }

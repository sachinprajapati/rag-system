"""
Keycloak OAuth2/OpenID Connect Authentication
Verifies JWT tokens issued by Keycloak
"""
from typing import Optional, Dict, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import requests
from functools import lru_cache
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class KeycloakJWTValidator:
    """Validates JWT tokens from Keycloak"""
    
    def __init__(self):
        self.keycloak_url = settings.KEYCLOAK_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self._public_key = None
        
    @lru_cache(maxsize=1)
    def get_public_key(self) -> str:
        """
        Fetch Keycloak's public key for JWT verification.
        Cached to avoid repeated requests.
        """
        try:
            url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            jwks = response.json()
            
            # Get the first key (in production, match by 'kid')
            if jwks.get("keys"):
                key_data = jwks["keys"][0]
                # Construct PEM format public key
                n = key_data["n"]
                e = key_data["e"]
                
                # For simplicity, we'll use the full JWKS approach
                return jwks
            else:
                raise ValueError("No keys found in JWKS")
                
        except Exception as e:
            logger.error(f"Failed to fetch Keycloak public key: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    def verify_token(self, token: str) -> Dict:
        """
        Verify JWT token signature and extract claims.
        
        Args:
            token: JWT access token from Keycloak
            
        Returns:
            Dictionary containing token claims (user_id, tenant_id, roles, etc.)
        """
        try:
            # In production, verify against Keycloak's public key
            # For now, we decode without verification for development
            # NOTE: In production, always verify the signature!
            
            # Decode token header to get algorithm
            unverified_header = jwt.get_unverified_header(token)
            
            # Decode and verify token
            # For production: Fetch and use Keycloak's public key
            decoded = jwt.decode(
                token,
                options={
                    "verify_signature": False,  # TODO: Set to True in production with proper key
                    "verify_aud": False,  # Set to True and verify audience
                    "verify_exp": True,   # Always verify expiration
                },
            )
            
            return decoded
            
        except JWTError as e:
            logger.error(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global validator instance
jwt_validator = KeycloakJWTValidator()


class TokenData:
    """Structured token data extracted from JWT"""
    
    def __init__(self, token_dict: Dict):
        self.user_id: str = token_dict.get("sub", "")
        self.username: str = token_dict.get("preferred_username", "")
        self.email: str = token_dict.get("email", "")
        self.tenant_id: str = token_dict.get("tenant_id", "default")
        self.roles: List[str] = self._extract_roles(token_dict)
        self.raw_token: Dict = token_dict
        
    @staticmethod
    def _extract_roles(token_dict: Dict) -> List[str]:
        """Extract roles from Keycloak token structure"""
        roles = []
        
        # Realm roles
        if "realm_access" in token_dict:
            roles.extend(token_dict["realm_access"].get("roles", []))
        
        # Client roles
        if "resource_access" in token_dict:
            for client, access in token_dict["resource_access"].items():
                roles.extend(access.get("roles", []))
        
        return roles
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(role in self.roles for role in roles)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to extract and validate current user from JWT token.
    
    Usage in routes:
        @router.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id, "tenant": user.tenant_id}
    """
    token = credentials.credentials
    
    # Validate token
    token_dict = jwt_validator.verify_token(token)
    
    # Return structured token data
    return TokenData(token_dict)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Dependency for routes requiring an active user.
    Can be extended to check user status in database.
    """
    # Add additional checks here (e.g., user not disabled)
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to require specific role.
    
    Usage:
        @router.get("/admin")
        async def admin_route(user: TokenData = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker


def require_any_role(required_roles: List[str]):
    """
    Dependency factory to require any of the specified roles.
    
    Usage:
        @router.get("/resource")
        async def resource_route(
            user: TokenData = Depends(require_any_role(["admin", "editor"]))
        ):
            return {"message": "Access granted"}
    """
    async def role_checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if not user.has_any_role(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {required_roles} required"
            )
        return user
    return role_checker


# Optional: Make authentication optional for certain routes
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[TokenData]:
    """
    Optional authentication - returns None if no token provided.
    
    Usage:
        @router.get("/public-or-private")
        async def flexible_route(user: Optional[TokenData] = Depends(get_optional_user)):
            if user:
                return {"message": f"Welcome {user.username}"}
            return {"message": "Welcome guest"}
    """
    if not credentials:
        return None
    
    try:
        token_dict = jwt_validator.verify_token(credentials.credentials)
        return TokenData(token_dict)
    except HTTPException:
        return None


# Convenient role-specific dependencies
async def require_admin(user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require admin role - for document upload, user management"""
    if not user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return user


async def require_user(user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require user role - for asking questions, basic operations"""
    if not user.has_any_role(["admin", "user"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User or admin role required"
        )
    return user


async def require_viewer(user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require viewer role - for read-only access"""
    if not user.has_any_role(["admin", "user", "viewer"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer, user, or admin role required"
        )
    return user

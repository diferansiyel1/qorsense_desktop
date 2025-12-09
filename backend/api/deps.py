"""
API Dependencies Module - Multi-Tenant Security.

Provides reusable dependencies for FastAPI endpoints including:
- Authentication (get_current_user with JWT claims)
- Role-based authorization (RoleChecker)
- Organization-scoped data access
- Database sessions
- Pagination

JWT tokens contain:
- sub: user_id (UUID)
- org_id: organization_id (UUID)
- role: user role (super_admin, org_admin, engineer)

This allows authorization checks without additional DB queries.

Usage Examples:
    # Basic authentication
    @router.get("/protected")
    async def protected_route(user: CurrentUser):
        return {"user": user.email}
    
    # Role-based access
    @router.delete("/admin-only", dependencies=[Depends(RoleChecker(["super_admin", "org_admin"]))])
    async def admin_route():
        return {"status": "ok"}
    
    # Organization-scoped access
    @router.get("/org/{org_id}/data")
    async def org_data(org_id: str, user: CurrentOrgUser):
        return {"org": org_id}
"""

from typing import Annotated, Optional, List, Union
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.core.config import settings
from backend.core.security import verify_token
from backend.models_db import User, Role


# ==============================================================================
# OAUTH2 CONFIGURATION
# ==============================================================================

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login/form",
    auto_error=False  # Don't auto-error, we'll handle it manually
)


# ==============================================================================
# TOKEN CLAIMS DATACLASS
# ==============================================================================

@dataclass
class TokenClaims:
    """
    Parsed JWT token claims.
    
    Provides quick access to authorization info without DB lookup.
    Use this for lightweight permission checks.
    """
    user_id: str
    org_id: Optional[str]
    role: Role
    
    @property
    def is_super_admin(self) -> bool:
        """Check if user has SUPER_ADMIN role."""
        return self.role == Role.SUPER_ADMIN
    
    @property
    def is_org_admin(self) -> bool:
        """Check if user has ORG_ADMIN role."""
        return self.role == Role.ORG_ADMIN
    
    @property
    def is_engineer(self) -> bool:
        """Check if user has ENGINEER role."""
        return self.role == Role.ENGINEER
    
    @property
    def role_value(self) -> str:
        """Get role as string value."""
        return self.role.value if isinstance(self.role, Role) else str(self.role)
    
    def can_access_org(self, org_id: str) -> bool:
        """
        Check if user can access the specified organization.
        
        SUPER_ADMIN can access all organizations.
        Others can only access their own organization.
        """
        if self.is_super_admin:
            return True
        return self.org_id == org_id
    
    def has_role(self, roles: List[str]) -> bool:
        """
        Check if user has one of the specified roles.
        
        Args:
            roles: List of role strings to check against
            
        Returns:
            True if user's role is in the list
        """
        return self.role_value in roles


def parse_token_claims(payload: dict) -> Optional[TokenClaims]:
    """
    Parse JWT payload into TokenClaims object.
    
    Returns None if payload is invalid or missing required fields.
    """
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    role_str = payload.get("role", "engineer")
    try:
        role = Role(role_str)
    except ValueError:
        role = Role.ENGINEER  # Default fallback
    
    return TokenClaims(
        user_id=user_id,
        org_id=payload.get("org_id"),
        role=role,
    )


# ==============================================================================
# ROLE CHECKER CLASS
# ==============================================================================

class RoleChecker:
    """
    Role-based permission checker dependency.
    
    Validates that the current user has one of the allowed roles.
    Raises 403 Forbidden if role check fails.
    
    Usage:
        # Single role
        @router.post("/admin", dependencies=[Depends(RoleChecker(["super_admin"]))])
        async def admin_only():
            ...
        
        # Multiple roles
        @router.put("/data", dependencies=[Depends(RoleChecker(["org_admin", "super_admin"]))])
        async def admin_route():
            ...
        
        # As function parameter
        @router.delete("/item/{id}")
        async def delete_item(
            id: str,
            _: Annotated[bool, Depends(RoleChecker(["super_admin"]))]
        ):
            ...
    """
    
    def __init__(self, allowed_roles: List[str]):
        """
        Initialize RoleChecker with allowed roles.
        
        Args:
            allowed_roles: List of role strings that are allowed.
                          Valid values: "super_admin", "org_admin", "engineer"
        """
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        token: Annotated[Optional[str], Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)]
    ) -> bool:
        """
        Check if current user has an allowed role.
        
        Returns True if authorized, raises HTTPException otherwise.
        """
        # Validate token exists
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kimlik doğrulama gerekli",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Decode and validate token
        payload = verify_token(token, token_type="access")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Parse claims
        claims = parse_token_claims(payload)
        if claims is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token içeriği geçersiz",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check role
        if not claims.has_role(self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu işlem için yetkiniz yok. Gerekli roller: {', '.join(self.allowed_roles)}",
            )
        
        # Optionally verify user still exists and is active
        result = await db.execute(
            select(User).where(User.id == claims.user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kullanıcı bulunamadı",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hesabınız devre dışı bırakılmış",
            )
        
        return True


# ==============================================================================
# CORE AUTHENTICATION DEPENDENCIES
# ==============================================================================

async def get_token_claims(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> TokenClaims:
    """
    Get token claims from JWT without DB lookup.
    
    Use this for lightweight authorization checks where you don't need
    the full User object.
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli - Token bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    claims = parse_token_claims(payload)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token içeriği geçersiz",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return claims


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Performs DB lookup to get full user object with all attributes.
    Use get_token_claims if you only need role/org info.
    
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 403: If user account is disabled
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli - Token bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token içeriği geçersiz - user_id bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database by ID (UUID)
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user and verify they are active.
    
    This is a wrapper around get_current_user that explicitly
    documents the is_active check requirement.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )
    return current_user


async def get_current_org_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get current user and validate organization membership.
    
    Validates that:
    1. Token is valid and not expired
    2. User exists and is active
    3. User belongs to an organization (org_id in token)
    4. Organization ID in token matches user's organization
    
    Raises:
        HTTPException 401: If token is invalid
        HTTPException 403: If user has no organization or mismatch
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    token_org_id: Optional[str] = payload.get("org_id")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token içeriği geçersiz",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )
    
    # SUPER_ADMIN can bypass org check
    if user.role == Role.SUPER_ADMIN:
        return user
    
    # Validate organization membership
    if user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bir organizasyona ait değilsiniz"
        )
    
    # Validate token org_id matches user's org
    if token_org_id and user.organization_id != token_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizasyon yetkisi eşleşmiyor - yeniden giriş yapın"
        )
    
    return user


# ==============================================================================
# ROLE-BASED AUTHORIZATION DEPENDENCIES
# ==============================================================================

async def get_current_org_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user and verify they have ORG_ADMIN or SUPER_ADMIN role.
    """
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için ORG_ADMIN veya SUPER_ADMIN yetkisi gerekli"
        )
    return current_user


async def get_current_super_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user and verify they have SUPER_ADMIN role.
    """
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için SUPER_ADMIN yetkisi gerekli"
        )
    return current_user


# ==============================================================================
# OPTIONAL AUTHENTICATION DEPENDENCIES
# ==============================================================================

async def get_optional_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """
    Optionally get the current user if authenticated.
    
    Does not raise an exception if no valid token is provided.
    Useful for endpoints with different behavior for auth/unauth users.
    """
    if token is None:
        return None
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return None
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        return None
    
    return user


async def get_current_user_or_dev_bypass(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """
    Get current user OR bypass auth in development mode.
    
    In development mode (settings.is_development = True):
    - If no token provided, returns None (allows unauthenticated access)
    - If token provided, validates and returns user
    
    In production mode:
    - Always requires valid token, raises 401 if missing/invalid
    """
    # Development mode bypass
    if settings.is_development and token is None:
        return None
    
    # Production mode: require auth
    if not settings.is_development and token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If token provided, validate it
    if token is not None:
        payload = verify_token(token, token_type="access")
        if payload is None:
            if settings.is_development:
                return None
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id: Optional[str] = payload.get("sub")
        if user_id:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
    
    if settings.is_development:
        return None
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama başarısız",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ==============================================================================
# ORGANIZATION ACCESS CONTROL
# ==============================================================================

def require_org_access(org_id: str):
    """
    Factory function to create an organization access checker dependency.
    
    Usage:
        @router.get("/orgs/{org_id}/data")
        async def get_org_data(
            org_id: str,
            _: Annotated[None, Depends(require_org_access(org_id))]
        ):
            ...
    """
    async def checker(claims: Annotated[TokenClaims, Depends(get_token_claims)]):
        if not claims.can_access_org(org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu organizasyona erişim yetkiniz yok"
            )
    return checker


class OrgAccessChecker:
    """
    Class-based organization access checker.
    
    Use when you need to check organization access from path parameters.
    
    Usage:
        @router.get("/orgs/{org_id}/sensors")
        async def get_org_sensors(
            org_id: str,
            _: Annotated[bool, Depends(OrgAccessChecker("org_id"))]
        ):
            ...
    """
    
    def __init__(self, org_id_param: str = "org_id"):
        """
        Initialize with the name of the path parameter containing org_id.
        """
        self.org_id_param = org_id_param
    
    async def __call__(
        self,
        request: Request,
        claims: Annotated[TokenClaims, Depends(get_token_claims)]
    ) -> bool:
        """
        Check if user can access the organization specified in path.
        """
        org_id = request.path_params.get(self.org_id_param)
        if org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organizasyon ID'si ({self.org_id_param}) path'te bulunamadı"
            )
        
        if not claims.can_access_org(org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu organizasyona erişim yetkiniz yok"
            )
        
        return True


# ==============================================================================
# TYPE ALIASES FOR CLEANER DEPENDENCY INJECTION
# ==============================================================================

# Database session
DbSession = Annotated[AsyncSession, Depends(get_db)]

# User dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentOrgUser = Annotated[User, Depends(get_current_org_user)]
CurrentOrgAdmin = Annotated[User, Depends(get_current_org_admin)]
CurrentSuperAdmin = Annotated[User, Depends(get_current_super_admin)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
DevUser = Annotated[Optional[User], Depends(get_current_user_or_dev_bypass)]

# Token claims (lightweight, no DB lookup)
Claims = Annotated[TokenClaims, Depends(get_token_claims)]

# Legacy alias for backward compatibility
CurrentAdminUser = CurrentOrgAdmin


# ==============================================================================
# PRE-CONFIGURED ROLE CHECKERS (Convenience)
# ==============================================================================

# Common role checker instances
require_super_admin = RoleChecker(["super_admin"])
require_org_admin = RoleChecker(["org_admin", "super_admin"])
require_admin = RoleChecker(["org_admin", "super_admin"])  # Alias
require_engineer = RoleChecker(["engineer", "org_admin", "super_admin"])

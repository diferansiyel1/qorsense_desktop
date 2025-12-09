"""
API Dependencies Module - Multi-Tenant Support.

Provides reusable dependencies for FastAPI endpoints including:
- Authentication (get_current_user with JWT claims)
- Role-based authorization
- Organization-scoped data access
- Database sessions
- Pagination

JWT tokens contain:
- sub: user_id (UUID)
- org_id: organization_id (UUID)
- role: user role (super_admin, org_admin, engineer)

This allows authorization checks without additional DB queries.
"""

from typing import Annotated, Optional
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.core.config import settings
from backend.core.security import verify_token
from backend.models_db import User, Role


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login/form",
    auto_error=False  # Don't auto-error, we'll handle it
)


@dataclass
class TokenClaims:
    """
    Parsed JWT token claims.
    
    Provides quick access to authorization info without DB lookup.
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
    
    def can_access_org(self, org_id: str) -> bool:
        """
        Check if user can access the specified organization.
        
        SUPER_ADMIN can access all organizations.
        Others can only access their own organization.
        """
        if self.is_super_admin:
            return True
        return self.org_id == org_id


def parse_token_claims(payload: dict) -> Optional[TokenClaims]:
    """
    Parse JWT payload into TokenClaims object.
    
    Returns None if payload is invalid.
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


async def get_token_claims(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> TokenClaims:
    """
    Get token claims from JWT without DB lookup.
    
    Use this for lightweight authorization checks.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama başarısız",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if token is None:
        raise credentials_exception
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    claims = parse_token_claims(payload)
    if claims is None:
        raise credentials_exception
    
    return claims


async def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Performs DB lookup to get full user object.
    Use get_token_claims if you only need authorization info.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama başarısız",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if token is None:
        raise credentials_exception
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database by ID (UUID)
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
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
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )
    return current_user


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


# ==============================================================================
# TYPE ALIASES FOR CLEANER DEPENDENCY INJECTION
# ==============================================================================

# Database session
DbSession = Annotated[AsyncSession, Depends(get_db)]

# User dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentOrgAdmin = Annotated[User, Depends(get_current_org_admin)]
CurrentSuperAdmin = Annotated[User, Depends(get_current_super_admin)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
DevUser = Annotated[Optional[User], Depends(get_current_user_or_dev_bypass)]

# Token claims (lightweight, no DB lookup)
Claims = Annotated[TokenClaims, Depends(get_token_claims)]

# Legacy alias for backward compatibility
CurrentAdminUser = CurrentOrgAdmin

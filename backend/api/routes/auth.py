"""
Authentication Router - Multi-Tenant Support.

Provides endpoints for user authentication and registration:
- POST /login: Authenticate with email/password, returns JWT with org_id & role claims
- POST /register: Create organization + first admin user atomically
- POST /refresh: Refresh access token
- GET /me: Get current user info
- POST /logout: Logout (client-side token invalidation)

JWT Payload includes:
- sub: user_id (UUID)
- org_id: organization_id (UUID or null for SUPER_ADMIN)
- role: user role (super_admin, org_admin, engineer)
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models_db import User, Organization, Role
from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
)
from backend.schemas.auth import (
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    OrganizationCreate,
    OrganizationResponse,
    RegisterRequest,
    RegisterResponse,
)
from backend.api.deps import CurrentUser, DbSession


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
    responses={401: {"description": "Unauthorized"}},
)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_jwt_with_claims(user: User) -> tuple[str, str]:
    """
    Create JWT access and refresh tokens with extended claims.
    
    JWT Payload:
    - sub: user_id (UUID string)
    - org_id: organization_id (UUID string or None)
    - role: user role value (e.g., "org_admin")
    
    This allows authorization checks without DB queries.
    """
    token_data = {
        "sub": str(user.id),
        "org_id": str(user.organization_id) if user.organization_id else None,
        "role": user.role.value if isinstance(user.role, Role) else str(user.role),
    }
    
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
    return access_token, refresh_token


# ==============================================================================
# AUTHENTICATION ENDPOINTS
# ==============================================================================

@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: DbSession,
) -> Token:
    """
    Authenticate user with email and password.
    
    Returns JWT tokens with extended claims:
    - sub: user_id
    - org_id: organization_id (for tenant isolation)
    - role: user role (for authorization)
    
    This enables stateless authorization without DB lookups.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış",
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create tokens with extended claims
    access_token, refresh_token = create_jwt_with_claims(user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login/form", response_model=Token)
async def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """
    OAuth2 compatible login endpoint (for Swagger UI).
    
    Uses username field as email for OAuth2 form compatibility.
    """
    # OAuth2 form uses 'username' field, we treat it as email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış",
        )
    
    user.last_login = datetime.utcnow()
    await db.commit()
    
    access_token, refresh_token = create_jwt_with_claims(user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: TokenRefreshRequest,
    db: DbSession,
) -> Token:
    """
    Refresh access token using refresh token.
    
    Returns a new access token with same claims if refresh token is valid.
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token içeriği",
        )
    
    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya devre dışı",
        )
    
    # Create new access token with fresh claims (in case role/org changed)
    access_token, _ = create_jwt_with_claims(user)
    
    return Token(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# ==============================================================================
# REGISTRATION ENDPOINTS
# ==============================================================================

@router.post(
    "/register", 
    response_model=RegisterResponse, 
    status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    db: DbSession,
) -> RegisterResponse:
    """
    Register a new organization and its first admin user.
    
    This endpoint creates:
    1. A new Organization
    2. The first ORG_ADMIN user for that organization
    
    The operation is ATOMIC - if any step fails, everything is rolled back.
    
    Returns both organization and user details upon success.
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kayıtlı",
        )
    
    # Check if organization name already exists
    result = await db.execute(
        select(Organization).where(Organization.name == data.organization_name.strip())
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu organizasyon adı zaten kullanımda",
        )
    
    try:
        # Create organization
        new_org = Organization(
            id=str(uuid.uuid4()),
            name=data.organization_name.strip(),
            subscription_plan="Free",
        )
        db.add(new_org)
        await db.flush()  # Get the org ID without committing
        
        # Create admin user for this organization
        new_user = User(
            id=str(uuid.uuid4()),
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            role=Role.ORG_ADMIN,  # First user is always ORG_ADMIN
            organization_id=new_org.id,
            is_active=True,
        )
        db.add(new_user)
        
        # Commit transaction (atomic)
        await db.commit()
        await db.refresh(new_org)
        await db.refresh(new_user)
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kayıt işlemi başarısız: {str(e)}",
        )
    
    return RegisterResponse(
        organization=OrganizationResponse.model_validate(new_org),
        user=UserResponse.model_validate(new_user),
        message="Kayıt başarılı! Şimdi giriş yapabilirsiniz.",
    )


@router.post(
    "/users", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_user(
    user_data: UserCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """
    Create a new user within the current user's organization.
    
    Requires ORG_ADMIN or SUPER_ADMIN role.
    New user is automatically assigned to the admin's organization.
    """
    # Check authorization
    if current_user.role not in [Role.ORG_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok (ORG_ADMIN veya SUPER_ADMIN gerekli)",
        )
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kayıtlı",
        )
    
    # Determine the organization for the new user
    # SUPER_ADMIN can create users without org, ORG_ADMIN creates in their org
    org_id = current_user.organization_id
    
    # Validate role assignment
    if user_data.role == Role.SUPER_ADMIN and current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SUPER_ADMIN rolü sadece SUPER_ADMIN tarafından atanabilir",
        )
    
    # Create new user
    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        organization_id=org_id,
        is_active=True,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


# ==============================================================================
# USER PROFILE ENDPOINTS
# ==============================================================================

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> User:
    """
    Get current authenticated user's information.
    
    Requires valid JWT access token.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """
    Update current user's profile information.
    
    Allows users to update their own email, full name, and password.
    """
    # Update fields if provided
    if update_data.email is not None:
        # Check if email is taken by another user
        result = await db.execute(
            select(User).where(
                User.email == update_data.email,
                User.id != current_user.id
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu email adresi başka bir kullanıcı tarafından kullanılıyor",
            )
        current_user.email = update_data.email
    
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    if update_data.password is not None:
        current_user.hashed_password = get_password_hash(update_data.password)
    
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.post("/logout")
async def logout(current_user: CurrentUser) -> dict:
    """
    Logout endpoint.
    
    Note: JWT tokens are stateless, so this endpoint mainly serves
    as a signal for the client to discard the token.
    For production, consider implementing a token blacklist with Redis.
    """
    return {
        "message": "Başarıyla çıkış yapıldı",
        "detail": "Token istemci tarafında silinmelidir"
    }


# ==============================================================================
# ORGANIZATION ENDPOINTS
# ==============================================================================

@router.get("/organization", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: CurrentUser,
    db: DbSession,
) -> Organization:
    """
    Get current user's organization details.
    """
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bir organizasyona bağlı değilsiniz",
        )
    
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizasyon bulunamadı",
        )
    
    return org

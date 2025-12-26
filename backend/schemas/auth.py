"""
Authentication & Authorization Pydantic Schemas.

Provides request/response schemas for:
- User registration and authentication
- Organization management
- JWT token handling

All schemas use strict validation with clear error messages.
"""

import re
from datetime import datetime

from backend.models_db import Role
from pydantic import BaseModel, EmailStr, Field, field_validator

# ==============================================================================
# TOKEN SCHEMAS
# ==============================================================================

class Token(BaseModel):
    """JWT token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class TokenPayload(BaseModel):
    """JWT token payload schema for internal use."""
    sub: str = Field(..., description="Subject (user_id)")
    org_id: str | None = Field(None, description="Organization ID")
    role: str = Field(..., description="User role")
    exp: int | None = Field(None, description="Expiration timestamp")
    type: str = Field(default="access", description="Token type")


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str = Field(..., description="Refresh token")


# ==============================================================================
# USER SCHEMAS
# ==============================================================================

class UserLogin(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class UserCreate(BaseModel):
    """User creation schema for registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Full name"
    )
    role: Role = Field(
        default=Role.ENGINEER,
        description="User role (defaults to ENGINEER)"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password has minimum security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    """User response schema (excludes sensitive data like password)."""
    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="Full name")
    role: Role = Field(..., description="User role")
    organization_id: str | None = Field(None, description="Organization UUID")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: datetime | None = Field(None, description="Last login timestamp")

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User update schema for profile changes."""
    email: EmailStr | None = Field(None, description="New email address")
    full_name: str | None = Field(None, max_length=255, description="New full name")
    password: str | None = Field(
        None,
        min_length=8,
        max_length=100,
        description="New password"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        """Validate password has minimum security requirements."""
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


# ==============================================================================
# ORGANIZATION SCHEMAS
# ==============================================================================

class OrganizationCreate(BaseModel):
    """Organization creation schema."""
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Organization name"
    )
    subscription_plan: str = Field(
        default="Free",
        description="Subscription plan"
    )

    @field_validator("name")
    @classmethod
    def validate_org_name(cls, v: str) -> str:
        """Validate organization name format."""
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        return v


class OrganizationResponse(BaseModel):
    """Organization response schema."""
    id: str = Field(..., description="Organization UUID")
    name: str = Field(..., description="Organization name")
    subscription_plan: str = Field(..., description="Subscription plan")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: str | None = Field(None, min_length=2, max_length=255)
    subscription_plan: str | None = Field(None)


# ==============================================================================
# REGISTRATION SCHEMAS
# ==============================================================================

class RegisterRequest(BaseModel):
    """
    Combined registration request for creating organization + admin user.
    
    This creates a new organization and the first ORG_ADMIN user atomically.
    """
    # Organization fields
    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Organization name"
    )

    # User fields
    email: EmailStr = Field(..., description="Admin user email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Admin user password (min 8 characters)"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Admin user full name"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password has minimum security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponse(BaseModel):
    """Registration response with organization and user details."""
    organization: OrganizationResponse
    user: UserResponse
    message: str = Field(
        default="Registration successful",
        description="Success message"
    )

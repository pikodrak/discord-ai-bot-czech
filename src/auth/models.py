"""
Authentication models for user management and sessions.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """User model for authentication."""

    id: int
    username: str
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    must_change_password: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_admin: bool = False


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response (without password)."""

    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    must_change_password: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: Optional[bool] = False


class TokenData(BaseModel):
    """Token payload data."""

    user_id: int
    username: str
    is_admin: bool
    exp: Optional[datetime] = None


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8)

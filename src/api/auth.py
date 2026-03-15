"""
Authentication router for admin access.

Provides JWT-based authentication for admin users with complete
user management, password hashing, and middleware for protecting routes.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from src.config import Settings, get_settings


router = APIRouter()
security_basic = HTTPBasic()
security_bearer = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds


class TokenData(BaseModel):
    """Token payload data."""

    username: str
    is_admin: bool = True
    exp: Optional[datetime] = None


class UserLogin(BaseModel):
    """User login schema."""

    username: str
    password: str


class UserResponse(BaseModel):
    """User response schema (without sensitive data)."""

    username: str
    email: Optional[str] = None
    is_admin: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    """User creation schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8)
    is_admin: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, settings: Settings, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in token
        settings: Application settings
        expires_delta: Token expiration time

    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def authenticate_user(username: str, password: str, settings: Settings) -> Optional[dict]:
    """
    Authenticate a user with username and password.

    Args:
        username: Username to authenticate
        password: Password to verify
        settings: Application settings

    Returns:
        dict: User data if authentication successful, None otherwise
    """
    if username != settings.admin_username:
        return None

    # Verify password (using bcrypt hash comparison)
    if not verify_password(password, get_password_hash(settings.admin_password)):
        return None

    return {
        "username": username,
        "email": "admin@example.com",
        "is_admin": True,
        "is_active": True
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    settings: Settings = Depends(get_settings)
) -> dict:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        settings: Application settings

    Returns:
        dict: Current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"]
        )
        username: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False)

        if username is None:
            raise credentials_exception

        token_data = TokenData(
            username=username,
            is_admin=is_admin,
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
    except JWTError:
        raise credentials_exception

    # Return user data (in production, fetch from database)
    return {
        "username": token_data.username,
        "is_admin": token_data.is_admin,
        "is_active": True
    }


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current authenticated admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        dict: Current admin user data

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    settings: Settings = Depends(get_settings)
) -> Token:
    """
    Login endpoint to obtain JWT token.

    Args:
        credentials: User login credentials (username and password)
        settings: Application settings

    Returns:
        Token: JWT access token

    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(credentials.username, credentials.password, settings)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={
            "sub": credentials.username,
            "is_admin": user.get("is_admin", False)
        },
        settings=settings,
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400  # 24 hours
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Logout endpoint (client should delete token).

    Since we're using stateless JWT tokens, logout is handled client-side
    by deleting the token. This endpoint is provided for consistency.

    Args:
        current_user: Current authenticated user

    Returns:
        dict: Success message
    """
    return {
        "message": "Successfully logged out. Please delete your access token.",
        "username": current_user["username"]
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user information
    """
    return UserResponse(
        username=current_user["username"],
        email=current_user.get("email"),
        is_admin=current_user.get("is_admin", False),
        is_active=current_user.get("is_active", True)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token: str,
    settings: Settings = Depends(get_settings)
) -> Token:
    """
    Refresh an existing JWT token.

    Args:
        token: Current JWT token
        settings: Application settings

    Returns:
        Token: New JWT access token

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    new_token = create_access_token(
        data={"sub": username},
        settings=settings,
        expires_delta=timedelta(hours=24)
    )

    return Token(access_token=new_token, token_type="bearer")

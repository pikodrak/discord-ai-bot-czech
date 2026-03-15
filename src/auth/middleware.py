"""
Authentication middleware for protecting routes.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.auth.security import verify_token
from src.auth.database import user_db
from src.auth.models import User, TokenData


# Security scheme for JWT tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data: Optional[TokenData] = verify_token(token)

    if token_data is None:
        raise credentials_exception

    user = user_db.get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current authenticated admin user.

    Args:
        current_user: Current authenticated user

    Returns:
        Current authenticated admin user

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )

    return current_user


async def check_password_change_required(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if the user must change their password before accessing protected routes.

    Args:
        current_user: Current authenticated user

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If user must change password
    """
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required. Please change your password before accessing this resource.",
            headers={"X-Password-Change-Required": "true"}
        )

    return current_user


async def get_current_admin_user_with_password_check(
    current_user: User = Depends(check_password_change_required)
) -> User:
    """
    Get the current authenticated admin user and ensure password has been changed if required.

    Args:
        current_user: Current authenticated user (already checked for password change)

    Returns:
        Current authenticated admin user

    Raises:
        HTTPException: If user is not an admin or must change password
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )

    return current_user


async def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Args:
        credentials: Optional HTTP Bearer token credentials

    Returns:
        Current user if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token_data = verify_token(credentials.credentials)
    if token_data is None:
        return None

    user = user_db.get_user_by_id(token_data.user_id)
    if user is None or not user.is_active:
        return None

    return user

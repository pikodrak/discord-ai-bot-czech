"""
Authentication API routes for login, logout, and user management.
"""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.models import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    PasswordChange
)
from src.auth.database import user_db
from src.auth.security import (
    verify_password,
    hash_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.auth.middleware import (
    get_current_user,
    get_current_admin_user,
    check_password_change_required,
    get_current_admin_user_with_password_check
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    current_admin: User = Depends(get_current_admin_user_with_password_check)
) -> UserResponse:
    """
    Register a new user (admin only).

    Args:
        user_data: User registration data
        current_admin: Current authenticated admin user

    Returns:
        Created user information

    Raises:
        HTTPException: If username or email already exists
    """
    try:
        user = user_db.create_user(user_data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin) -> Token:
    """
    Login and receive JWT access token.

    Args:
        credentials: Login credentials (username and password)

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = user_db.get_user_by_username(credentials.username)

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=user.must_change_password
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    """
    Logout (client should delete token).

    Since we're using JWT tokens, logout is handled client-side
    by deleting the token. This endpoint is provided for consistency.

    Args:
        current_user: Current authenticated user

    Returns:
        Success message
    """
    return {"message": "Successfully logged out. Please delete your access token."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user information
    """
    return UserResponse.model_validate(current_user)


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_admin: User = Depends(get_current_admin_user_with_password_check)
) -> List[UserResponse]:
    """
    List all users (admin only).

    Args:
        current_admin: Current authenticated admin user

    Returns:
        List of all users
    """
    users = user_db.get_all_users()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user_with_password_check)
) -> UserResponse:
    """
    Get user by ID (admin only).

    Args:
        user_id: User's ID
        current_admin: Current authenticated admin user

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """
    user = user_db.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user_with_password_check)
) -> None:
    """
    Delete user by ID (admin only).

    Args:
        user_id: User's ID
        current_admin: Current authenticated admin user

    Raises:
        HTTPException: If user not found or trying to delete self
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    if not user_db.delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Change user password.

    Args:
        password_data: Current and new password
        current_user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If current password is incorrect or password change fails
    """
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    new_hashed_password = hash_password(password_data.new_password)
    updated_user = user_db.update_user(
        current_user.id,
        hashed_password=new_hashed_password,
        must_change_password=False
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )

    return {"message": "Password changed successfully"}

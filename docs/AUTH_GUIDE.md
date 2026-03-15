# Authentication Implementation Guide

## Overview

The Discord AI Bot admin interface uses JWT (JSON Web Token) based authentication with bcrypt password hashing. This provides secure, stateless authentication for admin users.

## Features

- **JWT Token Authentication**: Stateless authentication using JSON Web Tokens (HS256 algorithm)
- **Bcrypt Password Hashing**: Secure password storage using bcrypt via passlib
- **Role-Based Access Control**: Admin-only access control for sensitive endpoints
- **Protected Routes**: FastAPI dependency injection for securing endpoints
- **Token Expiration**: 24-hour token lifetime
- **Middleware Functions**: Reusable dependencies for authentication

## Configuration

### Environment Variables

Configure authentication in your `.env` file:

```env
# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password_immediately

# JWT Secret Key (generate with: openssl rand -hex 32)
SECRET_KEY=generate-a-secure-random-secret-key-here
```

**Security Best Practices**:
1. Change default admin credentials immediately
2. Use a strong, randomly generated SECRET_KEY
3. Never commit the `.env` file to version control
4. Use different credentials for development and production

### Generate Secure Secret Key

```bash
# Using OpenSSL
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## API Endpoints

### POST /api/auth/login

Login and receive JWT access token.

**Request**:
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

### GET /api/auth/me

Get current authenticated user information.

**Headers**:
```
Authorization: Bearer <your_access_token>
```

**Response**:
```json
{
  "username": "admin",
  "email": "admin@example.com",
  "is_admin": true,
  "is_active": true,
  "created_at": "2026-03-13T10:00:00"
}
```

**cURL Example**:
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer <your_access_token>"
```

### POST /api/auth/logout

Logout endpoint (client should delete token).

**Headers**:
```
Authorization: Bearer <your_access_token>
```

**Response**:
```json
{
  "message": "Successfully logged out. Please delete your access token.",
  "username": "admin"
}
```

### POST /api/auth/refresh

Refresh an existing JWT token to extend the session.

**Request**:
```json
{
  "token": "your-current-token"
}
```

**Response**:
```json
{
  "access_token": "new-token-here",
  "token_type": "bearer",
  "expires_in": 86400
}
```

## Protected Routes

### Example: Admin Dashboard

The `/api/admin/dashboard` endpoint is protected and requires admin authentication:

```bash
curl -X GET "http://localhost:8000/api/admin/dashboard" \
  -H "Authorization: Bearer <admin_access_token>"
```

**Response**:
```json
{
  "message": "Welcome to the admin dashboard, admin!",
  "user": {
    "username": "admin",
    "is_admin": true,
    "is_active": true
  },
  "stats": {
    "total_users": 1,
    "active_sessions": 1,
    "bot_status": "offline"
  }
}
```

## Using Authentication in Your Code

### Protect Any Route (Authenticated Users)

```python
from fastapi import APIRouter, Depends
from src.api.auth import get_current_user

router = APIRouter()

@router.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    """Route accessible to any authenticated user."""
    return {
        "message": f"Hello, {current_user['username']}!",
        "is_admin": current_user.get("is_admin", False)
    }
```

### Protect Admin-Only Routes

```python
from fastapi import APIRouter, Depends
from src.api.auth import get_current_admin_user

router = APIRouter()

@router.get("/admin-only")
async def admin_route(current_admin: dict = Depends(get_current_admin_user)):
    """Route accessible only to admin users."""
    return {
        "message": f"Admin access granted to {current_admin['username']}",
        "admin_data": {"sensitive": "information"}
    }
```

## Authentication Flow

1. **Login**: Client sends username/password to `/api/auth/login`
2. **Token Received**: Server validates credentials and returns JWT token
3. **Store Token**: Client stores token securely (localStorage, sessionStorage, or httpOnly cookie)
4. **Authenticated Requests**: Client includes token in `Authorization: Bearer <token>` header
5. **Token Validation**: Server validates token on each protected endpoint request
6. **Access Granted**: If token is valid and not expired, request proceeds
7. **Logout**: Client deletes stored token (server-side logout is not needed for JWT)

## Security Middleware

### `get_current_user()`

Validates JWT token and returns current user data. Raises `401 Unauthorized` if token is invalid or expired.

**Usage**:
```python
current_user: dict = Depends(get_current_user)
```

**Returns**:
```python
{
    "username": "admin",
    "is_admin": True,
    "is_active": True
}
```

### `get_current_admin_user()`

Validates JWT token and ensures user has admin privileges. Raises `403 Forbidden` if user is not an admin.

**Usage**:
```python
current_admin: dict = Depends(get_current_admin_user)
```

## Error Responses

### 401 Unauthorized - Invalid or Missing Token

```json
{
  "detail": "Could not validate credentials"
}
```

**Causes**:
- No Authorization header provided
- Invalid token format
- Token signature verification failed
- Token has expired

### 403 Forbidden - Insufficient Permissions

```json
{
  "detail": "Not enough permissions. Admin access required."
}
```

**Causes**:
- User is authenticated but not an admin
- Attempting to access admin-only endpoints

## Token Structure

JWT tokens contain the following claims:

```json
{
  "sub": "admin",           // Subject (username)
  "is_admin": true,         // Admin flag
  "exp": 1710345600         // Expiration timestamp
}
```

## Implementation Details

### Password Hashing

Passwords are hashed using bcrypt via passlib's `CryptContext`:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("plain_password")

# Verify password
is_valid = pwd_context.verify("plain_password", hashed)
```

### Token Generation

JWT tokens are created using python-jose:

```python
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, settings: Settings, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
```

### Token Validation

```python
from jose import jwt, JWTError

try:
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    username = payload.get("sub")
    # Validate username and other claims
except JWTError:
    # Handle invalid token
    raise HTTPException(status_code=401, detail="Invalid token")
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and set your credentials and secret key

# Run the admin server
python app.py

# Or with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Access the API documentation: http://localhost:8000/docs

## Testing Authentication

### 1. Test Login

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 2. Test Protected Endpoint

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Test Admin Endpoint

```bash
curl -X GET "http://localhost:8000/api/admin/dashboard" \
  -H "Authorization: Bearer $TOKEN"
```

## Future Enhancements

The current implementation is functional but can be enhanced:

1. **Database Integration**: Store users in a database instead of environment variables
2. **User Management**: Add endpoints for creating/updating/deleting users
3. **Refresh Tokens**: Implement long-lived refresh tokens for better UX
4. **Password Reset**: Add password reset functionality
5. **Email Verification**: Verify email addresses for new users
6. **2FA**: Add two-factor authentication support
7. **Rate Limiting**: Prevent brute force attacks
8. **Audit Logging**: Log authentication events
9. **Session Management**: Track active sessions
10. **OAuth Integration**: Add OAuth providers (Google, GitHub, etc.)

## Troubleshooting

### "Could not validate credentials" Error

- Check that the token is included in the `Authorization` header
- Verify the token format: `Bearer <token>`
- Ensure the token hasn't expired (24-hour lifetime)
- Confirm the SECRET_KEY matches between token creation and validation

### "Not enough permissions" Error

- Verify user has `is_admin: true` in token claims
- Check that the endpoint requires admin access
- Try logging in again to get a fresh token

### Login Always Fails

- Verify ADMIN_USERNAME and ADMIN_PASSWORD in `.env`
- Check for typos in credentials
- Ensure the application has loaded the `.env` file
- Try restarting the application after changing `.env`

# Authentication System Documentation

## Overview

This authentication system provides JWT-based authentication for the Discord AI Bot admin interface. It includes user management, password hashing with bcrypt, and middleware for protecting admin routes.

## Features

- **JWT Token Authentication**: Stateless authentication using JSON Web Tokens
- **Bcrypt Password Hashing**: Secure password storage using bcrypt
- **Role-Based Access Control**: Admin and regular user roles
- **Protected Routes**: Middleware to secure admin endpoints
- **User Management**: Complete CRUD operations for users (admin only)

## Default Credentials

For initial access, a default admin account is created:

- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@example.com`

**IMPORTANT**: Change these credentials immediately after first login!

## API Endpoints

### Public Endpoints

#### POST /auth/login
Login and receive JWT access token.

**Request Body**:
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Protected Endpoints (Require Authentication)

All protected endpoints require the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```

#### GET /auth/me
Get current user information.

**Response**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_active": true,
  "is_admin": true,
  "created_at": "2026-03-13T10:00:00"
}
```

#### POST /auth/logout
Logout (client should delete token).

**Response**:
```json
{
  "message": "Successfully logged out. Please delete your access token."
}
```

### Admin-Only Endpoints

#### POST /auth/register
Register a new user (admin only).

**Request Body**:
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123",
  "is_admin": false
}
```

**Response**:
```json
{
  "id": 2,
  "username": "newuser",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-03-13T10:00:00"
}
```

#### GET /auth/users
List all users (admin only).

**Response**:
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_active": true,
    "is_admin": true,
    "created_at": "2026-03-13T10:00:00"
  }
]
```

#### GET /auth/users/{user_id}
Get user by ID (admin only).

#### DELETE /auth/users/{user_id}
Delete user by ID (admin only). Cannot delete your own account.

## Usage Examples

### 1. Login and Get Token

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

### 2. Access Protected Endpoint

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <your_access_token>"
```

### 3. Create New User (Admin Only)

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "securepass123",
    "is_admin": false
  }'
```

### 4. Access Admin Dashboard

```bash
curl -X GET "http://localhost:8000/admin/dashboard" \
  -H "Authorization: Bearer <admin_access_token>"
```

## Using Middleware in Your Routes

### Require Authentication

```python
from fastapi import APIRouter, Depends
from src.auth.middleware import get_current_user
from src.auth.models import User

router = APIRouter()

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.username}!"}
```

### Require Admin Access

```python
from fastapi import APIRouter, Depends
from src.auth.middleware import get_current_admin_user
from src.auth.models import User

router = APIRouter()

@router.get("/admin-only")
async def admin_route(current_admin: User = Depends(get_current_admin_user)):
    return {"message": f"Admin access granted to {current_admin.username}"}
```

### Optional Authentication

```python
from fastapi import APIRouter, Depends
from typing import Optional
from src.auth.middleware import optional_current_user
from src.auth.models import User

router = APIRouter()

@router.get("/optional-auth")
async def optional_auth_route(user: Optional[User] = Depends(optional_current_user)):
    if user:
        return {"message": f"Authenticated as {user.username}"}
    return {"message": "Not authenticated"}
```

## Security Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**IMPORTANT**:
- Generate a strong random SECRET_KEY in production
- Never commit the `.env` file to version control
- Use different secrets for development and production

### Generate Secure SECRET_KEY

```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

## Token Expiration

- Default token expiration: 60 minutes
- Tokens are stateless - server doesn't track them
- Client must store and manage token lifecycle
- After expiration, user must login again

## Database

Currently uses in-memory storage (resets on restart). For production:

1. Replace `UserDatabase` with SQLAlchemy models
2. Use PostgreSQL or MySQL
3. Add database migrations with Alembic
4. Implement proper session management

## Security Best Practices

1. **Change Default Credentials**: Update admin password immediately
2. **Use HTTPS**: Always use HTTPS in production
3. **Secure SECRET_KEY**: Use strong random keys, never hardcode
4. **Token Storage**: Store tokens securely in client (httpOnly cookies recommended)
5. **CORS Configuration**: Restrict allowed origins in production
6. **Rate Limiting**: Add rate limiting to prevent brute force attacks
7. **Input Validation**: All inputs are validated with Pydantic
8. **Password Requirements**: Minimum 8 characters enforced

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions. Admin access required."
}
```

### 400 Bad Request
```json
{
  "detail": "Username 'admin' already exists"
}
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the admin server
python app.py

# Or with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API docs at: http://localhost:8000/docs

## Next Steps

1. Replace in-memory database with persistent storage
2. Add refresh tokens for extended sessions
3. Implement password reset functionality
4. Add email verification for new users
5. Implement 2FA (two-factor authentication)
6. Add rate limiting and IP blocking
7. Add audit logging for security events

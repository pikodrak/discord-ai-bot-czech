# Authentication Quick Reference

## Setup

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set ADMIN_USERNAME, ADMIN_PASSWORD, SECRET_KEY
   ```

2. **Generate Secret Key**:
   ```bash
   openssl rand -hex 32
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Server**:
   ```bash
   python app.py
   # Or: uvicorn app:app --reload
   ```

## API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/auth/login` | No | Login and get JWT token |
| GET | `/api/auth/me` | Yes | Get current user info |
| POST | `/api/auth/logout` | Yes | Logout (delete token client-side) |
| POST | `/api/auth/refresh` | No | Refresh JWT token |
| GET | `/api/admin/dashboard` | Admin | Admin dashboard (example) |

## Quick Examples

### Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

### Get User Info
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Admin Dashboard
```bash
curl -X GET "http://localhost:8000/api/admin/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Code Examples

### Protect Any Route
```python
from fastapi import Depends
from src.api.auth import get_current_user

@app.get("/protected")
async def protected(user: dict = Depends(get_current_user)):
    return {"user": user["username"]}
```

### Protect Admin Route
```python
from fastapi import Depends
from src.api.auth import get_current_admin_user

@app.get("/admin")
async def admin_only(admin: dict = Depends(get_current_admin_user)):
    return {"admin": admin["username"]}
```

## Testing

```bash
# Run all tests
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_auth.py::TestAuthenticationEndpoints::test_login_success -v
```

## Default Credentials

- **Username**: `admin` (from `.env`)
- **Password**: `changeme` (from `.env`)
- **Change these immediately!**

## Token Details

- **Algorithm**: HS256
- **Expiration**: 24 hours
- **Header Format**: `Authorization: Bearer <token>`

## Common Issues

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check token is valid and not expired |
| 403 Forbidden | Ensure user has admin privileges |
| Login fails | Verify username/password in `.env` |
| "Could not validate credentials" | Check Authorization header format |

## Security Checklist

- [ ] Change default admin password
- [ ] Generate strong SECRET_KEY
- [ ] Don't commit `.env` file
- [ ] Use HTTPS in production
- [ ] Configure CORS properly
- [ ] Add rate limiting
- [ ] Monitor failed login attempts

"""
JWT Authentication Example for FastAPI-Lambda

This example demonstrates how to:
1. Extract JWT tokens from Authorization header using HTTPBearer
2. Decode and validate JWT tokens
3. Create user context from validated tokens
4. Protect endpoints with authentication
5. Optional authentication (public + protected endpoints)

NOTE: This is a SIMPLIFIED example for demonstration.
For production use:
- Use a proper JWT library (PyJWT, python-jose)
- Store secrets in AWS Secrets Manager or Parameter Store
- Validate token expiration, audience, issuer
- Handle token refresh
- Use proper error handling
"""

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi_lambda import FastAPI
from fastapi_lambda.exceptions import HTTPException
from fastapi_lambda.params import Depends
from fastapi_lambda.security import HTTPAuthorizationCredentials, HTTPBearer

# ============================================================================
# MOCK JWT FUNCTIONS (Replace with PyJWT or python-jose in production)
# ============================================================================


def create_access_token(data: dict, secret: str = "your-secret-key") -> str:
    """
    Create a JWT token (SIMPLIFIED - use PyJWT in production).

    Production example with PyJWT:
        import jwt
        payload = data.copy()
        payload.update({"exp": datetime.utcnow() + timedelta(hours=1)})
        return jwt.encode(payload, secret, algorithm="HS256")
    """
    # Mock token: base64-like string with user info
    # In reality, this would be a properly signed JWT
    import base64
    import json

    payload = data.copy()
    payload["exp"] = (datetime.utcnow() + timedelta(hours=1)).timestamp()

    # This is NOT a real JWT! Just for demo purposes
    token_data = json.dumps(payload)
    return base64.b64encode(token_data.encode()).decode()


def decode_access_token(token: str, secret: str = "your-secret-key") -> dict:
    """
    Decode and validate a JWT token (SIMPLIFIED - use PyJWT in production).

    Production example with PyJWT:
        import jwt
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    """
    import base64
    import json

    try:
        decoded = base64.b64decode(token.encode()).decode()
        payload = json.loads(decoded)

        # Check expiration
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")

        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ============================================================================
# USER MODEL
# ============================================================================


class User:
    """User model (simplified)."""

    def __init__(self, user_id: int, username: str, email: str, is_admin: bool = False):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.is_admin = is_admin

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "is_admin": self.is_admin,
        }


# Mock user database
USERS_DB = {
    "alice": User(1, "alice", "alice@example.com", is_admin=True),
    "bob": User(2, "bob", "bob@example.com", is_admin=False),
}


def get_user_by_username(username: str) -> Optional[User]:
    """Get user from database by username."""
    return USERS_DB.get(username)


# ============================================================================
# SECURITY DEPENDENCIES
# ============================================================================


# Create HTTPBearer instance (extracts token from Authorization header)
bearer_scheme = HTTPBearer()

# Optional authentication (returns None if no token)
optional_bearer_scheme = HTTPBearer(auto_error=False)


async def get_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> str:
    """
    Dependency that extracts the Bearer token from Authorization header.

    HTTPBearer already does this, but this shows the pattern for additional validation.
    """
    return credentials.credentials


async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> User:
    """
    Dependency that decodes JWT token and returns the current user.

    This is the CORE authentication dependency you'll use in protected endpoints.
    """
    token = credentials.credentials

    # Decode and validate token
    try:
        payload = decode_access_token(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")

    # Extract user info from token
    username = payload.get("sub")  # "sub" (subject) is standard JWT claim for user identifier
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token: no user identifier")

    # Get user from database
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_active_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Dependency that requires admin privileges.

    This shows dependency CHAINING - get_current_active_admin depends on get_current_user.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(optional_bearer_scheme)],
) -> Optional[User]:
    """
    Optional authentication - returns None if no token provided.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        username = payload.get("sub")
        if username:
            return get_user_by_username(username)
    except Exception:
        pass  # Invalid token -> treat as anonymous

    return None


# ============================================================================
# FASTAPI APP
# ============================================================================


app = FastAPI(
    title="JWT Authentication Example",
    description="Demonstrates JWT authentication with HTTPBearer in FastAPI-Lambda",
)


# ----------------------------------------------------------------------------
# Public endpoints (no authentication required)
# ----------------------------------------------------------------------------


@app.get("/")
def root():
    """Public endpoint - no authentication required."""
    return {
        "message": "Welcome to JWT Auth Example",
        "endpoints": {
            "login": "POST /login",
            "me": "GET /me (requires auth)",
            "admin": "GET /admin (requires admin)",
            "public": "GET /public-or-protected (optional auth)",
        },
    }


@app.post("/login")
def login(username: str, password: str):
    """
    Login endpoint - returns JWT token.

    Query parameters:
    - username: User's username
    - password: User's password

    In production:
    - Use request body with Pydantic model instead of query params
    - Validate password against hashed password in database
    - Use proper password hashing (bcrypt, argon2)
    - Rate limit login attempts
    - Log failed attempts
    """
    # Mock authentication (replace with real password validation)
    user = get_user_by_username(username)
    if not user or password != "password123":  # NEVER do this in production!
        raise HTTPException(status_code=401, detail="Incorrect username or password")  # Create JWT token
    token_data = {
        "sub": user.username,  # "sub" (subject) is the user identifier
        "user_id": user.user_id,
        "email": user.email,
        "is_admin": user.is_admin,
    }
    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


# ----------------------------------------------------------------------------
# Protected endpoints (authentication required)
# ----------------------------------------------------------------------------


@app.get("/me")
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get current user info - requires authentication.

    The magic happens in Depends(get_current_user):
    1. HTTPBearer extracts token from "Authorization: Bearer <token>" header
    2. get_current_user decodes JWT and validates it
    3. Returns User object
    4. If any step fails, returns 401/403 automatically
    """
    return {
        "message": "This is your profile",
        "user": current_user.to_dict(),
    }


@app.get("/token-info")
def get_token_info(token: Annotated[str, Depends(get_token)]):
    """
    Decode token and show its contents - requires authentication.

    This shows how to access the raw token if needed.
    """
    payload = decode_access_token(token)
    return {
        "token_payload": payload,
        "note": "In production, avoid exposing raw token data",
    }


# ----------------------------------------------------------------------------
# Admin-only endpoints (requires admin role)
# ----------------------------------------------------------------------------


@app.get("/admin")
def admin_only(admin_user: Annotated[User, Depends(get_current_active_admin)]):
    """
    Admin-only endpoint - requires authentication + admin role.

    This shows DEPENDENCY CHAINING:
    get_current_active_admin -> get_current_user -> bearer_scheme
    """
    return {
        "message": "Welcome to admin panel",
        "admin": admin_user.to_dict(),
        "note": "Only admins can see this",
    }


# ----------------------------------------------------------------------------
# Optional authentication (works for both authenticated and anonymous)
# ----------------------------------------------------------------------------


@app.get("/public-or-protected")
def public_or_protected(user: Annotated[Optional[User], Depends(get_optional_user)]):
    """
    Endpoint with optional authentication.

    - If user provides valid token: returns personalized message
    - If no token or invalid token: returns public message

    This is useful for endpoints like:
    - Homepage (show "Login" vs "Welcome, {username}")
    - Product list (show prices based on user tier)
    - Content (show more for authenticated users)
    """
    if user:
        return {
            "message": f"Welcome back, {user.username}!",
            "authenticated": True,
            "user": user.to_dict(),
        }
    else:
        return {
            "message": "Welcome, guest!",
            "authenticated": False,
            "note": "Login to see personalized content",
        }


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

# Lambda handler
from fastapi_lambda import create_lambda_handler  # noqa: E402

lambda_handler = create_lambda_handler(app)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
1. Login to get token:

   POST /login
   Body: {"username": "alice", "password": "password123"}

   Response:
   {
     "access_token": "eyJ0eXAi...",
     "token_type": "bearer",
     "user": {"user_id": 1, "username": "alice", ...}
   }


2. Use token to access protected endpoint:

   GET /me
   Headers: {"Authorization": "Bearer eyJ0eXAi..."}

   Response:
   {
     "message": "This is your profile",
     "user": {"user_id": 1, "username": "alice", ...}
   }


3. Try to access without token:

   GET /me

   Response: 403 Forbidden
   {
     "detail": "Not authenticated"
   }


4. Access admin endpoint as non-admin:

   GET /admin
   Headers: {"Authorization": "Bearer <bob's token>"}

   Response: 403 Forbidden
   {
     "detail": "Not enough permissions"
   }


5. Optional authentication:

   GET /public-or-protected
   # No header -> guest message

   GET /public-or-protected
   Headers: {"Authorization": "Bearer <alice's token>"}
   # Authenticated -> personalized message
"""


# ============================================================================
# PRODUCTION CHECKLIST
# ============================================================================

"""
For production use, replace the mock implementations with:

1. JWT Library:
   - Install: pip install PyJWT
   - Use proper signing/verification with RS256 or HS256
   - Validate exp, iss, aud claims

2. Password Hashing:
   - Install: pip install passlib[bcrypt]
   - Hash passwords with bcrypt before storing
   - Compare hashed passwords during login

3. Secret Management:
   - Store JWT secret in AWS Secrets Manager
   - Rotate secrets regularly
   - Use different secrets for dev/staging/prod

4. Database:
   - Replace USERS_DB dict with real database (DynamoDB, RDS)
   - Cache user lookups to reduce DB queries
   - Use database connection pooling

5. Token Best Practices:
   - Short expiration (15-60 minutes)
   - Implement refresh tokens
   - Blacklist revoked tokens
   - Include minimal claims in token

6. Security Headers:
   - Add rate limiting (API Gateway can do this)
   - Log authentication failures
   - Monitor for brute force attacks
   - Use HTTPS only (API Gateway enforces this)

7. Error Handling:
   - Don't leak information in error messages
   - Log security events
   - Return generic "Invalid credentials" messages
   - Implement proper exception handling
"""

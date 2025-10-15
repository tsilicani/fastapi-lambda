# FastAPI-Lambda Examples

This directory contains example implementations demonstrating various features of FastAPI-Lambda.

## Examples

### `jwt_auth.py` - JWT Authentication

Complete example showing how to implement JWT authentication in FastAPI-Lambda.

**Features demonstrated:**
- ✅ Extract JWT tokens from `Authorization: Bearer` header using `HTTPBearer`
- ✅ Decode and validate JWT tokens
- ✅ Create user context from validated tokens
- ✅ Protect endpoints with authentication
- ✅ Optional authentication (public + protected endpoints)
- ✅ Role-based access control (admin-only endpoints)
- ✅ Dependency chaining

**Key concepts:**

1. **HTTPBearer is a Dependency, NOT a Middleware**
   ```python
   from fastapi_lambda.security import HTTPBearer, HTTPAuthorizationCredentials
   
   security = HTTPBearer()
   
   @app.get("/protected")
   def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
       token = credentials.credentials  # The actual JWT token
       # ... decode and validate token
   ```

2. **Dependency Chaining for User Context**
   ```python
   async def get_current_user(
       credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
   ) -> User:
       token = credentials.credentials
       payload = decode_jwt(token)
       return get_user_from_db(payload["sub"])
   
   @app.get("/me")
   def read_me(user: Annotated[User, Depends(get_current_user)]):
       return {"user": user}
   ```

3. **Optional Authentication**
   ```python
   optional_auth = HTTPBearer(auto_error=False)
   
   @app.get("/public-or-protected")
   def flexible(user: Annotated[Optional[User], Depends(get_optional_user)]):
       if user:
           return {"message": f"Hello, {user.username}"}
       return {"message": "Hello, guest"}
   ```

**Usage:**

```bash
# Test locally (requires deployment to Lambda or local Lambda emulator)

# 1. Login to get token
curl -X POST http://localhost:3000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "password123"}'

# Response: {"access_token": "...", "token_type": "bearer"}

# 2. Use token to access protected endpoint
curl http://localhost:3000/me \
  -H "Authorization: Bearer <your-token>"

# 3. Try without token (should fail)
curl http://localhost:3000/me

# 4. Access admin endpoint
curl http://localhost:3000/admin \
  -H "Authorization: Bearer <alice-token>"
```

**Production Checklist:**

The example uses simplified JWT encoding/decoding for demonstration. For production:

- [ ] **Use PyJWT or python-jose** for proper JWT handling
  ```bash
  pip install PyJWT
  ```

- [ ] **Hash passwords** with bcrypt
  ```bash
  pip install passlib[bcrypt]
  ```

- [ ] **Store secrets in AWS Secrets Manager**
  - JWT signing key
  - Database credentials
  - API keys

- [ ] **Validate JWT claims**
  - `exp` (expiration)
  - `iss` (issuer)
  - `aud` (audience)

- [ ] **Implement refresh tokens**
  - Short-lived access tokens (15-60 min)
  - Long-lived refresh tokens (7-30 days)
  - Token rotation on refresh

- [ ] **Add rate limiting**
  - Use API Gateway throttling
  - Track failed login attempts
  - Implement account lockout

- [ ] **Use a real database**
  - DynamoDB for serverless
  - RDS for relational data
  - Cache user lookups

## Running Examples

### Local Testing

1. **Install dependencies:**
   ```bash
   pip install fastapi-lambda PyJWT passlib[bcrypt]
   ```

2. **Run with AWS SAM Local or Serverless Framework:**
   ```bash
   # With Serverless Framework
   sls offline start
   
   # Or AWS SAM
   sam local start-api
   ```

### Deploy to Lambda

1. **Create `serverless.yml`:**
   ```yaml
   service: fastapi-lambda-examples
   
   provider:
     name: aws
     runtime: python3.11
     region: us-east-1
   
   functions:
     jwt-auth:
       handler: examples/jwt_auth.lambda_handler
       url:
         cors: true
       events:
         - httpApi:
             path: /{proxy+}
             method: "*"
   ```

2. **Deploy:**
   ```bash
   serverless deploy
   ```

3. **Test deployed endpoint:**
   ```bash
   curl https://your-lambda-url.amazonaws.com/login -X POST \
     -H "Content-Type: application/json" \
     -d '{"username": "alice", "password": "password123"}'
   ```

## Common Questions

### Q: Why is HTTPBearer a dependency and not a middleware?

**A:** In FastAPI/FastAPI-Lambda, authentication is handled per-endpoint using the dependency injection system, not globally via middleware. This provides:

- ✅ **Granular control** - Different endpoints can use different auth schemes
- ✅ **Type safety** - Dependencies provide typed user objects
- ✅ **Automatic OpenAPI docs** - Security schemes appear in `/openapi.json`
- ✅ **Easier testing** - Can override dependencies in tests

### Q: How do I decode JWT tokens?

**A:** FastAPI-Lambda provides `HTTPBearer` which extracts the token from the header, but you must decode it yourself:

```python
import jwt

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
) -> User:
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        return get_user_from_db(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Q: Can I use middleware for authentication instead?

**A:** You *could* write a custom middleware, but it's not recommended because:

- ❌ Less flexible (all-or-nothing authentication)
- ❌ No automatic OpenAPI documentation
- ❌ Harder to test
- ❌ Can't have different auth per endpoint
- ❌ Loses type safety

**Dependencies are the FastAPI way** - use them!

### Q: How do I implement refresh tokens?

**A:** Create a separate endpoint that accepts a refresh token and returns a new access token:

```python
@app.post("/refresh")
def refresh_token(refresh_token: str):
    # Validate refresh token
    payload = decode_refresh_token(refresh_token)
    
    # Create new access token
    access_token = create_access_token({"sub": payload["sub"]})
    
    return {"access_token": access_token, "token_type": "bearer"}
```

Store refresh tokens in a database and invalidate them on logout.

## Contributing

To add a new example:

1. Create a new Python file in this directory
2. Add comprehensive comments explaining the feature
3. Include usage examples in docstrings
4. Add a section to this README
5. Ensure the example is self-contained and runnable

## See Also

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io - JWT Debugger](https://jwt.io/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

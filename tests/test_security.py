"""Test security and authentication."""

from typing import Annotated, Optional

import pytest

from fastapi_lambda.app import FastAPI
from fastapi_lambda.params import Depends
from fastapi_lambda.security import HTTPAuthorizationCredentials, HTTPBearer
from tests.conftest import parse_response


@pytest.mark.asyncio
async def test_bearer_auth_success(make_event):
    """Test Bearer authentication with valid token."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"token": credentials.credentials, "scheme": credentials.scheme}

    event = make_event("GET", "/protected", headers={"Authorization": "Bearer secret123"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["token"] == "secret123"
    assert body["scheme"] == "Bearer"


@pytest.mark.asyncio
async def test_bearer_auth_missing_token(make_event):
    """Test Bearer authentication without token returns 403."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"ok": True}

    event = make_event("GET", "/protected")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 403
    assert "Not authenticated" in body.get("detail", "")


@pytest.mark.asyncio
async def test_bearer_auth_invalid_scheme(make_event):
    """Test Bearer authentication with wrong scheme returns 403."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"ok": True}

    event = make_event("GET", "/protected", headers={"Authorization": "Basic abc"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 403


@pytest.mark.asyncio
async def test_bearer_auth_optional(make_event):
    """Test optional Bearer authentication (auto_error=False)."""
    app = FastAPI()
    security = HTTPBearer(auto_error=False)

    @app.get("/maybe-protected", response_model=None)
    async def maybe_protected(
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    ):
        if credentials:
            return {"authenticated": True, "token": credentials.credentials}
        return {"authenticated": False}

    # Without token
    event = make_event("GET", "/maybe-protected")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["authenticated"] is False

    # With token
    event = make_event("GET", "/maybe-protected", headers={"Authorization": "Bearer token123"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["authenticated"] is True
    assert body["token"] == "token123"


@pytest.mark.asyncio
async def test_user_context_from_token(make_event):
    """Test creating user context from Bearer token."""
    app = FastAPI()
    security = HTTPBearer()

    async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> dict:
        token = credentials.credentials
        return {"user_id": 123, "username": "testuser", "token": token}

    @app.get("/me", response_model=None)
    async def read_user_me(user: Annotated[dict, Depends(get_current_user)]):
        return user

    event = make_event("GET", "/me", headers={"Authorization": "Bearer my_token"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["user_id"] == 123
    assert body["username"] == "testuser"
    assert body["token"] == "my_token"


@pytest.mark.asyncio
async def test_http_base_custom_scheme(make_event):
    """Test HTTPBase with custom authentication scheme."""
    from fastapi_lambda.security import HTTPBase

    app = FastAPI()
    security = HTTPBase(scheme="ApiKey", description="Custom API Key auth")

    @app.get("/api", response_model=None)
    async def api_endpoint(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"scheme": credentials.scheme, "key": credentials.credentials}

    event = make_event("GET", "/api", headers={"Authorization": "ApiKey abc123xyz"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["scheme"] == "ApiKey"
    assert body["key"] == "abc123xyz"


@pytest.mark.asyncio
async def test_http_base_optional_auth(make_event):
    """Test HTTPBase with optional authentication."""
    from fastapi_lambda.security import HTTPBase

    app = FastAPI()
    security = HTTPBase(scheme="Token", auto_error=False)

    @app.get("/data", response_model=None)
    async def get_data(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]):
        if credentials:
            return {"protected": True, "token": credentials.credentials}
        return {"protected": False, "public": "data"}

    event = make_event("GET", "/data")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["protected"] is False

    event = make_event("GET", "/data", headers={"Authorization": "Token xyz789"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["protected"] is True
    assert body["token"] == "xyz789"


@pytest.mark.asyncio
async def test_bearer_optional_wrong_scheme(make_event):
    """Test Bearer with auto_error=False and wrong scheme returns None."""
    app = FastAPI()
    security = HTTPBearer(auto_error=False)

    @app.get("/test", response_model=None)
    async def test_endpoint(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]):
        return {"has_auth": credentials is not None}

    event = make_event("GET", "/test", headers={"Authorization": "Basic user:pass"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["has_auth"] is False


@pytest.mark.asyncio
async def test_http_base_missing_auth(make_event):
    """Test HTTPBase with missing authorization header raises 403."""
    from fastapi_lambda.security import HTTPBase

    app = FastAPI()
    security = HTTPBase(scheme="Custom")

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"ok": True}

    event = make_event("GET", "/protected")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 403
    assert "Not authenticated" in body.get("detail", "")

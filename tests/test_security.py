"""Test security and authentication."""

from typing import Annotated, Optional

import pytest

from fastapifn.app import FastAPI
from fastapifn.params import Depends
from fastapifn.security import HTTPAuthorizationCredentials, HTTPBearer
from tests.conftest import parse_response


@pytest.mark.asyncio
async def test_bearer_auth_success(make_event, lambda_context):
    """Test Bearer authentication with valid token."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"token": credentials.credentials, "scheme": credentials.scheme}

    event = make_event("GET", "/protected", headers={"Authorization": "Bearer secret123"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["token"] == "secret123"
    assert body["scheme"] == "Bearer"


@pytest.mark.asyncio
async def test_bearer_auth_missing_token(make_event, lambda_context):
    """Test Bearer authentication without token returns 403."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"ok": True}

    event = make_event("GET", "/protected")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 403
    assert "Not authenticated" in body.get("detail", "")


@pytest.mark.asyncio
async def test_bearer_auth_invalid_scheme(make_event, lambda_context):
    """Test Bearer authentication with wrong scheme returns 403."""
    app = FastAPI()
    security = HTTPBearer()

    @app.get("/protected", response_model=None)
    async def protected(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
        return {"ok": True}

    event = make_event("GET", "/protected", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 403


@pytest.mark.asyncio
async def test_bearer_auth_optional(make_event, lambda_context):
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
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["authenticated"] is False

    # With token
    event = make_event("GET", "/maybe-protected", headers={"Authorization": "Bearer token123"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["authenticated"] is True
    assert body["token"] == "token123"


@pytest.mark.asyncio
async def test_user_context_from_token(make_event, lambda_context):
    """Test creating user context from Bearer token."""
    app = FastAPI()
    security = HTTPBearer()

    # Simula estrazione user da token
    async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> dict:
        # In produzione: decodifica JWT, query DB, ecc.
        # Qui solo simulazione
        token = credentials.credentials
        return {"user_id": 123, "username": "testuser", "token": token}

    @app.get("/me", response_model=None)
    async def read_user_me(user: Annotated[dict, Depends(get_current_user)]):
        return user

    event = make_event("GET", "/me", headers={"Authorization": "Bearer mytoken"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["user_id"] == 123
    assert body["username"] == "testuser"
    assert body["token"] == "mytoken"

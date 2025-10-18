"""Tests for param_functions - 100% coverage with minimal code."""
import pytest

from fastapi_lambda.app import FastAPI
from tests.conftest import parse_response


@pytest.mark.asyncio
async def test_path_function(make_event, lambda_context):
    """Test Path() wrapper function."""
    from fastapi_lambda.param_functions import Path

    app = FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int = Path(gt=0, description="Item ID")):
        return {"item_id": item_id}

    event = make_event("GET", "/items/42")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["item_id"] == 42


@pytest.mark.asyncio
async def test_header_function(make_event, lambda_context):
    """Test Header() wrapper function."""
    from fastapi_lambda.param_functions import Header

    app = FastAPI()

    @app.get("/protected")
    async def protected(x_api_key: str = Header(description="API Key")):
        return {"key": x_api_key}

    event = make_event("GET", "/protected", headers={"x-api-key": "secret123"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["key"] == "secret123"


@pytest.mark.asyncio
async def test_security_function(make_event, lambda_context):
    """Test Security() wrapper function."""
    from fastapi_lambda.param_functions import Security

    app = FastAPI()

    async def get_current_user():
        return {"user": "test"}

    @app.get("/secure")
    async def secure_endpoint(user=Security(get_current_user, scopes=["read", "write"])):
        return user

    event = make_event("GET", "/secure")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["user"] == "test"

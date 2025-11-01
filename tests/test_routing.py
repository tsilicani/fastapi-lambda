"""Test routing functionality."""

import pytest
from pydantic import BaseModel

from typing import cast

from fastapi_lambda.applications import FastAPI, create_lambda_handler
from fastapi_lambda.exceptions import FastAPIError
from fastapi_lambda.response import Response
from fastapi_lambda.routing import Convertor
from fastapi_lambda.types import HttpMethod
from tests.conftest import parse_response
from tests.utils import make_event


@pytest.mark.asyncio
async def test_get_route():
    """Test GET route."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "hello"}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["message"] == "hello"


def test_get_route_with_lambda_handler():
    """Test GET route using create_lambda_handler."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "hello"}

    handler = create_lambda_handler(app)
    event = make_event(method="GET", path="/")
    response = handler(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["message"] == "hello"


@pytest.mark.asyncio
async def test_post_route():
    """Test POST route."""
    app = FastAPI()

    @app.post("/items")
    async def create_item():
        return {"created": True}

    event = make_event(method="POST", path="/items")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["created"] is True


@pytest.mark.asyncio
async def test_path_parameters():
    """Test path parameters."""
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    event = make_event(method="GET", path="/items/42", path_params={"item_id": "42"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["item_id"] == 42


@pytest.mark.asyncio
async def test_query_parameters():
    """Test query parameters."""
    app = FastAPI()

    @app.get("/search")
    async def search(q: str = "default"):
        return {"query": q}

    event = make_event(method="GET", path="/search", query={"q": "test"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["query"] == "test"


@pytest.mark.asyncio
async def test_multiple_methods():
    """Test multiple HTTP methods on same path."""
    app = FastAPI()

    @app.get("/resource")
    async def get_resource():
        return {"method": "GET"}

    @app.post("/resource")
    async def create_resource():
        return {"method": "POST"}

    @app.put("/resource")
    async def update_resource():
        return {"method": "PUT"}

    @app.delete("/resource")
    async def delete_resource():
        return {"method": "DELETE"}

    @app.patch("/resource")
    async def patch_resource():
        return {"method": "PATCH"}

    # Test each method
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        event = make_event(method=cast(HttpMethod, method), path="/resource")
        response = await app(event)
        status, body = parse_response(response)
        assert status == 200
        assert body["method"] == method


@pytest.mark.asyncio
async def test_404_not_found():
    """Test 404 for non-existent route."""
    app = FastAPI()

    @app.get("/exists")
    async def exists():
        return {"ok": True}

    event = make_event(method="GET", path="/does-not-exist")
    response = await app(event)

    assert response["statusCode"] == 404


@pytest.mark.asyncio
async def test_sync_endpoint():
    """Test synchronous endpoint (non-async def)."""
    app = FastAPI()

    @app.get("/sync")
    def sync_endpoint():
        return {"type": "sync"}

    event = make_event(method="GET", path="/sync")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "sync"


@pytest.mark.asyncio
async def test_mixed_sync_async_endpoints():
    """Test mix of sync and async endpoints."""
    app = FastAPI()

    @app.get("/sync")
    def sync_endpoint():
        return {"type": "sync"}

    @app.get("/async")
    async def async_endpoint():
        return {"type": "async"}

    # Test sync endpoint
    event = make_event(method="GET", path="/sync")
    response = await app(event)
    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "sync"

    # Test async endpoint
    event = make_event(method="GET", path="/async")
    response = await app(event)
    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "async"


@pytest.mark.asyncio
async def test_path_convertor_types():
    """Test different path parameter types (str, int, path)."""
    app = FastAPI()

    @app.get("/items/{item_id:int}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    @app.get("/files/{file_path:path}")
    async def get_file(file_path: str):
        return {"path": file_path}

    # Test int convertor
    event = make_event(method="GET", path="/items/123")
    response = await app(event)
    status, body = parse_response(response)
    assert status == 200
    assert body["item_id"] == 123

    # Test path convertor (matches everything including slashes)
    event = make_event(method="GET", path="/files/folder/subfolder/file.txt")
    response = await app(event)
    status, body = parse_response(response)
    assert status == 200
    assert body["path"] == "folder/subfolder/file.txt"


@pytest.mark.asyncio
async def test_invalid_convertor_type():
    """Test that invalid convertor type raises ValueError."""
    app = FastAPI()

    with pytest.raises(ValueError, match="Unknown path convertor 'invalid'"):

        @app.get("/items/{item_id:invalid}")
        async def get_item(item_id):
            return {}


@pytest.mark.asyncio
async def test_post_with_invalid_json():
    """Test POST with non-JSON body (should not crash)."""
    app = FastAPI()

    @app.post("/items")
    async def create_item():
        return {"created": True}

    # Send invalid JSON
    event = make_event(method="POST", path="/items")
    event["body"] = "not-valid-json{"
    response = await app(event)

    # Should still succeed (body parsing error is caught)
    status, body = parse_response(response)
    assert status == 200
    assert body["created"] is True


@pytest.mark.asyncio
async def test_response_model():
    """Test response_model validation and serialization."""

    app = FastAPI()

    class Item(BaseModel):
        name: str
        price: float

    @app.get("/items/{item_id}", response_model=Item)
    async def get_item(item_id: int):
        # Return dict with extra field (should be filtered)
        return {"name": "Widget", "price": 9.99, "internal_id": 12345}

    event = make_event(method="GET", path="/items/1")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body == {"name": "Widget", "price": 9.99}
    assert "internal_id" not in body


@pytest.mark.asyncio
async def test_return_lambda_response_directly():
    """Test returning Response directly from endpoint."""

    app = FastAPI()

    @app.get("/custom")
    async def custom_response():
        return Response(content="custom content", status_code=201, headers={"X-Custom": "header"})

    event = make_event(method="GET", path="/custom")
    response = await app(event)

    assert response["statusCode"] == 201
    assert response["headers"]["X-Custom"] == "header"
    assert "custom content" in response["body"]


def test_base_convertor_not_implemented():
    """Test that base Convertor.convert() raises NotImplementedError."""

    convertor = Convertor()
    with pytest.raises(NotImplementedError):
        convertor.convert("test")


def test_invalid_response_model():
    """Test that invalid response_model raises FastAPIError at route creation."""

    app = FastAPI()

    # Try to use Response as response_model (invalid - it's not a Pydantic model)
    with pytest.raises(FastAPIError, match="Invalid args for response field"):

        @app.get("/invalid", response_model=Response)  # type: ignore
        async def invalid_endpoint():
            return {"data": "test"}

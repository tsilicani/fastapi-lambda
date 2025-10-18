"""Test routing functionality."""

import pytest

from fastapi_lambda.app import FastAPI, create_lambda_handler
from tests.conftest import parse_response


@pytest.mark.asyncio
async def test_get_route(make_event, lambda_context):
    """Test GET route."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "hello"}

    event = make_event("GET", "/")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["message"] == "hello"


def test_get_route_with_lambda_handler(make_event, lambda_context):
    """Test GET route using create_lambda_handler."""
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "hello"}

    handler = create_lambda_handler(app)
    event = make_event("GET", "/")
    response = handler(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["message"] == "hello"


@pytest.mark.asyncio
async def test_post_route(make_event, lambda_context):
    """Test POST route."""
    app = FastAPI()

    @app.post("/items")
    async def create_item():
        return {"created": True}

    event = make_event("POST", "/items")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["created"] is True


@pytest.mark.asyncio
async def test_path_parameters(make_event, lambda_context):
    """Test path parameters."""
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"item_id": item_id}

    event = make_event("GET", "/items/42", path_params={"item_id": "42"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["item_id"] == 42


@pytest.mark.asyncio
async def test_query_parameters(make_event, lambda_context):
    """Test query parameters."""
    app = FastAPI()

    @app.get("/search")
    async def search(q: str = "default"):
        return {"query": q}

    event = make_event("GET", "/search", query={"q": "test"})
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["query"] == "test"


@pytest.mark.asyncio
async def test_multiple_methods(make_event, lambda_context):
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
        event = make_event(method, "/resource")
        response = await app(event, lambda_context)
        status, body = parse_response(response)
        assert status == 200
        assert body["method"] == method


@pytest.mark.asyncio
async def test_404_not_found(make_event, lambda_context):
    """Test 404 for non-existent route."""
    app = FastAPI()

    @app.get("/exists")
    async def exists():
        return {"ok": True}

    event = make_event("GET", "/does-not-exist")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 404


@pytest.mark.asyncio
async def test_sync_endpoint(make_event, lambda_context):
    """Test synchronous endpoint (non-async def)."""
    app = FastAPI()

    @app.get("/sync")
    def sync_endpoint():
        return {"type": "sync"}

    event = make_event("GET", "/sync")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "sync"


@pytest.mark.asyncio
async def test_mixed_sync_async_endpoints(make_event, lambda_context):
    """Test mix of sync and async endpoints."""
    app = FastAPI()

    @app.get("/sync")
    def sync_endpoint():
        return {"type": "sync"}

    @app.get("/async")
    async def async_endpoint():
        return {"type": "async"}

    # Test sync endpoint
    event = make_event("GET", "/sync")
    response = await app(event, lambda_context)
    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "sync"

    # Test async endpoint
    event = make_event("GET", "/async")
    response = await app(event, lambda_context)
    status, body = parse_response(response)
    assert status == 200
    assert body["type"] == "async"

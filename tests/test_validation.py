"""Test Pydantic validation."""

from typing import Optional

import pytest
from pydantic import BaseModel

from fastapi_lambda.app import FastAPI
from fastapi_lambda.param_functions import Body, Query
from fastapi_lambda.params import Depends
from tests.conftest import parse_response
from tests.utils import make_event


class Item(BaseModel):
    name: str
    price: float
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float


@pytest.mark.asyncio
async def test_request_body_validation():
    """Test request body validation with Pydantic."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item):
        return {"name": item.name, "price": item.price}

    # Valid body
    event = make_event("POST", "/items", body={"name": "Widget", "price": 9.99})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["name"] == "Widget"
    assert body["price"] == 9.99


@pytest.mark.asyncio
async def test_validation_error_422():
    """Test validation error returns 422."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item):
        return {"ok": True}

    # Invalid body (missing required fields)
    event = make_event("POST", "/items", body={"invalid": "data"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 422
    assert "detail" in body


@pytest.mark.asyncio
async def test_response_model_serialization():
    """Test response model serialization."""
    app = FastAPI()

    @app.get("/items/{item_id}", response_model=ItemResponse)
    async def get_item(item_id: int):
        # Returns more fields than ItemResponse, should be filtered
        return {
            "id": item_id,
            "name": "Widget",
            "price": 19.99,
            "secret": "should_not_appear",  # Extra field
        }

    event = make_event("GET", "/items/1", path_params={"item_id": "1"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["id"] == 1
    assert body["name"] == "Widget"
    assert body["price"] == 19.99
    # Extra field should NOT be in response
    assert "secret" not in body


@pytest.mark.asyncio
async def test_optional_fields():
    """Test optional fields in Pydantic models."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item):
        return {"name": item.name, "has_description": item.description is not None}

    # Without optional field
    event = make_event("POST", "/items", body={"name": "Widget", "price": 9.99})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["has_description"] is False

    # With optional field
    event = make_event(
        "POST",
        "/items",
        body={"name": "Widget", "price": 9.99, "description": "A nice widget"},
    )
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["has_description"] is True


@pytest.mark.asyncio
async def test_type_coercion():
    """Test Pydantic type coercion."""
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int):
        return {"item_id": item_id, "type": type(item_id).__name__}

    event = make_event("GET", "/items/42", path_params={"item_id": "42"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["item_id"] == 42
    assert body["type"] == "int"


@pytest.mark.asyncio
async def test_query_with_examples():
    """Test Query parameter with examples."""

    app = FastAPI()

    @app.get("/search")
    async def search(q: str = Query(examples=[{"example1": "test"}])):
        return {"query": q}

    event = make_event("GET", "/search", None, {"q": "hello"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["query"] == "hello"


@pytest.mark.asyncio
async def test_body_with_examples():
    """Test Body parameter with examples."""

    app = FastAPI()

    @app.post("/items")
    async def create_item(name: str = Body(examples=["widget", "gadget"])):
        return {"name": name}

    event = make_event("POST", "/items", "test_name")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["name"] == "test_name"


@pytest.mark.asyncio
async def test_depends_repr():
    """Test Depends __repr__ for coverage."""

    async def my_dep():
        return 42

    dep = Depends(my_dep)
    assert "my_dep" in repr(dep)

    dep_no_cache = Depends(my_dep, use_cache=False)
    assert "use_cache=False" in repr(dep_no_cache)

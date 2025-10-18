"""Test OpenAPI schema generation."""

from typing import Optional

import pytest
from pydantic import BaseModel

from fastapi_lambda.app import FastAPI


class Item(BaseModel):
    name: str
    price: float


@pytest.mark.asyncio
async def test_openapi_endpoint(make_event, lambda_context):
    """Test /openapi.json endpoint exists."""
    app = FastAPI(title="Test API", version="1.0.0")

    @app.get("/")
    async def root():
        return {"ok": True}

    event = make_event("GET", "/openapi.json")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 200
    assert "application/json" in response["headers"]["Content-Type"]


def test_openapi_schema_structure():
    """Test OpenAPI schema structure."""
    app = FastAPI(title="Test API", version="1.0.0", description="Test description")

    @app.get("/")
    async def root():
        return {"ok": True}

    schema = app.openapi()

    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["title"] == "Test API"
    assert schema["info"]["version"] == "1.0.0"
    assert schema["info"]["description"] == "Test description"
    assert "paths" in schema
    assert "/" in schema["paths"]


def test_openapi_path_parameters():
    """Test path parameters appear in schema."""
    app = FastAPI()

    @app.get("/items/{item_id}")
    async def get_item(item_id: int, q: Optional[str] = None):
        return {"item_id": item_id}

    schema = app.openapi()

    path_item = schema["paths"]["/items/{item_id}"]["get"]
    params = path_item["parameters"]

    # Should have 2 parameters: item_id (path) and q (query)
    assert len(params) == 2

    # Check path parameter
    path_param = next(p for p in params if p["name"] == "item_id")
    assert path_param["in"] == "path"
    assert path_param["required"] is True
    assert path_param["schema"]["type"] == "integer"

    # Check query parameter
    query_param = next(p for p in params if p["name"] == "q")
    assert query_param["in"] == "query"
    assert query_param["required"] is False


def test_openapi_request_body():
    """Test request body appears in schema."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item):
        return {"ok": True}

    schema = app.openapi()

    operation = schema["paths"]["/items"]["post"]
    assert "requestBody" in operation
    assert operation["requestBody"]["required"] is True
    assert "application/json" in operation["requestBody"]["content"]


def test_openapi_response_model():
    """Test response model appears in schema."""
    app = FastAPI()

    @app.get("/items/{item_id}", response_model=Item)
    async def get_item(item_id: int):
        return {"name": "Widget", "price": 9.99}

    schema = app.openapi()

    operation = schema["paths"]["/items/{item_id}"]["get"]
    response_200 = operation["responses"]["200"]
    assert "content" in response_200
    assert "application/json" in response_200["content"]


def test_openapi_model_description_truncation():
    """Test model description truncation with \\f character.

    The \\f (form feed) character allows keeping detailed docs in code
    while showing only concise descriptions in OpenAPI schema.
    """
    app = FastAPI()

    class DetailedModel(BaseModel):
        """Short description for API docs.
        \f
        This detailed explanation is only for code documentation tools
        like Sphinx or IDEs, and won't appear in OpenAPI schema.
        """
        value: str

    @app.get("/detailed", response_model=DetailedModel)
    async def get_detailed():
        return {"value": "test"}

    schema = app.openapi()

    # Check that model definition exists in components
    assert "components" in schema
    assert "schemas" in schema["components"]
    assert "DetailedModel" in schema["components"]["schemas"]

    # Verify description is truncated at \f character
    model_schema = schema["components"]["schemas"]["DetailedModel"]
    assert "description" in model_schema
    description = model_schema["description"]

    # Should contain the short description
    assert "Short description for API docs" in description

    # Should NOT contain the detailed part after \f
    assert "Sphinx" not in description
    assert "IDEs" not in description


def test_openapi_validation_error_response():
    """Test 422 validation error response in schema."""
    app = FastAPI()

    @app.post("/items")
    async def create_item(item: Item):
        return {"ok": True}

    schema = app.openapi()

    operation = schema["paths"]["/items"]["post"]
    # Should have 422 response for validation errors
    assert "422" in operation["responses"]
    assert "Validation Error" in operation["responses"]["422"]["description"]


def test_openapi_tags():
    """Test tags appear in schema."""
    app = FastAPI(tags=[{"name": "items", "description": "Item operations"}])

    @app.get("/items", tags=["items"])
    async def list_items():
        return []

    schema = app.openapi()

    assert "tags" in schema
    assert len(schema["tags"]) == 1
    assert schema["tags"][0]["name"] == "items"

    operation = schema["paths"]["/items"]["get"]
    assert "tags" in operation
    assert "items" in operation["tags"]


def test_openapi_exclude_route():
    """Test include_in_schema=False excludes route from schema."""
    app = FastAPI()

    @app.get("/public")
    async def public():
        return {"ok": True}

    # This route should NOT appear in OpenAPI schema
    app.add_route("/internal", lambda: {"ok": True}, ["GET"], include_in_schema=False)

    schema = app.openapi()

    assert "/public" in schema["paths"]
    assert "/internal" not in schema["paths"]


def test_openapi_disable():
    """Test disabling OpenAPI endpoint."""
    app = FastAPI(openapi_url=None)

    @app.get("/")
    async def root():
        return {"ok": True}

    # OpenAPI schema can still be generated programmatically
    schema = app.openapi()
    assert schema["openapi"] == "3.1.0"


def test_openapi_examples_with_complex_types():
    """Test OpenAPI examples with UUID, Decimal, Enum, datetime."""
    from decimal import Decimal
    from enum import Enum
    from uuid import UUID

    from fastapi_lambda import Body, Query

    class Status(Enum):
        ACTIVE = "active"

    class Product(BaseModel):
        id: UUID
        price: Decimal

    app = FastAPI()

    # Query param with UUID example
    @app.get("/items")
    def get_items(item_id: UUID = Query(example=UUID("12345678-1234-5678-1234-567812345678"))):
        return {"item_id": item_id}

    # Body with complex types
    @app.post("/products")
    def create_product(
        product: Product = Body(
            example={
                "id": UUID("11111111-1111-1111-1111-111111111111"),
                "price": Decimal("99.99"),
            }
        )
    ):
        return {"ok": True}

    schema = app.openapi()

    # Check query param example (UUID → string)
    query_param = schema["paths"]["/items"]["get"]["parameters"][0]
    assert query_param["example"] == "12345678-1234-5678-1234-567812345678"

    # Check body example (UUID → string, Decimal → float)
    body_example = schema["paths"]["/products"]["post"]["requestBody"]["content"]["application/json"]["example"]
    assert body_example["id"] == "11111111-1111-1111-1111-111111111111"
    assert body_example["price"] == 99.99


def test_openapi_examples_all_types():
    """Test _jsonable_encoder with all supported types."""
    from datetime import datetime, timedelta
    from decimal import Decimal
    from enum import Enum
    from pathlib import Path

    from fastapi_lambda import Body

    class Priority(Enum):
        HIGH = "high"
        LOW = "low"

    class Task(BaseModel):
        name: str

    app = FastAPI()

    @app.post("/tasks")
    def create_task(
        task: Task = Body(
            example={
                "name": "Complete project",
                "enum_field": Priority.HIGH,
                "date": datetime(2024, 1, 15),
                "duration": timedelta(hours=2),
                "int_price": Decimal("100"),
                "float_price": Decimal("19.99"),
                "path": Path("/tmp/file.txt"),
                "data": b"binary",
                "tags": {"python", "fastapi"},
            }
        )
    ):
        return {"ok": True}

    schema = app.openapi()
    example = schema["paths"]["/tasks"]["post"]["requestBody"]["content"]["application/json"]["example"]

    # Verify all types are serialized
    assert example["name"] == "Complete project"
    assert example["enum_field"] == "high"
    assert example["date"] == "2024-01-15T00:00:00"
    assert example["duration"] == 7200.0
    assert example["int_price"] == 100  # int not float
    assert example["float_price"] == 19.99
    assert example["path"] == "/tmp/file.txt"
    assert example["data"] == "binary"
    assert isinstance(example["tags"], list)
    assert set(example["tags"]) == {"python", "fastapi"}


def test_openapi_examples_edge_cases():
    """Test _jsonable_encoder edge cases for 100% coverage."""
    from datetime import time
    from uuid import UUID

    from fastapi_lambda import Body

    class TestProduct(BaseModel):
        id: UUID
        name: str
        price: float

    # Custom type for fallback str() test
    class CustomType:
        def __str__(self):
            return "custom_value"

    app = FastAPI()

    # Pydantic model instance (not dict)
    product_instance = TestProduct(id=UUID("12345678-1234-5678-1234-567812345678"), name="Widget", price=9.99)

    @app.post("/items")
    def create_item(
        item: TestProduct = Body(
            example={
                "model": product_instance,  # BaseModel instance
                "time": time(14, 30, 0),  # datetime.time
                "tuple": (1, 2, 3),  # tuple
                "frozenset": frozenset([4, 5]),  # frozenset
                "custom": CustomType(),  # Unknown type → str() fallback
            }
        )
    ):
        return {"ok": True}

    schema = app.openapi()
    example = schema["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["example"]

    # Verify edge cases
    assert example["model"]["name"] == "Widget"
    assert example["time"] == "14:30:00"
    assert example["tuple"] == [1, 2, 3]
    assert isinstance(example["frozenset"], list)
    assert set(example["frozenset"]) == {4, 5}
    assert example["custom"] == "custom_value"  # str() fallback

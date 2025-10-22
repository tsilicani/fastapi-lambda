"""Test dependency injection functionality."""

from typing import Annotated

import pytest
from pydantic import BaseModel

from fastapi_lambda.app import FastAPI
from fastapi_lambda.param_functions import Header
from fastapi_lambda.params import Depends
from fastapi_lambda.requests import LambdaRequest
from tests.conftest import parse_response
from tests.utils import make_event


@pytest.mark.asyncio
async def test_simple_dependency():
    """Test simple dependency injection."""
    app = FastAPI()

    async def get_value() -> int:
        return 42

    @app.get("/")
    async def root(value: Annotated[int, Depends(get_value)]):
        return {"value": value}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["value"] == 42


@pytest.mark.asyncio
async def test_dependency_with_yield():
    """Test dependency with yield (cleanup)."""
    app = FastAPI()
    cleanup_called = []

    async def get_db():
        db = {"connected": True}
        try:
            yield db
        finally:
            cleanup_called.append(True)

    @app.get("/")
    async def root(db: Annotated[dict, Depends(get_db)]):
        return {"db_connected": db["connected"]}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["db_connected"] is True
    # Cleanup should have been called
    assert len(cleanup_called) == 1


@pytest.mark.asyncio
async def test_nested_dependencies():
    """Test nested dependencies."""
    app = FastAPI()

    async def get_a() -> int:
        return 10

    async def get_b(a: Annotated[int, Depends(get_a)]) -> int:
        return a + 5

    @app.get("/")
    async def root(b: Annotated[int, Depends(get_b)]):
        return {"result": b}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["result"] == 15


@pytest.mark.asyncio
async def test_request_dependency():
    """Test injecting Request object."""
    app = FastAPI()

    @app.get("/info", response_model=None)  # Disable response_model validation for Request
    async def info(request: LambdaRequest):
        return {"method": request.method, "path": request.path}

    event = make_event(method="GET", path="/info")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["method"] == "GET"
    assert body["path"] == "/info"


@pytest.mark.asyncio
async def test_dependency_caching():
    """Test that dependencies are cached within a request."""
    app = FastAPI()
    call_count = []

    async def get_value() -> int:
        call_count.append(1)
        return len(call_count)

    async def dep1(value: Annotated[int, Depends(get_value)]) -> int:
        return value

    async def dep2(value: Annotated[int, Depends(get_value)]) -> int:
        return value

    @app.get("/")
    async def root(v1: Annotated[int, Depends(dep1)], v2: Annotated[int, Depends(dep2)]):
        return {"v1": v1, "v2": v2}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    # Both should return 1 (dependency called only once and cached)
    assert body["v1"] == 1
    assert body["v2"] == 1
    # Dependency should have been called only once
    assert len(call_count) == 1


@pytest.mark.asyncio
async def test_class_dependency_raises_error():
    """Test that using a class as dependency raises RuntimeError."""
    app = FastAPI()

    class MyClass:
        """A class that is not async callable."""

        def __init__(self):
            self.value = 42

    @app.get("/")
    async def root(obj: Annotated[MyClass, Depends(MyClass)]):
        return {"value": obj.value}

    event = make_event(method="GET", path="/")
    response = await app(event)

    # Should return 500 error because class dependencies are not allowed
    assert response["statusCode"] == 500


@pytest.mark.asyncio
async def test_sync_generator_dependency_raises_error():
    """Test that using a sync generator as dependency raises RuntimeError."""
    app = FastAPI()

    def sync_gen():
        """Sync generator (not allowed)."""
        yield 42

    @app.get("/")
    async def root(value: Annotated[int, Depends(sync_gen)]):
        return {"value": value}

    event = make_event(method="GET", path="/")
    response = await app(event)

    # Should return 500 error because sync generators are not allowed
    assert response["statusCode"] == 500


@pytest.mark.asyncio
async def test_dependency_with_request_injection():
    """Test dependency with LambdaRequest auto-injection."""

    app = FastAPI()

    async def get_path(request: LambdaRequest):
        yield request.path

    @app.get("/test")
    async def root(path: Annotated[str, Depends(get_path)]):
        return {"path": path}

    event = make_event(method="GET", path="/test")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["path"] == "/test"


@pytest.mark.asyncio
async def test_query_and_body_params():
    """Test query and body parameter extraction."""

    app = FastAPI()

    class Item(BaseModel):
        name: str
        price: float

    @app.post("/items")
    async def create_item(item: Item, source: str | None = None):
        return {"item": item.model_dump(), "source": source}

    event = make_event(method="POST", path="/items", body={"name": "Widget", "price": 9.99}, query={"source": "api"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["item"]["name"] == "Widget"
    assert body["source"] == "api"


@pytest.mark.asyncio
async def test_callable_with_dunder_call():
    """Test dependency using callable object with __call__."""
    app = FastAPI()

    class Counter:
        def __init__(self):
            self.count = 0

        async def __call__(self):
            self.count += 1
            return self.count

    counter = Counter()

    @app.get("/count")
    async def get_count(value: Annotated[int, Depends(counter)]):
        return {"count": value}

    event = make_event(method="GET", path="/count")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_no_cache_dependency():
    """Test dependency with use_cache=False."""
    app = FastAPI()
    call_count = []

    async def get_value():
        call_count.append(1)
        return len(call_count)

    @app.get("/")
    async def root(
        v1: Annotated[int, Depends(get_value, use_cache=False)],
        v2: Annotated[int, Depends(get_value, use_cache=False)],
    ):
        return {"v1": v1, "v2": v2}

    event = make_event(method="GET", path="/")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["v1"] == 1
    assert body["v2"] == 2
    assert len(call_count) == 2


@pytest.mark.asyncio
async def test_path_param_with_annotation():
    """Test path parameter with Annotated type."""
    app = FastAPI()

    @app.get("/users/{user_id}")
    async def get_user(user_id: Annotated[int, "User ID"]):
        return {"user_id": user_id}

    event = make_event(method="GET", path="/users/123")
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["user_id"] == 123


@pytest.mark.asyncio
async def test_header_params():
    """Test header parameter extraction."""

    app = FastAPI()

    @app.get("/auth")
    async def check_auth(authorization: str = Header()):
        return {"auth": authorization}

    event = make_event(method="GET", path="/auth", headers={"authorization": "Bearer token123"})
    response = await app(event)

    status, body = parse_response(response)
    assert status == 200
    assert body["auth"] == "Bearer token123"

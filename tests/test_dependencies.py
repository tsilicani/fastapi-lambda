"""Test dependency injection functionality."""

from typing import Annotated

import pytest

from fastapifn.app import FastAPI
from fastapifn.params import Depends
from tests.conftest import parse_response


@pytest.mark.asyncio
async def test_simple_dependency(make_event, lambda_context):
    """Test simple dependency injection."""
    app = FastAPI()

    async def get_value() -> int:
        return 42

    @app.get("/")
    async def root(value: Annotated[int, Depends(get_value)]):
        return {"value": value}

    event = make_event("GET", "/")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["value"] == 42


@pytest.mark.asyncio
async def test_dependency_with_yield(make_event, lambda_context):
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

    event = make_event("GET", "/")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["db_connected"] is True
    # Cleanup should have been called
    assert len(cleanup_called) == 1


@pytest.mark.asyncio
async def test_nested_dependencies(make_event, lambda_context):
    """Test nested dependencies."""
    app = FastAPI()

    async def get_a() -> int:
        return 10

    async def get_b(a: Annotated[int, Depends(get_a)]) -> int:
        return a + 5

    @app.get("/")
    async def root(b: Annotated[int, Depends(get_b)]):
        return {"result": b}

    event = make_event("GET", "/")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["result"] == 15


@pytest.mark.asyncio
async def test_request_dependency(make_event, lambda_context):
    """Test injecting Request object."""
    app = FastAPI()
    from fastapifn.request import LambdaRequest

    @app.get("/info", response_model=None)  # Disable response_model validation for Request
    async def info(request: LambdaRequest):
        return {"method": request.method, "path": request.path}

    event = make_event("GET", "/info")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    assert body["method"] == "GET"
    assert body["path"] == "/info"


@pytest.mark.asyncio
async def test_dependency_caching(make_event, lambda_context):
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

    event = make_event("GET", "/")
    response = await app(event, lambda_context)

    status, body = parse_response(response)
    assert status == 200
    # Both should return 1 (dependency called only once and cached)
    assert body["v1"] == 1
    assert body["v2"] == 1
    # Dependency should have been called only once
    assert len(call_count) == 1

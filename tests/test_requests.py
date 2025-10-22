"""Tests for LambdaRequest - complete coverage with minimal code."""

import base64
from typing import cast

import pytest

from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.types import LambdaEvent
from tests.utils import make_event


@pytest.mark.asyncio
async def test_v1_request():
    """Test API Gateway v1 format."""
    event = make_event("POST", "/api/users", {"name": "test"}, {"q": "search"}, {"x-api-key": "KEY"}, {"id": "123"})
    req = LambdaRequest(event)

    assert req.method == "POST"
    assert req.path == "/api/users"
    assert req.headers == {"x-api-key": "KEY"}
    assert req.query_params == {"q": "search"}
    assert req.path_params == {"id": "123"}
    assert await req.body() == b'{"name": "test"}'
    assert await req.json() == {"name": "test"}


@pytest.mark.asyncio
async def test_v2_format():
    """Test API Gateway v2 format."""
    event: LambdaEvent = cast(
        LambdaEvent,
        {
            "rawPath": "/v2/items",
            "rawQueryString": "filter=active&limit=10",
            "headers": {"Content-Type": "application/json"},
            "requestContext": {
                "http": {"method": "get"},
                "requestId": "v2-req-id",
                "identity": {"sourceIp": "1.2.3.4"},
            },
        },
    )
    req = LambdaRequest(event)

    assert req.method == "GET"
    assert req.path == "/v2/items"
    assert req.query_params == {"filter": "active", "limit": "10"}
    assert req.client.host == "1.2.3.4"
    assert req.client.port == 0


@pytest.mark.asyncio
async def test_empty_query_string():
    """Test empty rawQueryString."""
    event: LambdaEvent = cast(LambdaEvent, {"rawQueryString": "", "requestContext": {"http": {"method": "GET"}}})
    req = LambdaRequest(event)
    assert req.query_params == {}


@pytest.mark.asyncio
async def test_base64_body():
    """Test base64 encoded body."""
    encoded = base64.b64encode(b"binary data").decode()
    event: LambdaEvent = cast(
        LambdaEvent, {"body": encoded, "isBase64Encoded": True, "requestContext": {"http": {"method": "POST"}}}
    )
    req = LambdaRequest(event)

    assert await req.body() == b"binary data"


@pytest.mark.asyncio
async def test_empty_body():
    """Test empty body."""
    event: LambdaEvent = cast(LambdaEvent, {"requestContext": {"http": {"method": "GET"}}})
    req = LambdaRequest(event)

    assert await req.body() == b""
    assert await req.json() is None


@pytest.mark.asyncio
async def test_missing_fields():
    """Test missing optional fields."""
    event: LambdaEvent = cast(LambdaEvent, {})
    req = LambdaRequest(event)

    assert req.method == "GET"
    assert req.path == "/"
    assert req.headers == {}
    assert req.query_params == {}
    assert req.path_params == {}
    assert req.client.host is None


@pytest.mark.asyncio
async def test_body_caching():
    """Test body is cached after first call."""
    event: LambdaEvent = cast(LambdaEvent, {"body": '{"cached": true}', "requestContext": {"http": {"method": "POST"}}})
    req = LambdaRequest(event)

    body1 = await req.body()
    body2 = await req.body()
    assert body1 is body2


@pytest.mark.asyncio
async def test_json_caching():
    """Test JSON is cached after first call."""
    event: LambdaEvent = cast(LambdaEvent, {"body": '{"data": 42}', "requestContext": {"http": {"method": "POST"}}})
    req = LambdaRequest(event)

    json1 = await req.json()
    json2 = await req.json()
    assert json1 is json2


def test_client_tuple_unpacking():
    """Test client can be unpacked as tuple (Starlette compatibility)."""
    req = LambdaRequest(make_event(source_ip="192.168.1.1"))

    # Test tuple unpacking
    host, port = req.client
    assert host == "192.168.1.1"
    assert port == 0

    # Test repr
    assert "192.168.1.1" in repr(req.client)

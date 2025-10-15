"""
Tests for CORS middleware.
"""

import pytest

from fastapi_lambda import FastAPI
from fastapi_lambda.middleware.cors import CORSMiddleware
from fastapi_lambda.types import LambdaEvent


@pytest.fixture
def app_with_cors():
    """FastAPI app with CORS middleware."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.com", "https://test.com"],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["X-Custom-Header"],
        allow_credentials=True,
        expose_headers=["X-Custom-Response"],
        max_age=3600,
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


@pytest.fixture
def app_with_cors_wildcard():
    """FastAPI app with wildcard CORS."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return app


@pytest.mark.asyncio
async def test_cors_simple_request_allowed_origin(app_with_cors):
    """Test CORS headers on simple request with allowed origin."""
    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "origin": "https://example.com",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
    assert response["headers"]["Access-Control-Allow-Credentials"] == "true"
    assert response["headers"]["Access-Control-Expose-Headers"] == "X-Custom-Response"
    assert "Vary" in response["headers"]


@pytest.mark.asyncio
async def test_cors_simple_request_disallowed_origin(app_with_cors):
    """Test CORS headers on simple request with disallowed origin."""
    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "origin": "https://evil.com",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    # Request succeeds but no CORS headers added for disallowed origin
    assert response["statusCode"] == 200
    # Should not have Access-Control-Allow-Origin for disallowed origin
    assert (
        "Access-Control-Allow-Origin" not in response["headers"]
        or response["headers"]["Access-Control-Allow-Origin"] != "https://evil.com"
    )


@pytest.mark.asyncio
async def test_cors_preflight_allowed(app_with_cors):
    """Test CORS preflight request with allowed origin and method."""
    event: LambdaEvent = {
        "httpMethod": "OPTIONS",
        "path": "/test",
        "headers": {
            "origin": "https://example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "X-Custom-Header",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 200
    assert response["body"] == "OK"
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET, POST, PUT"
    assert "X-Custom-Header" in response["headers"]["Access-Control-Allow-Headers"]
    assert response["headers"]["Access-Control-Max-Age"] == "3600"
    assert response["headers"]["Access-Control-Allow-Credentials"] == "true"


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin(app_with_cors):
    """Test CORS preflight request with disallowed origin."""
    event: LambdaEvent = {
        "httpMethod": "OPTIONS",
        "path": "/test",
        "headers": {
            "origin": "https://evil.com",
            "access-control-request-method": "GET",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS origin" in response["body"]


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_method(app_with_cors):
    """Test CORS preflight request with disallowed method."""
    event: LambdaEvent = {
        "httpMethod": "OPTIONS",
        "path": "/test",
        "headers": {
            "origin": "https://example.com",
            "access-control-request-method": "DELETE",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS method" in response["body"]


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_header(app_with_cors):
    """Test CORS preflight request with disallowed header."""
    event: LambdaEvent = {
        "httpMethod": "OPTIONS",
        "path": "/test",
        "headers": {
            "origin": "https://example.com",
            "access-control-request-method": "GET",
            "access-control-request-headers": "X-Evil-Header",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS headers" in response["body"]


@pytest.mark.asyncio
async def test_cors_wildcard_origin(app_with_cors_wildcard):
    """Test CORS with wildcard origin."""
    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "origin": "https://any-origin.com",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors_wildcard(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_cors_wildcard_with_cookies(app_with_cors_wildcard):
    """Test CORS wildcard with cookies - should return specific origin."""
    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "origin": "https://example.com",
            "cookie": "session=abc123",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors_wildcard(event, {})

    assert response["statusCode"] == 200
    # When cookies present, must return specific origin not wildcard
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
    assert "Vary" in response["headers"]


@pytest.mark.asyncio
async def test_cors_no_origin_header(app_with_cors):
    """Test request without origin header - no CORS processing."""
    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {},
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app_with_cors(event, {})

    assert response["statusCode"] == 200
    # No CORS headers should be added
    assert "Access-Control-Allow-Origin" not in response["headers"]


@pytest.mark.asyncio
async def test_cors_regex_origin():
    """Test CORS with regex pattern for allowed origins."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https://.*\.example\.com",
        allow_methods=["GET"],
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    event: LambdaEvent = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {
            "origin": "https://subdomain.example.com",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://subdomain.example.com"

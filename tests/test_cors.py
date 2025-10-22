"""
Tests for CORS middleware.
"""

import pytest

from fastapi_lambda import FastAPI, HTTPException
from fastapi_lambda.middleware.cors import CORSMiddleware
from fastapi_lambda.response import JSONResponse
from tests.utils import make_event


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
    event = make_event("GET", "/test", headers={"origin": "https://example.com"})
    response = await app_with_cors(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
    assert response["headers"]["Access-Control-Allow-Credentials"] == "true"
    assert response["headers"]["Access-Control-Expose-Headers"] == "X-Custom-Response"
    assert "Vary" in response["headers"]


@pytest.mark.asyncio
async def test_cors_simple_request_disallowed_origin(app_with_cors):
    """Test CORS headers on simple request with disallowed origin."""
    event = make_event("GET", "/test", headers={"origin": "https://evil.com"})
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
    event = make_event(
        "OPTIONS",
        "/test",
        headers={
            "origin": "https://example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "X-Custom-Header",
        },
    )
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
    event = make_event(
        "OPTIONS",
        "/test",
        headers={"origin": "https://evil.com", "access-control-request-method": "GET"},
    )
    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS origin" in response["body"]


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_method(app_with_cors):
    """Test CORS preflight request with disallowed method."""
    event = make_event(
        "OPTIONS",
        "/test",
        headers={"origin": "https://example.com", "access-control-request-method": "DELETE"},
    )
    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS method" in response["body"]


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_header(app_with_cors):
    """Test CORS preflight request with disallowed header."""
    event = make_event(
        "OPTIONS",
        "/test",
        headers={
            "origin": "https://example.com",
            "access-control-request-method": "GET",
            "access-control-request-headers": "X-Evil-Header",
        },
    )
    response = await app_with_cors(event, {})

    assert response["statusCode"] == 400
    assert "Disallowed CORS headers" in response["body"]


@pytest.mark.asyncio
async def test_cors_wildcard_origin(app_with_cors_wildcard):
    """Test CORS with wildcard origin."""
    event = make_event("GET", "/test", headers={"origin": "https://any-origin.com"})
    response = await app_with_cors_wildcard(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_cors_wildcard_with_cookies(app_with_cors_wildcard):
    """Test CORS wildcard with cookies - should return specific origin."""
    event = make_event("GET", "/test", headers={"origin": "https://example.com", "cookie": "session=abc123"})
    response = await app_with_cors_wildcard(event, {})

    assert response["statusCode"] == 200
    # When cookies present, must return specific origin not wildcard
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://example.com"
    assert "Vary" in response["headers"]


@pytest.mark.asyncio
async def test_cors_no_origin_header(app_with_cors):
    """Test request without origin header - no CORS processing."""
    event = make_event("GET", "/test")
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

    event = make_event("GET", "/test", headers={"origin": "https://subdomain.example.com"})
    response = await app(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://subdomain.example.com"


@pytest.mark.asyncio
async def test_cors_on_unhandled_exception():
    """Test that CORS headers are present even on unhandled exceptions (500) in debug mode."""
    app = FastAPI(debug=True)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/crash")
    def crash_endpoint():
        raise Exception("Unhandled exception!")

    event = make_event("GET", "/crash", headers={"origin": "https://example.com"})
    response = await app(event, {})

    # Should return 500
    assert response["statusCode"] == 500

    # CRITICAL: CORS headers must be present even on unhandled exceptions
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    # Note: Allow-Methods and Allow-Headers are only added on preflight (OPTIONS) requests


@pytest.mark.asyncio
async def test_cors_on_unhandled_exception_production():
    """Test that CORS headers are present even on unhandled exceptions (500) in production mode."""
    app = FastAPI(debug=False)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/crash")
    def crash_endpoint():
        raise Exception("Unhandled exception!")

    event = make_event("GET", "/crash", headers={"origin": "https://example.com"})
    response = await app(event, {})

    # Should return 500
    assert response["statusCode"] == 500

    # CRITICAL: CORS headers must be present even on unhandled exceptions
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_cors_on_http_exception():
    """Test that CORS headers are present on HTTPException (404)."""

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/not-found")
    def not_found_endpoint():
        raise HTTPException(status_code=404, detail="Not found")

    event = make_event("GET", "/not-found", headers={"origin": "https://example.com"})
    response = await app(event, {})

    # Should return 404
    assert response["statusCode"] == 404

    # CORS headers must be present
    assert "Access-Control-Allow-Origin" in response["headers"]
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.asyncio
async def test_cors_preflight_wildcard_headers():
    """Test CORS preflight with wildcard headers - mirrors request headers."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.com"],
        allow_methods=["POST"],
        allow_headers=["*"],  # Wildcard headers
    )

    @app.post("/test")
    async def test_endpoint():
        return {"message": "test"}

    event = make_event(
        "OPTIONS",
        "/test",
        headers={
            "origin": "https://example.com",
            "access-control-request-method": "POST",
            "access-control-request-headers": "X-Custom-1, X-Custom-2",
        },
    )
    response = await app(event, {})

    assert response["statusCode"] == 200
    # With wildcard headers, should mirror the requested headers
    assert response["headers"]["Access-Control-Allow-Headers"] == "X-Custom-1, X-Custom-2"


@pytest.mark.asyncio
async def test_cors_vary_header_append():
    """Test that Vary header is appended correctly when already present."""

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.com"],
        allow_methods=["GET"],
        allow_credentials=True,
    )

    @app.get("/test")
    async def test_endpoint():
        # Return response with existing Vary header
        return JSONResponse({"message": "test"}, headers={"Vary": "Accept-Encoding"})

    event = make_event("GET", "/test", headers={"origin": "https://example.com"})
    response = await app(event, {})

    assert response["statusCode"] == 200
    # Should have both Accept-Encoding and Origin in Vary header
    vary_header = response["headers"]["Vary"]
    assert "Accept-Encoding" in vary_header
    assert "Origin" in vary_header


@pytest.mark.asyncio
async def test_cors_preflight_wildcard_with_credentials():
    """Test CORS preflight with wildcard origins AND credentials."""
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["POST"],
        allow_credentials=True,  # Forces explicit origin check
    )

    @app.post("/test")
    async def test_endpoint():
        return {"message": "test"}

    event = make_event(
        "OPTIONS",
        "/test",
        headers={"origin": "https://any-origin.com", "access-control-request-method": "POST"},
    )
    response = await app(event, {})

    assert response["statusCode"] == 200
    # With credentials, must return specific origin (not wildcard)
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://any-origin.com"
    assert response["headers"]["Access-Control-Allow-Credentials"] == "true"

"""Test response classes in Lambda context."""

import pytest

from fastapi_lambda import FastAPI
from fastapi_lambda.response import HTMLResponse, PlainTextResponse, RedirectResponse


@pytest.mark.asyncio
async def test_json_response_unicode(make_event, lambda_context):
    """Test JSONResponse preserves Unicode."""
    app = FastAPI()

    @app.get("/unicode")
    async def get_unicode():
        from fastapi_lambda import JSONResponse

        return JSONResponse({"msg": "Hello 世界 🚀"})

    event = make_event("GET", "/unicode")
    response = await app(event, lambda_context)

    assert "世界" in response["body"]
    assert "🚀" in response["body"]


@pytest.mark.asyncio
async def test_html_response(make_event, lambda_context):
    """Test HTMLResponse with FastAPI."""
    app = FastAPI()

    @app.get("/page")
    async def get_page():
        return HTMLResponse("<html><body>Test</body></html>")

    event = make_event("GET", "/page")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/html"
    assert response["body"] == "<html><body>Test</body></html>"


@pytest.mark.asyncio
async def test_plain_text_response(make_event, lambda_context):
    """Test PlainTextResponse with FastAPI."""
    app = FastAPI()

    @app.get("/text")
    async def get_text():
        return PlainTextResponse("Plain text data")

    event = make_event("GET", "/text")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/plain"
    assert response["body"] == "Plain text data"


@pytest.mark.asyncio
async def test_redirect_response(make_event, lambda_context):
    """Test RedirectResponse with FastAPI."""
    app = FastAPI()

    @app.get("/old")
    async def old_endpoint():
        return RedirectResponse("/new", status_code=301)

    event = make_event("GET", "/old")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 301
    assert response["headers"]["Location"] == "/new"
    assert response["body"] == ""


@pytest.mark.asyncio
async def test_redirect_with_custom_headers(make_event, lambda_context):
    """Test RedirectResponse with additional headers."""
    app = FastAPI()

    @app.get("/redirect")
    async def redirect():
        return RedirectResponse("/target", headers={"X-Custom": "value"})

    event = make_event("GET", "/redirect")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 307
    assert response["headers"]["Location"] == "/target"
    assert response["headers"]["X-Custom"] == "value"


@pytest.mark.asyncio
async def test_lambda_response_none_content(make_event, lambda_context):
    """Test LambdaResponse with None content."""
    from fastapi_lambda.response import LambdaResponse

    app = FastAPI()

    @app.get("/empty")
    async def empty():
        return LambdaResponse(None, status_code=204)

    event = make_event("GET", "/empty")
    response = await app(event, lambda_context)

    assert response["statusCode"] == 204
    assert response["body"] == ""


@pytest.mark.asyncio
async def test_lambda_response_bytes_content(make_event, lambda_context):
    """Test LambdaResponse with bytes content."""
    from fastapi_lambda.response import LambdaResponse

    app = FastAPI()

    @app.get("/bytes")
    async def get_bytes():
        return LambdaResponse(b"Binary data")

    event = make_event("GET", "/bytes")
    response = await app(event, lambda_context)

    assert response["body"] == "Binary data"


@pytest.mark.asyncio
async def test_lambda_response_int_content(make_event, lambda_context):
    """Test LambdaResponse with int content."""
    from fastapi_lambda.response import LambdaResponse

    app = FastAPI()

    @app.get("/number")
    async def get_number():
        return LambdaResponse(12345)

    event = make_event("GET", "/number")
    response = await app(event, lambda_context)

    assert response["body"] == "12345"


@pytest.mark.asyncio
async def test_response_media_type_sets_content_type(make_event, lambda_context):
    """Test media_type parameter sets Content-Type header."""
    from fastapi_lambda.response import LambdaResponse

    app = FastAPI()

    @app.get("/xml")
    async def get_xml():
        return LambdaResponse("<xml/>", media_type="application/xml")

    event = make_event("GET", "/xml")
    response = await app(event, lambda_context)

    assert response["headers"]["Content-Type"] == "application/xml"

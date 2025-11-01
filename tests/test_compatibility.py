"""
Test compatibility with FastAPI API.

This ensures that fastapi_lambda can be used as a drop-in replacement for FastAPI.
"""


def test_fastapi_class_import():
    """Test that FastAPI class can be imported."""
    from fastapi_lambda import FastAPI

    assert FastAPI is not None
    app = FastAPI()
    assert app is not None


def test_middleware_import():
    """Test that CORSMiddleware can be imported from fastapi.middleware.cors."""
    from fastapi_lambda.middleware.cors import CORSMiddleware

    assert CORSMiddleware is not None


def test_add_middleware_interface():
    """Test that add_middleware has the same interface as FastAPI."""
    from fastapi_lambda import FastAPI
    from fastapi_lambda.middleware.cors import CORSMiddleware

    app = FastAPI()

    # This should work exactly like FastAPI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://example.com"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        max_age=3600,
    )

    # Verify middleware was added
    assert len(app.user_middleware) == 1


def test_parameter_functions_import():
    """Test that parameter functions can be imported."""
    from fastapi_lambda import Body, Depends, Header, Path, Query

    assert Query is not None
    assert Path is not None
    assert Header is not None
    assert Body is not None
    assert Depends is not None


def test_response_classes_import():
    """Test that response classes can be imported."""
    from fastapi_lambda import (
        HTMLResponse,
        JSONResponse,
        PlainTextResponse,
        RedirectResponse,
    )

    assert JSONResponse is not None
    assert HTMLResponse is not None
    assert PlainTextResponse is not None
    assert RedirectResponse is not None


def test_exception_import():
    """Test that HTTPException can be imported."""
    from fastapi_lambda import HTTPException

    assert HTTPException is not None

    # Test that it can be instantiated
    exc = HTTPException(status_code=404, detail="Not found")
    assert exc.status_code == 404
    assert exc.detail == "Not found"


def test_decorator_methods():
    """Test that decorator methods exist and work."""
    from fastapi_lambda import FastAPI

    app = FastAPI()

    # Test that all decorator methods exist
    assert hasattr(app, "get")
    assert hasattr(app, "post")
    assert hasattr(app, "put")
    assert hasattr(app, "delete")
    assert hasattr(app, "patch")

    # Test that they work
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}

    assert len(app.routes) > 0


def test_fastapi_init_parameters():
    """Test that FastAPI __init__ accepts common parameters."""
    from fastapi_lambda import FastAPI

    # This should work exactly like FastAPI
    app = FastAPI(
        title="Test API",
        description="Test Description",
        version="1.0.0",
        openapi_url="/openapi.json",
        docs_url=None,  # Disabled in fastapi_lambda
        debug=True,
    )

    assert app.title == "Test API"
    assert app.description == "Test Description"
    assert app.version == "1.0.0"
    assert app.openapi_url == "/openapi.json"
    assert app.debug is True


def test_cors_middleware_parameters():
    """Test that CORSMiddleware accepts all standard parameters."""
    from fastapi_lambda.middleware.cors import CORSMiddleware

    # Mock app callable
    async def mock_app(request):
        from fastapi_lambda.response import JSONResponse

        return JSONResponse({"message": "ok"})

    # All these parameters should work
    middleware = CORSMiddleware(
        mock_app,
        allow_origins=["https://example.com"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=True,
        allow_origin_regex=r"https://.*\.example\.com",
        expose_headers=["X-Custom-Header"],
        max_age=3600,
    )

    assert middleware.allow_origins == ["https://example.com"]
    assert "GET" in middleware.allow_methods
    assert middleware.allow_credentials is True
    assert middleware.allow_origin_regex is not None


def test_drop_in_replacement_example():
    """Test a complete example that should work exactly like FastAPI."""
    from fastapi_lambda import Depends, FastAPI, HTTPException
    from fastapi_lambda.middleware.cors import CORSMiddleware

    app = FastAPI(title="Drop-in Test")

    # Add CORS - exactly like FastAPI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Dependency injection - exactly like FastAPI
    def get_token():
        return "token123"

    @app.get("/items")
    def read_items(token: str = Depends(get_token)):
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {"items": []}

    # Verify everything was set up correctly
    assert len(app.routes) > 0
    assert len(app.user_middleware) == 1


def test_import_compatibility():
    """Test that imports work with 'from fastapi_lambda import' syntax."""
    # All these should work without errors
    from fastapi_lambda import (
        Body,
        Depends,
        FastAPI,
        Header,
        HTMLResponse,
        HTTPException,
        JSONResponse,
        Path,
        PlainTextResponse,
        Query,
        RedirectResponse,
    )

    # Verify they're all importable
    assert all(
        [
            FastAPI,
            HTTPException,
            Query,
            Path,
            Header,
            Body,
            Depends,
            JSONResponse,
            HTMLResponse,
            PlainTextResponse,
            RedirectResponse,
        ]
    )


def test_middleware_import_path():
    """Test that middleware can be imported from standard path."""
    # This should work like: from fastapi.middleware.cors import CORSMiddleware
    from fastapi_lambda.middleware.cors import CORSMiddleware

    assert CORSMiddleware is not None

    # Can also import from middleware package
    from fastapi_lambda.middleware import CORSMiddleware as CORS

    assert CORS is CORSMiddleware

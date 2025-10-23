"""
Middleware stack tests.

Verifies FastAPI/Starlette-compatible middleware with pre/post processing and short-circuit behavior.
"""

import time
from typing import Awaitable, Callable, List

import pytest

from fastapi_lambda import FastAPI, status
from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import JSONResponse, Response
from tests.utils import make_event


class LoggingMiddleware:
    """Logs request method/path and response status code."""

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
        logs: List[str],
    ):
        self.app = app
        self.logs = logs

    async def __call__(self, request: LambdaRequest) -> Response:
        self.logs.append(f"{request.method} {request.path}")
        response = await self.app(request)
        self.logs.append(f"{response.status_code}")
        return response


class AuthMiddleware:
    """Validates API key (short-circuits on invalid) and adds user header."""

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
        logs: List[str],
    ):
        self.app = app
        self.logs = logs

    async def __call__(self, request: LambdaRequest) -> Response:
        self.logs.append("Authenticating...")
        api_key = request.headers.get("x-api-key", "")

        if not api_key:
            return JSONResponse({"error": "Missing API key"}, status_code=401)

        if not api_key.startswith("valid-key-"):
            return JSONResponse({"error": "Invalid API key"}, status_code=403)

        user_id = api_key.split("-")[-1]
        response = await self.app(request)
        response.headers["X-Auth-User"] = user_id
        self.logs.append(f"Authenticated user {user_id}")
        return response


@pytest.mark.asyncio
async def test_middleware_happy_path():
    """Test middleware stack with class-based and functional middleware."""
    logs: List[str] = []
    app = FastAPI()

    # Class-based middleware
    app.add_middleware(LoggingMiddleware, logs=logs)
    app.add_middleware(AuthMiddleware, logs=logs)

    # Functional middleware (FastAPI example)
    @app.middleware("http")
    async def add_process_time_header(
        request: LambdaRequest,
        call_next: Callable[[LambdaRequest], Awaitable[Response]],
    ) -> Response:
        logs.append("Starting process time measurement...")
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logs.append("Finished process time measurement")
        return response

    @app.post("/items")
    async def add_item() -> JSONResponse:
        logs.append(f"Added {42}")
        return JSONResponse({"message": "ok"}, status_code=status.HTTP_201_CREATED)

    event = make_event(
        method="POST",
        path="/items",
        headers={"x-api-key": "valid-key-user123"},
    )
    response = await app(event)

    # Verify response
    assert response["statusCode"] == status.HTTP_201_CREATED
    assert response["headers"]["X-Auth-User"] == "user123"
    assert "X-Process-Time" in response["headers"]

    # Verify execution order through logs
    assert logs == [
        "Starting process time measurement...",
        "Authenticating...",
        "POST /items",
        "Added 42",  # Inner handler log
        "201",
        "Authenticated user user123",
        "Finished process time measurement",
    ]

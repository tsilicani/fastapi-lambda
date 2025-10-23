"""
Middleware stack tests.

Verifies FastAPI/Starlette-compatible middleware with pre/post processing and short-circuit behavior.
Uses realistic logging + auth middleware with mock dependencies (logger, database).
"""

import time
from typing import Awaitable, Callable, List

import pytest

from fastapi_lambda import FastAPI, status
from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import JSONResponse, Response
from tests.utils import make_event


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.logs: List[str] = []

    def info(self, message: str) -> None:
        self.logs.append(f"INFO: {message}")

    def error(self, message: str) -> None:
        self.logs.append(f"ERROR: {message}")


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.records: List[int] = []

    def save(self, record: int) -> None:
        self.records.append(record)


class LoggingMiddleware:
    """Logs requests/responses and saves metrics to database."""

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
        logger: MockLogger,
    ):
        self.app = app
        self.logger = logger

    async def __call__(self, request: LambdaRequest) -> Response:
        start_time = time.perf_counter()
        self.logger.info(f"→ {request.method} {request.path}")

        response = await self.app(request)

        duration = time.perf_counter() - start_time
        self.logger.info(f"← {response.status_code} ({duration:.3f}s)")

        return response


class AuthMiddleware:
    """Validates API key (short-circuits on invalid) and adds user header."""

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
    ):
        self.app = app

    async def __call__(self, request: LambdaRequest) -> Response:
        api_key = request.headers.get("x-api-key", "")

        if not api_key:
            return JSONResponse({"error": "Missing API key"}, status_code=401)

        if not api_key.startswith("valid-key-"):
            return JSONResponse({"error": "Invalid API key"}, status_code=403)

        user_id = api_key.split("-")[-1]
        response = await self.app(request)
        response.headers["X-Auth-User"] = user_id

        return response


# TODO: Implement test cases:
# - test_middleware_happy_path()
# - test_middleware_auth_missing_key()
# - test_middleware_auth_invalid_key()
# - test_middleware_execution_order()


@pytest.mark.asyncio
async def test_middleware_happy_path():
    """Test middleware with valid request (happy path)."""
    logger = MockLogger()
    database = MockDatabase()
    app = FastAPI()
    app.add_middleware(LoggingMiddleware, logger=logger)
    app.add_middleware(AuthMiddleware)

    @app.post("/items")
    async def add_item(item: int) -> JSONResponse:
        """Add a number to the database."""
        database.save(item)
        return JSONResponse({"message": f"Item {item} added"}, status_code=status.HTTP_201_CREATED)

    event = make_event(
        method="POST",
        path="/test",
        headers={"origin": "https://any-origin.com", "access-control-request-method": "POST"},
    )
    response = await app(event, {})
    print(response)
    # assert response["statusCode"] == status.HTTP_201_CREATED

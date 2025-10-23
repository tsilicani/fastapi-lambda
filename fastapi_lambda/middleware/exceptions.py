"""
ExceptionMiddleware - Handle known exceptions.

Inspired by: starlette.middleware.exceptions.ExceptionMiddleware
Adapted for: AWS Lambda (no ASGI)
"""

from typing import Awaitable, Callable, Dict, Optional, Type

from fastapi_lambda.exceptions import HTTPException, RequestValidationError
from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import JSONResponse, Response


class ExceptionMiddleware:
    """
    Handle known exceptions (HTTPException, RequestValidationError).

    Converts known exception types to proper HTTP responses.
    Unhandled exceptions bubble up to ServerErrorMiddleware.

    This middleware sits INSIDE user middleware, close to the router.

    Example:
        # Automatically added in build_middleware_stack()
        # Handles HTTPException(404) → JSONResponse(404)
        # Handles RequestValidationError → JSONResponse(422)
    """

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
        handlers: Optional[Dict[Type[Exception], Callable]] = None,
    ):
        """
        Initialize ExceptionMiddleware.

        Args:
            app: Next middleware/router in chain
            handlers: Optional custom exception handlers
        """
        self.app = app
        self._exception_handlers: Dict[Type[Exception], Callable] = {
            HTTPException: self._http_exception_handler,
            RequestValidationError: self._validation_exception_handler,
        }

        # Add custom handlers
        if handlers is not None:
            self._exception_handlers.update(handlers)

    async def __call__(self, request: LambdaRequest) -> Response:
        """
        Execute middleware.

        Catches known exceptions and converts them to HTTP responses.
        """
        try:
            # Call router
            return await self.app(request)

        except Exception as exc:
            # Find handler for this exception type
            handler = self._lookup_exception_handler(exc)

            if handler is None:
                # No handler found, let it bubble up to ServerErrorMiddleware
                raise

            # Handle exception
            return await handler(request, exc)

    def _lookup_exception_handler(self, exc: Exception) -> Optional[Callable]:
        """
        Find handler for exception type.

        Searches exception's MRO (Method Resolution Order) to find handler
        for parent classes if exact match not found.
        """
        for cls in type(exc).__mro__:
            if cls in self._exception_handlers:
                return self._exception_handlers[cls]
        return None

    async def _http_exception_handler(self, request: LambdaRequest, exc: HTTPException) -> Response:
        """
        Handle HTTPException.

        Converts HTTPException to JSONResponse with proper status code.
        """
        headers = getattr(exc, "headers", None)

        # 204 and 304 should not have body
        if exc.status_code in (204, 304):
            return Response(
                content=b"",
                status_code=exc.status_code,
                headers=headers or {},
            )

        return JSONResponse(
            content={"detail": exc.detail},
            status_code=exc.status_code,
            headers=headers,
        )

    async def _validation_exception_handler(
        self, request: LambdaRequest, exc: RequestValidationError
    ) -> Response:
        """
        Handle RequestValidationError.

        Returns 422 Unprocessable Entity with validation error details.
        """
        return JSONResponse(
            content={"detail": exc.errors()},
            status_code=422,
        )

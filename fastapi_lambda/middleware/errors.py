"""
ServerErrorMiddleware - Handle unhandled exceptions.

Inspired by: starlette.middleware.errors.ServerErrorMiddleware
Adapted for: AWS Lambda (no ASGI)
"""

import traceback
from typing import Awaitable, Callable, Optional

from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import JSONResponse, LambdaResponse


class ServerErrorMiddleware:
    """
    Handle unhandled exceptions and return 500 responses.

    This is the outermost middleware layer, catching all exceptions
    that bubble up from user middleware, ExceptionMiddleware, or the router.

    In debug mode, returns detailed error with traceback.
    In production mode, returns generic "Internal Server Error".

    Example:
        app = FastAPI(debug=True)
        # ServerErrorMiddleware automatically added as outermost layer
    """

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[LambdaResponse]],
        handler: Optional[Callable[[LambdaRequest, Exception], Awaitable[LambdaResponse]]] = None,
        debug: bool = False,
    ):
        """
        Initialize ServerErrorMiddleware.

        Args:
            app: Next middleware/router in chain
            handler: Optional custom error handler
            debug: If True, return detailed error with traceback
        """
        self.app = app
        self.handler = handler
        self.debug = debug

    async def __call__(self, request: LambdaRequest) -> LambdaResponse:
        """
        Execute middleware.

        Wraps entire middleware stack in try/except to catch unhandled exceptions.
        """
        try:
            # Call next layer (user middleware → exception → router)
            return await self.app(request)

        except Exception as exc:
            # Custom handler takes precedence
            if self.handler is not None:
                return await self.handler(request, exc)

            # Debug mode: detailed error
            if self.debug:
                return self._debug_response(exc)

            # Production: generic error
            return self._error_response(exc)

    def _debug_response(self, exc: Exception) -> LambdaResponse:
        """Generate detailed error response for debug mode."""
        return JSONResponse(
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "traceback": traceback.format_exc().split("\n"),
            },
            status_code=500,
        )

    def _error_response(self, exc: Exception) -> LambdaResponse:
        """Generate generic error response for production."""
        return JSONResponse(
            content={"detail": "Internal Server Error"},
            status_code=500,
        )

"""
Middleware wrapper for lazy instantiation.

Inspired by: starlette.middleware.Middleware
"""

from typing import Any, Awaitable, Callable, Iterator, Type

from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import Response


class BaseHTTPMiddleware:
    """
    Base class for HTTP middleware using function dispatch pattern.

    Wraps async functions with signature: (request, call_next) -> response
    Matches FastAPI/Starlette BaseHTTPMiddleware behavior (Lambda-native).

    Example:
        @app.middleware("http")
        async def add_header(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Custom"] = "value"
            return response
    """

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[Response]],
        dispatch: Callable[[LambdaRequest, Callable], Awaitable[Response]],
    ):
        self.app = app
        self.dispatch = dispatch

    async def __call__(self, request: LambdaRequest) -> Response:
        """Execute middleware with call_next pattern."""

        async def call_next(req: LambdaRequest) -> Response:
            return await self.app(req)

        return await self.dispatch(request, call_next)


class Middleware:
    """
    Middleware configuration wrapper.

    Stores middleware class, args, and kwargs for lazy instantiation.
    Matches FastAPI/Starlette pattern: (cls, args, kwargs)

    Example:
        middleware_list = [
            Middleware(ServerErrorMiddleware, debug=True),
            Middleware(CORSMiddleware, allow_origins=["*"]),
            Middleware(ExceptionMiddleware, debug=False),
        ]

        # Later, instantiate in reverse order (FastAPI pattern)
        app = router
        for cls, args, kwargs in reversed(middleware_list):
            app = cls(app, *args, **kwargs)
    """

    def __init__(
        self,
        middleware_class: Type,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize Middleware wrapper.

        Args:
            middleware_class: Middleware class to instantiate
            *args: Positional arguments (rarely used, for compatibility)
            **kwargs: Keyword arguments to pass to middleware constructor
        """
        self.cls = middleware_class
        self.args = args
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[Any]:
        """Allow unpacking: cls, args, kwargs = middleware (FastAPI pattern)"""
        return iter([self.cls, self.args, self.kwargs])

    def __repr__(self):
        """String representation for debugging."""
        args_str = ", ".join(repr(arg) for arg in self.args)
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items())
        parts = [self.cls.__name__]
        if args_str:
            parts.append(args_str)
        if kwargs_str:
            parts.append(kwargs_str)
        return f"Middleware({', '.join(parts)})"

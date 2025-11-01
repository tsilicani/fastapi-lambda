"""
Lambda-native FastAPI application.

Replaces fastapi.applications.FastAPI which is ASGI-based.

Original FastAPI implementation: https://github.com/fastapi/fastapi/blob/master/fastapi/applications.py
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
)

from fastapi_lambda.middleware.base import BaseHTTPMiddleware, Middleware
from fastapi_lambda.middleware.errors import ServerErrorMiddleware
from fastapi_lambda.middleware.exceptions import ExceptionMiddleware
from fastapi_lambda.openapi_schema import get_openapi_schema
from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import Response
from fastapi_lambda.router import LambdaRouter
from fastapi_lambda.types import DecoratedCallable, LambdaEvent, RequestHandler
from fastapi_lambda.types import LambdaResponse as LambdaResponseDict


class FastAPI:
    """
    Lambda-native FastAPI application.

    No ASGI - designed specifically for AWS Lambda.
    """

    def __init__(
        self,
        title: str = "FastAPI-Lambda",
        version: str = "0.1.0",
        description: str = "",
        debug: bool = False,
        openapi_url: Optional[str] = "/openapi.json",
        docs_url: Optional[str] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        servers: Optional[List[Dict[str, str]]] = None,
        exception_handlers: Optional[Dict[Any, Callable]] = None,
        middleware: Optional[Sequence[Middleware]] = None,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.debug = debug
        self.openapi_url = openapi_url
        self.docs_url = docs_url
        self.tags = tags
        self.servers = servers
        self.router = LambdaRouter()
        self._openapi_schema: Optional[Dict[str, Any]] = None

        # Exception handlers (FastAPI pattern)
        self.exception_handlers: Dict[Any, Callable] = {}
        if exception_handlers:
            self.exception_handlers.update(exception_handlers)

        # Middleware stack (lazy-built on first request)
        self.user_middleware: List[Middleware] = [] if middleware is None else list(middleware)
        self._middleware_stack: Optional[RequestHandler] = None

        # Register OpenAPI endpoint if enabled
        if self.openapi_url:
            self._register_openapi_route()

    def add_middleware(self, middleware_class: Type, **options: Any) -> None:
        """Add middleware to the stack, placing it as the outermost layer."""

        if self._middleware_stack is not None:  # pragma: no cover
            raise RuntimeError("Cannot add middleware after an application has started")
        self.user_middleware.insert(0, Middleware(middleware_class, **options))

    def middleware(
        self, _middleware_type: Literal["http"] = "http"
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """Decorator to add middleware to the stack, placing it as the outermost layer."""

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_middleware(BaseHTTPMiddleware, dispatch=func)
            return func

        return decorator

    def build_middleware_stack(self) -> RequestHandler:
        """
        Build middleware stack matching FastAPI/Starlette pattern.

        Stack order:
        User Middleware (CORS, logging, auth, etc.)
          → ServerErrorMiddleware (catches 500)
            → ExceptionMiddleware (innermost - handles HTTPException)
              → Router

        Note: User middleware is outermost to ensure CORS headers are added
        even on 500 errors. ServerError catches exceptions and returns response,
        which then flows back through user middleware post-processing.

        Inspired by: fastapi.applications.FastAPI.build_middleware_stack()
        """

        # Separate error handler (500/Exception) from exception handlers
        error_handler = None
        exception_handlers: Dict[Any, Callable] = {}

        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value

        # Build middleware list: user + system + system (FastAPI pattern)
        middleware = (
            self.user_middleware  # List of Middleware objects (outermost)
            + [Middleware(ServerErrorMiddleware, handler=error_handler, debug=self.debug)]
            + [Middleware(ExceptionMiddleware, handlers=exception_handlers)]
        )

        # Start with router as innermost layer
        async def router_handler(request: LambdaRequest) -> Response:
            return await self.router.route(request)

        app: RequestHandler = router_handler

        # Wrap with middleware stack (reverse order - LIFO)
        # FastAPI pattern: for cls, args, kwargs in reversed(middleware)
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)  # type: ignore[misc, call-arg]

        return app

    def get(self, path: str, **kwargs: Any) -> Callable:
        """Register GET endpoint."""
        return self.router.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable:
        """Register POST endpoint."""
        return self.router.post(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable:
        """Register PUT endpoint."""
        return self.router.put(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable:
        """Register DELETE endpoint."""
        return self.router.delete(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Callable:
        """Register PATCH endpoint."""
        return self.router.patch(path, **kwargs)

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str],
        **kwargs: Any,
    ) -> None:
        """Add a route directly."""
        self.router.add_route(path, endpoint, methods, **kwargs)

    def openapi(self) -> Dict[str, Any]:
        "Generate and cache OpenAPI schema."
        if self._openapi_schema is None:
            self._openapi_schema = get_openapi_schema(
                title=self.title,
                version=self.version,
                description=self.description,
                routes=self.router.routes,
                tags=self.tags,
                servers=self.servers,
            )
        return self._openapi_schema

    def _register_openapi_route(self) -> None:
        """Register the OpenAPI schema endpoint."""

        async def openapi_endpoint() -> Dict[str, Any]:
            return self.openapi()

        assert self.openapi_url is not None, "OpenAPI URL must be set"
        self.router.add_route(
            path=self.openapi_url,
            endpoint=openapi_endpoint,
            methods=["GET"],
            include_in_schema=False,
        )

    async def __call__(
        self,
        event: LambdaEvent,
        context: Optional[Dict] = None,
    ) -> LambdaResponseDict:
        """
        Lambda handler entry point.

        This is what gets called directly by AWS Lambda:
            def lambda_handler(event, context):
                return asyncio.run(app(event, context))

        Note: Exception handling is done INSIDE the middleware stack:
        - ServerErrorMiddleware (outermost) catches unhandled exceptions
        - ExceptionMiddleware (innermost) handles HTTPException
        - User middleware can log/trace all requests (success + failure)
        """
        if context is None:
            context = {}

        # Lazy build middleware stack on first request
        if self._middleware_stack is None:
            self._middleware_stack = self.build_middleware_stack()

        # Create request from Lambda event
        request = LambdaRequest(event)

        # Execute middleware chain (includes exception handling)
        response = await self._middleware_stack(request)

        # Convert to Lambda response format
        return response.to_lambda_response()


# Convenience function for Lambda handler
def create_lambda_handler(app: FastAPI) -> Callable:
    """
    Create a Lambda handler function for the app.

    Usage:
        app = FastAPI()

        @app.get("/hello")
        async def hello():
            return {"message": "hello"}

        # Lambda handler
        lambda_handler = create_lambda_handler(app)
    """
    import asyncio

    def lambda_handler(event: LambdaEvent, context: Optional[Any] = None) -> LambdaResponseDict:
        return asyncio.run(app(event, context))

    return lambda_handler

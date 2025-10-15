"""
Lambda-native FastAPI application.

Replaces fastapi.applications.FastAPI which is ASGI-based.
"""

import json
import traceback
from typing import Any, Callable, Dict, List, Optional, Type

from fastapi_lambda.openapi_schema import get_openapi_schema
from fastapi_lambda.request import LambdaRequest
from fastapi_lambda.router import LambdaRouter
from fastapi_lambda.types import LambdaEvent


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
        self._middleware: List[Any] = []

        # Register OpenAPI endpoint if enabled
        if self.openapi_url:
            self._register_openapi_route()

    def add_middleware(self, middleware_class: Type, **options: Any) -> None:
        """
        Add middleware to the application.

        Example:
            from fastapi_lambda.middleware.cors import CORSMiddleware

            app.add_middleware(
                CORSMiddleware,
                allow_origins=["https://example.com"],
                allow_methods=["*"],
                allow_headers=["*"],
            )
        """
        self._middleware.append(middleware_class(**options))

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
        context: Dict,
    ) -> Dict[str, Any]:
        """
        Lambda handler entry point.

        This is what gets called directly by AWS Lambda:
            def lambda_handler(event, context):
                return asyncio.run(app(event, context))
        """
        try:
            # Create request from Lambda event
            request = LambdaRequest(event)

            # Route and execute
            response = await self.router.route(request)

            # Apply middleware (in reverse order, last added first)
            for middleware in reversed(self._middleware):
                if hasattr(middleware, "process_request"):
                    response = middleware.process_request(request, response)

            # Convert to Lambda response format
            return response.to_lambda_response()  # type: ignore[return-value]

        except Exception as exc:
            # Handle errors
            return self._error_response(exc)

    def _error_response(self, exc: Exception) -> Dict[str, Any]:
        """Generate error response for Lambda."""
        from fastapi_lambda.exceptions import HTTPException, RequestValidationError

        # Handle validation errors (422)
        if isinstance(exc, RequestValidationError):
            return {
                "statusCode": 422,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"detail": exc.errors()}),
                "isBase64Encoded": False,
            }

        # Handle HTTP exceptions (custom status codes)
        if isinstance(exc, HTTPException):
            return {
                "statusCode": exc.status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"detail": exc.detail}),
                "isBase64Encoded": False,
            }

        # Handle generic exceptions (500)
        if self.debug:
            # Debug mode: return detailed error with traceback
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "detail": str(exc),
                        "type": type(exc).__name__,
                        "traceback": traceback.format_exc().split("\n"),
                    },
                    indent=2,
                ),
                "isBase64Encoded": False,
            }
        else:
            # Production: return generic error
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"detail": "Internal Server Error"}),
                "isBase64Encoded": False,
            }


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

    def lambda_handler(event: LambdaEvent, context: Any) -> Dict[str, Any]:
        return asyncio.run(app(event, context))

    return lambda_handler

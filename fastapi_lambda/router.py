"""
Lambda-native router.

Replaces Starlette's ASGI-based routing with direct Lambda event handling.
"""

import asyncio
import inspect
import re
from contextlib import AsyncExitStack
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

# Import from lambda_dependencies (not from old ASGI code)
from fastapi_lambda.dependencies import get_dependant, solve_dependencies
from fastapi_lambda.request import LambdaRequest
from fastapi_lambda.response import JSONResponse, LambdaResponse


# Path parameter converters (simplified from Starlette)
class Convertor:
    """Base converter for path parameters."""

    regex: str = ""

    def convert(self, value: str) -> Any:
        raise NotImplementedError()


class StringConvertor(Convertor):
    regex = "[^/]+"

    def convert(self, value: str) -> str:
        return value


class IntConvertor(Convertor):
    regex = "[0-9]+"

    def convert(self, value: str) -> int:
        return int(value)


class PathConvertor(Convertor):
    regex = ".*"

    def convert(self, value: str) -> str:
        return str(value)


CONVERTORS: Dict[str, Convertor] = {
    "str": StringConvertor(),
    "int": IntConvertor(),
    "path": PathConvertor(),
}


# Match parameters in URL paths, eg. '{param}', and '{param:int}'
PARAM_REGEX = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


def compile_path(path: str) -> Tuple[Pattern[str], Dict[str, Convertor]]:
    """
    Compile a path string to regex pattern.

    Example:
        "/users/{user_id:int}" -> (regex, {"user_id": IntConvertor()})
    """
    path_regex = "^"
    path_convertors: Dict[str, Convertor] = {}

    idx = 0
    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str")
        convertor_type = convertor_type.lstrip(":")

        if convertor_type not in CONVERTORS:
            raise ValueError(f"Unknown path convertor '{convertor_type}'")

        convertor = CONVERTORS[convertor_type]

        # Add literal part before parameter
        path_regex += re.escape(path[idx : match.start()])
        # Add parameter regex
        path_regex += f"(?P<{param_name}>{convertor.regex})"

        path_convertors[param_name] = convertor
        idx = match.end()

    # Add remaining literal part
    path_regex += re.escape(path[idx:]) + "$"

    return re.compile(path_regex), path_convertors


class Route:
    """
    A single route mapping path + methods to an endpoint.

    Lambda-native - no ASGI.
    """

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str],
        name: Optional[str] = None,
        include_in_schema: bool = True,
        response_model: Optional[type] = None,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        operation_id: Optional[str] = None,
        responses: Optional[Dict[int, Dict[str, Any]]] = None,
    ):
        self.path = path
        self.endpoint = endpoint
        self.methods = [m.upper() for m in methods]
        self.name = name or endpoint.__name__
        self.include_in_schema = include_in_schema
        self.response_model = response_model
        self.tags = tags
        self.summary = summary
        self.description = description or inspect.getdoc(endpoint)
        self.deprecated = deprecated
        self.operation_id = operation_id
        self.responses = responses

        # Compile path to regex
        self.path_regex, self.path_convertors = compile_path(path)

        # Check if endpoint is async
        self.is_async = inspect.iscoroutinefunction(endpoint)

        # Build dependency graph
        self.dependant = get_dependant(path=path, call=endpoint)

        # Create response field if response_model is provided
        self.response_field: Optional[Any] = None
        if response_model:
            from fastapi_lambda.utils import create_model_field

            self.response_field = create_model_field(
                name=f"Response_{self.name}",
                type_=response_model,
            )

    def matches(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        """
        Check if this route matches the request.

        Returns path parameters if matched, None otherwise.
        """
        if method.upper() not in self.methods:
            return None

        match = self.path_regex.match(path)
        if not match:
            return None

        # Extract and convert path parameters
        path_params: Dict[str, Any] = {}
        for name, value in match.groupdict().items():
            convertor = self.path_convertors[name]
            path_params[name] = convertor.convert(value)

        return path_params

    async def handle(
        self,
        request: LambdaRequest,
        path_params: Dict[str, Any],
    ) -> LambdaResponse:
        """
        Execute the endpoint with dependency injection.
        """
        # Update request with path params
        request._event["pathParameters"] = {k: str(v) for k, v in path_params.items()}

        # Parse body if present
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.json()
            except Exception:
                # Body is not JSON or empty
                pass

        # Solve dependencies
        async with AsyncExitStack() as stack:
            solved = await solve_dependencies(
                request=request,
                dependant=self.dependant,
                body=body,
                async_exit_stack=stack,
            )

            # Check for validation errors
            if solved.errors:
                # Return validation error response
                from fastapi_lambda.exceptions import RequestValidationError

                raise RequestValidationError(errors=solved.errors)

            # Auto-inject LambdaRequest if endpoint needs it
            endpoint_values = solved.values.copy()
            sig = inspect.signature(self.endpoint)
            for param_name, param in sig.parameters.items():
                if param.annotation is LambdaRequest or (
                    hasattr(param.annotation, "__origin__") and param.annotation.__origin__ is LambdaRequest
                ):
                    endpoint_values[param_name] = request

            # Call endpoint with resolved dependencies
            if self.is_async:
                result = await self.endpoint(**endpoint_values)
            else:
                # Run sync function in thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: self.endpoint(**endpoint_values))

        # If result is already a LambdaResponse, return it
        if isinstance(result, LambdaResponse):
            return result

        # Serialize with response_model if provided
        if self.response_field:
            # Validate and serialize using Pydantic model
            from pydantic import TypeAdapter

            response_model = self.response_field.field_info.annotation
            adapter = TypeAdapter(response_model)
            # Validate and serialize (filters extra fields)
            serialized = adapter.dump_python(adapter.validate_python(result), mode="json")
            return JSONResponse(serialized)

        # Otherwise wrap in JSONResponse
        return JSONResponse(result)


class LambdaRouter:
    """
    Lambda-native router.

    Replaces Starlette's Router - no ASGI scope/receive/send.
    """

    def __init__(self):
        self.routes: List[Route] = []

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str],
        name: Optional[str] = None,
        include_in_schema: bool = True,
        response_model: Optional[type] = None,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        deprecated: Optional[bool] = None,
        operation_id: Optional[str] = None,
        responses: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> None:
        """Add a route to the router."""
        route = Route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
            tags=tags,
            summary=summary,
            description=description,
            deprecated=deprecated,
            operation_id=operation_id,
            responses=responses,
        )
        self.routes.append(route)

    def get(self, path: str, **kwargs: Any) -> Callable:
        """Decorator to register a GET route."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, ["GET"], **kwargs)
            return func

        return decorator

    def post(self, path: str, **kwargs: Any) -> Callable:
        """Decorator to register a POST route."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, ["POST"], **kwargs)
            return func

        return decorator

    def put(self, path: str, **kwargs: Any) -> Callable:
        """Decorator to register a PUT route."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, ["PUT"], **kwargs)
            return func

        return decorator

    def delete(self, path: str, **kwargs: Any) -> Callable:
        """Decorator to register a DELETE route."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, ["DELETE"], **kwargs)
            return func

        return decorator

    def patch(self, path: str, **kwargs: Any) -> Callable:
        """Decorator to register a PATCH route."""

        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, ["PATCH"], **kwargs)
            return func

        return decorator

    async def route(self, request: LambdaRequest) -> LambdaResponse:
        """
        Find matching route and execute.

        Returns 404 if no route matches.
        """
        for route in self.routes:
            path_params = route.matches(request.method, request.path)
            if path_params is not None:
                return await route.handle(request, path_params)

        # No route found
        return JSONResponse(
            {"detail": "Not Found"},
            status_code=404,
        )

"""
Lambda-native types for API Gateway events and responses.

Replaces ASGI (scope/receive/send) with direct Lambda event handling.
"""

import types
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Literal,
    Optional,
    Set,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from pydantic import BaseModel

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])
UnionType = getattr(types, "UnionType", Union)
ModelNameMap = Dict[Union[Type[BaseModel], Type[Enum]], str]
IncEx = Union[Set[int], Set[str], Dict[int, Any], Dict[str, Any]]

HttpMethod = Literal[
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "OPTIONS",
    "PATCH",
]
"""HTTP methods supported by API Gateway or Lambda Function URLs."""


class HTTPContext(TypedDict, total=False):
    """HTTP context for API Gateway v2.0 events."""

    method: str
    sourceIp: str


class APIGatewayRequestContext(TypedDict, total=False):
    """API Gateway request context (minimal, only used fields)."""

    identity: Dict[str, Any]  # v1.0: contains sourceIp
    http: HTTPContext  # v2.0: contains method and sourceIp


class LambdaEvent(TypedDict, total=False):
    """
    API Gateway HTTP API (v2.0) or REST API (v1.0) event (minimal, only used fields).

    Supports both v1.0 and v2.0 formats with only fields actually used by the framework.
    """

    # HTTP method and path
    httpMethod: HttpMethod  # v1.0 only
    path: str  # v1.0: path

    # Request data
    headers: Dict[str, str]
    queryStringParameters: Optional[Dict[str, str]]
    pathParameters: Optional[Dict[str, str]]
    body: Optional[str]
    isBase64Encoded: bool

    # Context
    requestContext: APIGatewayRequestContext

    # v2.0 fields
    rawPath: str  # v2.0: raw path
    rawQueryString: str  # v2.0: raw query string


class LambdaResponse(TypedDict):
    """API Gateway response format (compatible with v1.0 and v2.0)."""

    statusCode: int
    headers: Dict[str, str]
    body: str
    isBase64Encoded: bool


if TYPE_CHECKING:
    from fastapi_lambda.requests import LambdaRequest
    from fastapi_lambda.response import Response

RequestHandler = Callable[["LambdaRequest"], Awaitable["Response"]]
"""Async handler that processes a Lambda request and returns a response."""

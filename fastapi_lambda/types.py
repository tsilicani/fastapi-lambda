"""
Lambda-native types for API Gateway events and responses.

Replaces ASGI (scope/receive/send) with direct Lambda event handling.
"""

import types
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
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


class APIGatewayRequestContext(TypedDict, total=False):
    """API Gateway request context."""

    requestId: str
    accountId: str
    stage: str
    requestTime: str
    requestTimeEpoch: int
    identity: Dict[str, Any]
    domainName: str
    apiId: str


class LambdaEvent(TypedDict, total=False):
    """
    API Gateway HTTP API (v2.0) or REST API (v1.0) event.

    Simplified to support both formats.
    """

    # HTTP method and path
    httpMethod: str  # v1.0: "GET", v2.0: uses requestContext.http.method
    path: str
    resource: str  # v1.0 resource path template

    # Request data
    headers: Dict[str, str]
    multiValueHeaders: Dict[str, List[str]]  # v1.0 only
    queryStringParameters: Optional[Dict[str, str]]
    multiValueQueryStringParameters: Optional[Dict[str, List[str]]]  # v1.0 only
    pathParameters: Optional[Dict[str, str]]
    body: Optional[str]
    isBase64Encoded: bool

    # Context
    requestContext: APIGatewayRequestContext

    # v2.0 fields
    version: str  # "2.0" for HTTP API
    rawPath: str  # v2.0: raw path
    rawQueryString: str  # v2.0: raw query string


class LambdaResponse(TypedDict, total=False):
    "API Gateway response format (compatible with v1.0 and v2.0)."

    statusCode: int
    headers: Dict[str, str]
    multiValueHeaders: Dict[str, List[str]]  # v1.0 only
    body: str
    isBase64Encoded: bool

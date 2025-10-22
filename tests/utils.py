"""Test utilities and helper functions."""

import json
from typing import Any, Dict, Optional

from fastapi_lambda.types import HttpMethod, LambdaEvent


def make_event(
    method: HttpMethod = "GET",
    path: str = "/",
    body: Any = None,
    query: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    path_params: Optional[Dict[str, str]] = None,
    source_ip: Optional[str] = None,
) -> LambdaEvent:
    """Create API Gateway v1 Lambda event (minimal required fields only)."""
    return {
        "httpMethod": method,
        "path": path,
        "headers": headers or {},
        "queryStringParameters": query,
        "pathParameters": path_params,
        "body": json.dumps(body) if body else None,
        "isBase64Encoded": False,
        "requestContext": {
            "identity": {"sourceIp": source_ip} if source_ip else {},
            "http": {},
        },
    }

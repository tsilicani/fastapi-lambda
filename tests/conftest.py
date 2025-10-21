"""Pytest configuration and shared fixtures."""

import json
from typing import Any, Dict, Optional, Tuple

import pytest


def parse_response(response: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Parse Lambda response into status code and body dict."""
    status_code = response["statusCode"]
    body = json.loads(response["body"]) if response.get("body") else {}
    return status_code, body


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""

    class MockContext:
        request_id = "test-request-id"
        function_name = "test-function"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
        aws_request_id = "test-request-id"

    return MockContext()


@pytest.fixture
def make_event():
    """Factory per creare Lambda events."""

    def _make(
        method: str = "GET",
        path: str = "/",
        body: Any = None,
        query: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        path_params: Optional[Dict[str, str]] = None,
    ):
        event = {
            "httpMethod": method,
            "path": path,
            "headers": headers or {},
            "queryStringParameters": query,
            "pathParameters": path_params,
            "body": json.dumps(body) if body else None,
            "isBase64Encoded": False,
            "requestContext": {
                "requestId": "test-request-id",
                "accountId": "123456789012",
                "stage": "test",
            },
        }
        return event

    return _make

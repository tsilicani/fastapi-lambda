"""Pytest configuration and shared fixtures."""

import json
from typing import Any, Dict, Tuple

import pytest

from tests.utils import make_event as _make_event


def parse_response(response: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Parse Lambda response into status code and body dict."""
    status_code = response["statusCode"]
    body = json.loads(response["body"]) if response.get("body") else {}
    return status_code, body


@pytest.fixture
def make_event():
    """Factory for API Gateway v1 Lambda events (minimal required fields only)."""
    return _make_event

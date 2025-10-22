"""Pytest configuration and shared fixtures."""

import json
from typing import Any, Dict, Tuple


def parse_response(response: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Parse Lambda response into status code and body dict."""
    status_code = response["statusCode"]
    body = json.loads(response["body"]) if response.get("body") else {}
    return status_code, body

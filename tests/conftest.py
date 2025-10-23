"""Pytest configuration and shared fixtures."""

import json
from typing import Any, Dict, Tuple, Union

from fastapi_lambda.types import LambdaResponse


def parse_response(response: Union[Dict[str, Any], LambdaResponse]) -> Tuple[int, Dict[str, Any]]:
    """Parse Lambda response into status code and body dict."""
    status_code = response["statusCode"]
    body = json.loads(response["body"]) if response.get("body") else {}
    return status_code, body

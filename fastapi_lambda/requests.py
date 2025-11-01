"""
Lambda-native Request class.

Replaces starlette.requests.Request which depends on ASGI scope/receive/send.
Original: https://github.com/encode/starlette/blob/master/starlette/requests.py
"""

import json
from typing import Any, Dict, Optional
from urllib.parse import parse_qs

from fastapi_lambda.datastructures import Address
from fastapi_lambda.types import LambdaEvent


class LambdaRequest:
    """
    Request object built directly from API Gateway Lambda event.

    No ASGI scope/receive/send - Lambda-native.
    """

    def __init__(self, event: LambdaEvent):
        self._event = event
        self._body: Optional[bytes] = None
        self._json: Any = None
        self._client: Optional[Address] = None

    @property
    def method(self) -> str:
        """HTTP method"""
        # Case v1
        if "httpMethod" in self._event:
            return self._event["httpMethod"].upper()
        # Case v2 and Lambda URL
        return self._event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()

    @property
    def path(self) -> str:
        """Request path."""
        # V2 and Lambda URL use rawPath, v1 uses path
        return self._event.get("rawPath") or self._event.get("path", "/")

    @property
    def headers(self) -> Dict[str, str]:
        """Request headers (case-insensitive)."""
        headers = self._event.get("headers") or {}
        # Lowercase all header names for case-insensitive access
        return {k.lower(): v for k, v in headers.items()}

    @property
    def query_params(self) -> Dict[str, str]:
        """
        Query string parameters (single value).

        For multi-value, API Gateway gives us both formats.
        """
        # Case rawQueryString present (v2 and Lambda URL)
        if "rawQueryString" in self._event:
            raw = self._event["rawQueryString"]
            if not raw:
                return {}
            parsed = parse_qs(raw, keep_blank_values=True)
            # Return first value for each key
            return {k: v[0] if v else "" for k, v in parsed.items()}
        # Case v1
        return self._event.get("queryStringParameters") or {}

    @property
    def path_params(self) -> Dict[str, str]:
        """Path parameters from route matching."""
        return self._event.get("pathParameters") or {}

    @property
    def client(self) -> Address:
        """Client address (host and port) - compatible with Starlette."""
        if self._client is None:
            ctx = self._event.get("requestContext", {})
            # Try v2/Lambda URL (http.sourceIp) or v1 (identity.sourceIp)
            source_ip = ctx.get("http", {}).get("sourceIp") or ctx.get("identity", {}).get("sourceIp")
            self._client = Address(source_ip, 0)
        return self._client

    async def body(self) -> bytes:
        """Request body as bytes."""
        if self._body is None:
            body_str = self._event.get("body") or ""
            if self._event.get("isBase64Encoded", False):
                import base64

                self._body = base64.b64decode(body_str)
            else:
                self._body = body_str.encode("utf-8")
        return self._body

    async def json(self) -> Any:
        """Parse request body as JSON."""
        if self._json is None:
            body = await self.body()
            if body:
                self._json = json.loads(body)
            else:
                self._json = None
        return self._json

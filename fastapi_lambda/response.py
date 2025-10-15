"""
Lambda-native Response class.

Replaces starlette.responses.Response which uses ASGI __call__(scope, receive, send).
"""

import json
from typing import Any, Dict, Optional

from fastapi_lambda.types import LambdaResponse as LambdaResponseDict


class LambdaResponse:
    """
    Response object that converts to API Gateway Lambda response format.

    No ASGI - returns dict directly for Lambda.
    """

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ):
        self.status_code = status_code
        self.media_type = media_type
        self.headers = headers or {}
        self._body = self._render(content)

        # Set content-type if not already set
        if media_type and "content-type" not in {k.lower() for k in self.headers.keys()}:
            self.headers["Content-Type"] = media_type

    def _render(self, content: Any) -> str:
        """Render content to string."""
        if content is None:
            return ""
        if isinstance(content, bytes):
            return content.decode("utf-8")
        if isinstance(content, str):
            return content
        # Default: convert to string
        return str(content)

    def to_lambda_response(self) -> LambdaResponseDict:
        """Convert to API Gateway Lambda response format."""
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": self._body,
            "isBase64Encoded": False,
        }


class JSONResponse(LambdaResponse):
    """JSON response."""

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="application/json",
        )

    def _render(self, content: Any) -> str:
        """Render content as JSON."""
        return json.dumps(content, ensure_ascii=False, indent=None, separators=(",", ":"))


class HTMLResponse(LambdaResponse):
    """HTML response."""

    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html",
        )


class PlainTextResponse(LambdaResponse):
    """Plain text response."""

    def __init__(
        self,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
        )


class RedirectResponse(LambdaResponse):
    """Redirect response."""

    def __init__(
        self,
        url: str,
        status_code: int = 307,
        headers: Optional[Dict[str, str]] = None,
    ):
        headers = headers or {}
        headers["Location"] = url
        super().__init__(
            content="",
            status_code=status_code,
            headers=headers,
        )

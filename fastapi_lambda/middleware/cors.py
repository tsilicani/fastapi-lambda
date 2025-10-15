"""
Lambda-native CORS middleware.

Adapted from Starlette's CORS middleware for Lambda event handling.
No ASGI - works directly with LambdaRequest/LambdaResponse.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from fastapi_lambda.request import LambdaRequest
from fastapi_lambda.response import LambdaResponse, PlainTextResponse

ALL_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
SAFELISTED_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}


class CORSMiddleware:
    """
    CORS middleware for Lambda functions.

    Handles CORS preflight requests and adds CORS headers to responses.

    Example:
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    """

    def __init__(
        self,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        allow_all_origins = "*" in allow_origins
        allow_all_headers = "*" in allow_headers
        preflight_explicit_allow_origin = not allow_all_origins or allow_credentials

        # Pre-compute headers for simple requests
        simple_headers = {}
        if allow_all_origins:
            simple_headers["Access-Control-Allow-Origin"] = "*"
        if allow_credentials:
            simple_headers["Access-Control-Allow-Credentials"] = "true"
        if expose_headers:
            simple_headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)

        # Pre-compute headers for preflight requests
        preflight_headers = {}
        if preflight_explicit_allow_origin:
            # Origin value set in preflight_response() if allowed
            preflight_headers["Vary"] = "Origin"
        else:
            preflight_headers["Access-Control-Allow-Origin"] = "*"
        preflight_headers.update(
            {
                "Access-Control-Allow-Methods": ", ".join(allow_methods),
                "Access-Control-Max-Age": str(max_age),
            }
        )
        allow_headers_list = sorted(SAFELISTED_HEADERS | set(allow_headers))
        if allow_headers_list and not allow_all_headers:
            preflight_headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers_list)
        if allow_credentials:
            preflight_headers["Access-Control-Allow-Credentials"] = "true"

        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = [h.lower() for h in allow_headers_list]
        self.allow_all_origins = allow_all_origins
        self.allow_all_headers = allow_all_headers
        self.preflight_explicit_allow_origin = preflight_explicit_allow_origin
        self.allow_origin_regex = compiled_allow_origin_regex
        self.allow_credentials = allow_credentials
        self.simple_headers = simple_headers
        self.preflight_headers = preflight_headers

    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if self.allow_all_origins:
            return True

        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(origin):
            return True

        return origin in self.allow_origins

    def process_request(self, request: LambdaRequest, response: LambdaResponse) -> LambdaResponse:
        """
        Add CORS headers to response based on request.

        Called by the app after routing but before returning response.
        """
        origin = request.headers.get("origin")

        # No origin header - no CORS processing needed
        if not origin:
            return response

        # Handle preflight request
        if request.method == "OPTIONS" and "access-control-request-method" in request.headers:
            return self._handle_preflight(request)

        # Handle simple request - add CORS headers
        self._add_cors_headers(response, origin, request.headers.get("cookie") is not None)
        return response

    def _handle_preflight(self, request: LambdaRequest) -> LambdaResponse:
        """Handle CORS preflight OPTIONS request."""
        requested_origin = request.headers.get("origin", "")
        requested_method = request.headers.get("access-control-request-method", "")
        requested_headers = request.headers.get("access-control-request-headers")

        headers = dict(self.preflight_headers)
        failures = []

        # Check origin
        if self.is_allowed_origin(origin=requested_origin):
            if self.preflight_explicit_allow_origin:
                headers["Access-Control-Allow-Origin"] = requested_origin
        else:
            failures.append("origin")

        # Check method
        if requested_method not in self.allow_methods:
            failures.append("method")

        # Check headers
        if self.allow_all_headers and requested_headers is not None:
            headers["Access-Control-Allow-Headers"] = requested_headers
        elif requested_headers is not None:
            for header in [h.lower().strip() for h in requested_headers.split(",")]:
                if header and header not in self.allow_headers:
                    failures.append("headers")
                    break

        # Return error or success
        if failures:
            failure_text = "Disallowed CORS " + ", ".join(failures)
            return PlainTextResponse(failure_text, status_code=400, headers=headers)

        return PlainTextResponse("OK", status_code=200, headers=headers)

    def _add_cors_headers(self, response: LambdaResponse, origin: str, has_cookie: bool) -> None:
        """Add CORS headers to a simple (non-preflight) response."""
        # Add pre-computed simple headers
        response.headers.update(self.simple_headers)

        # Handle explicit origin cases
        if self.allow_all_origins and has_cookie:
            # If request includes cookies, must respond with specific origin
            response.headers["Access-Control-Allow-Origin"] = origin
            self._add_vary_header(response, "Origin")
        elif not self.allow_all_origins and self.is_allowed_origin(origin=origin):
            # Mirror back the origin for specific allowed origins
            response.headers["Access-Control-Allow-Origin"] = origin
            self._add_vary_header(response, "Origin")

    @staticmethod
    def _add_vary_header(response: LambdaResponse, value: str) -> None:
        """Add or append to Vary header."""
        existing = response.headers.get("Vary", "")
        if existing:
            values = [v.strip() for v in existing.split(",")]
            if value not in values:
                values.append(value)
                response.headers["Vary"] = ", ".join(values)
        else:
            response.headers["Vary"] = value

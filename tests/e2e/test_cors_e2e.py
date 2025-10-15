"""
E2E tests for CORS middleware functionality.

Tests CORS behavior across all deployment types:
- Lambda Function URL
- API Gateway v1 (REST API)
- API Gateway v2 (HTTP API)
"""

import pytest
import requests


def test_cors_simple_request_allowed_origin(api_base_url: str) -> None:
    """Test CORS headers on simple request with allowed origin."""
    response = requests.get(
        f"{api_base_url}/health",
        headers={"Origin": "https://example.com"},
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    assert response.headers.get("Access-Control-Expose-Headers") == "X-Request-ID"
    assert "Vary" in response.headers


def test_cors_simple_request_disallowed_origin(api_base_url: str) -> None:
    """Test CORS headers on simple request with disallowed origin."""
    response = requests.get(
        f"{api_base_url}/health",
        headers={"Origin": "https://evil.com"},
    )

    # Request succeeds but no CORS headers for disallowed origin
    assert response.status_code == 200
    # Should not have Access-Control-Allow-Origin for disallowed origin
    cors_origin = response.headers.get("Access-Control-Allow-Origin")
    assert cors_origin != "https://evil.com"


def test_cors_preflight_request_allowed(api_base_url: str) -> None:
    """Test CORS preflight OPTIONS request with allowed origin and method."""
    response = requests.options(
        f"{api_base_url}/items",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert "POST" in response.headers.get("Access-Control-Allow-Methods", "")
    assert "Content-Type" in response.headers.get("Access-Control-Allow-Headers", "")
    assert "Authorization" in response.headers.get("Access-Control-Allow-Headers", "")
    assert response.headers.get("Access-Control-Max-Age") == "3600"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_preflight_request_disallowed_origin(api_base_url: str) -> None:
    """Test CORS preflight request with disallowed origin."""
    response = requests.options(
        f"{api_base_url}/items",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    # Should return 400 for disallowed origin
    assert response.status_code == 400
    assert "Disallowed CORS origin" in response.text


def test_cors_preflight_request_disallowed_method(api_base_url: str) -> None:
    """Test CORS preflight request with disallowed method."""
    response = requests.options(
        f"{api_base_url}/items",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "PATCH",  # Not in allowed methods
        },
    )

    # Should return 400 for disallowed method
    assert response.status_code == 400
    assert "Disallowed CORS method" in response.text


def test_cors_preflight_request_disallowed_header(api_base_url: str) -> None:
    """Test CORS preflight request with disallowed header."""
    response = requests.options(
        f"{api_base_url}/items",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Evil-Header",
        },
    )

    # Should return 400 for disallowed header
    assert response.status_code == 400
    assert "Disallowed CORS headers" in response.text


def test_cors_post_request_with_origin(api_base_url: str) -> None:
    """Test CORS headers on POST request with allowed origin."""
    response = requests.post(
        f"{api_base_url}/items",
        json={"name": "Test Item", "price": 19.99},
        headers={
            "Origin": "https://example.com",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    assert response.headers.get("Access-Control-Expose-Headers") == "X-Request-ID"


def test_cors_get_request_without_origin(api_base_url: str) -> None:
    """Test that requests without Origin header work normally."""
    response = requests.get(f"{api_base_url}/health")

    assert response.status_code == 200
    # No CORS headers should be added without Origin
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_multiple_allowed_origins(api_base_url: str) -> None:
    """Test that multiple allowed origins work correctly."""
    # First origin
    response1 = requests.get(
        f"{api_base_url}/health",
        headers={"Origin": "https://example.com"},
    )
    assert response1.status_code == 200
    assert response1.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    # Second origin
    response2 = requests.get(
        f"{api_base_url}/health",
        headers={"Origin": "https://test.example.com"},
    )
    assert response2.status_code == 200
    assert response2.headers.get("Access-Control-Allow-Origin") == "https://test.example.com"


def test_cors_with_custom_header(api_base_url: str) -> None:
    """Test CORS with custom header in actual request."""
    # First do preflight
    preflight = requests.options(
        f"{api_base_url}/items",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Custom-Header",
        },
    )

    assert preflight.status_code == 200
    assert "X-Custom-Header" in preflight.headers.get("Access-Control-Allow-Headers", "")

    # Then actual request with custom header
    response = requests.get(
        f"{api_base_url}/items/1",
        headers={
            "Origin": "https://example.com",
            "X-Custom-Header": "test-value",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/health"),
        ("GET", "/items/1"),
        ("POST", "/items"),
    ],
)
def test_cors_on_different_endpoints(api_base_url: str, method: str, path: str) -> None:
    """Test that CORS works on all endpoints."""
    headers = {"Origin": "https://example.com"}

    if method == "POST":
        response = requests.post(
            f"{api_base_url}{path}",
            json={"name": "Test", "price": 9.99},
            headers={**headers, "Content-Type": "application/json"},
        )
    else:
        response = requests.request(method, f"{api_base_url}{path}", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"

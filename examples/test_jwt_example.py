"""
Test the JWT authentication example to ensure it works correctly.

This is a simple test to verify the example is functional.
"""

import sys
from pathlib import Path

# Add parent directory to path to import the example
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.jwt_auth import app  # noqa: E402


def make_event(method: str, path: str, headers: dict = None, query: dict = None) -> dict:
    """Create a mock Lambda event."""
    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers or {},
        "queryStringParameters": query,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-request-id",
            "accountId": "123456789012",
            "stage": "test",
        },
    }
    return event


class MockContext:
    """Mock Lambda context."""

    request_id = "test-request-id"
    function_name = "test-function"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"


async def test_public_endpoint():
    """Test public endpoint works without authentication."""
    event = make_event("GET", "/")
    context = MockContext()

    response = await app(event, context)

    assert response["statusCode"] == 200
    print("✓ Public endpoint works")


async def test_login():
    """Test login endpoint returns token."""
    event = make_event(
        "POST",
        "/login",
        query={"username": "alice", "password": "password123"},
    )
    context = MockContext()

    response = await app(event, context)

    assert response["statusCode"] == 200
    print("✓ Login works")

    import json

    body = json.loads(response["body"])
    assert "access_token" in body
    assert body["token_type"] == "bearer"

    return body["access_token"]


async def test_protected_endpoint_with_token(token: str):
    """Test protected endpoint with valid token."""
    event = make_event(
        "GET",
        "/me",
        headers={"authorization": f"Bearer {token}"},
    )
    context = MockContext()

    response = await app(event, context)

    assert response["statusCode"] == 200
    print("✓ Protected endpoint works with token")

    import json

    body = json.loads(response["body"])
    assert body["user"]["username"] == "alice"


async def test_protected_endpoint_without_token():
    """Test protected endpoint fails without token."""
    event = make_event("GET", "/me")
    context = MockContext()

    response = await app(event, context)

    assert response["statusCode"] == 403
    print("✓ Protected endpoint rejects requests without token")


async def test_admin_endpoint_with_admin(token: str):
    """Test admin endpoint works with admin user."""
    event = make_event(
        "GET",
        "/admin",
        headers={"authorization": f"Bearer {token}"},
    )
    context = MockContext()

    response = await app(event, context)

    assert response["statusCode"] == 200
    print("✓ Admin endpoint works for admin user")


async def test_admin_endpoint_with_non_admin():
    """Test admin endpoint rejects non-admin user."""
    # Login as bob (non-admin)
    event = make_event(
        "POST",
        "/login",
        query={"username": "bob", "password": "password123"},
    )
    context = MockContext()

    response = await app(event, context)
    import json

    bob_token = json.loads(response["body"])["access_token"]

    # Try to access admin endpoint
    event = make_event(
        "GET",
        "/admin",
        headers={"authorization": f"Bearer {bob_token}"},
    )

    response = await app(event, context)

    assert response["statusCode"] == 403
    print("✓ Admin endpoint rejects non-admin user")


async def test_optional_auth():
    """Test optional authentication endpoint."""
    context = MockContext()

    # Without token
    event = make_event("GET", "/public-or-protected")
    response = await app(event, context)

    assert response["statusCode"] == 200
    import json

    body = json.loads(response["body"])
    assert body["authenticated"] is False
    print("✓ Optional auth works without token")

    # With token
    login_event = make_event(
        "POST",
        "/login",
        query={"username": "alice", "password": "password123"},
    )
    login_response = await app(login_event, context)
    token = json.loads(login_response["body"])["access_token"]

    event = make_event(
        "GET",
        "/public-or-protected",
        headers={"authorization": f"Bearer {token}"},
    )
    response = await app(event, context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["authenticated"] is True
    print("✓ Optional auth works with token")


async def run_all_tests():
    """Run all tests."""
    print("\n🧪 Testing JWT Authentication Example\n")

    await test_public_endpoint()
    token = await test_login()
    await test_protected_endpoint_with_token(token)
    await test_protected_endpoint_without_token()
    await test_admin_endpoint_with_admin(token)
    await test_admin_endpoint_with_non_admin()
    await test_optional_auth()

    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_all_tests())

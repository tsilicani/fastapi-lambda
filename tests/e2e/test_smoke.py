"""E2E tests using SAM Local."""

import requests


def test_root_endpoint(api_base_url: str) -> None:
    """Test root endpoint returns expected message."""
    response = requests.get(f"{api_base_url}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPIFn"}


def test_health_endpoint(api_base_url: str) -> None:
    """Test health check endpoint."""
    response = requests.get(f"{api_base_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_item(api_base_url: str) -> None:
    """Test GET /items/{item_id}."""
    response = requests.get(f"{api_base_url}/items/5")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == 5
    assert data["name"] == "Item 5"
    assert data["price"] == 49.95


def test_create_item(api_base_url: str) -> None:
    """Test POST /items."""
    payload = {
        "name": "Test Item",
        "price": 29.99,
        "description": "A test item",
    }

    response = requests.post(
        f"{api_base_url}/items",
        json=payload,
    )

    # Note: FastAPIFn returns 200 by default, not 201
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == 42
    assert data["name"] == "Test Item"
    assert data["price"] == 29.99


def test_openapi_schema(api_base_url: str) -> None:
    """Test OpenAPI schema endpoint."""
    response = requests.get(f"{api_base_url}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["title"] == "E2E Test API"
    assert schema["info"]["version"] == "1.0.0"

    # Check paths
    assert "/items/{item_id}" in schema["paths"]
    assert "/items" in schema["paths"]
    assert "/" in schema["paths"]
    assert "/health" in schema["paths"]

    # Check methods
    assert "get" in schema["paths"]["/items/{item_id}"]
    assert "post" in schema["paths"]["/items"]


def test_validation_error(api_base_url: str) -> None:
    """Test request validation error."""
    payload = {
        "name": "Invalid Item",
        # Missing required 'price' field
    }

    response = requests.post(
        f"{api_base_url}/items",
        json=payload,
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_path_not_found(api_base_url: str) -> None:
    """Test 404 for unknown path."""
    response = requests.get(f"{api_base_url}/nonexistent")
    assert response.status_code == 404

"""Example: Tests specific to certain deployment types."""

import requests


def test_lambda_url_specific_behavior(lambda_url: str) -> None:
    """Test behavior specific to Lambda Function URL.

    This test only runs against Lambda URL deployment.
    Use this pattern when testing deployment-specific features.
    """
    response = requests.get(f"{lambda_url}/health")
    assert response.status_code == 200
    # Lambda URL specific assertions here...


def test_api_gateway_v1_specific(api_gateway_v1_url: str) -> None:
    """Test behavior specific to API Gateway v1 (REST).

    This test only runs against API Gateway v1.
    """
    response = requests.get(f"{api_gateway_v1_url}/health")
    assert response.status_code == 200
    # API Gateway v1 specific assertions here...


def test_api_gateway_v2_specific(api_gateway_v2_url: str) -> None:
    """Test behavior specific to API Gateway v2 (HTTP).

    This test only runs against API Gateway v2.
    """
    response = requests.get(f"{api_gateway_v2_url}/health")
    assert response.status_code == 200
    # API Gateway v2 specific assertions here...

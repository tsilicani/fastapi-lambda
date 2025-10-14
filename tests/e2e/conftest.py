"""Pytest configuration and fixtures for E2E tests with Serverless Framework."""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def stack_outputs() -> dict[str, str]:
    """Load stack outputs from serverless deployment."""
    output_file = Path(__file__).parent / "stack-output.json"
    with open(output_file) as f:
        return json.load(f)


@pytest.fixture(
    scope="session",
    params=[
        "lambda_url",
        "api_gateway_v1",
        "api_gateway_v2",
    ],
    ids=[
        "Lambda URL",
        "API Gateway v1 (REST)",
        "API Gateway v2 (HTTP)",
    ],
)
def api_base_url(request, stack_outputs: dict[str, str]) -> str:
    """Base URL for each deployment type.

    This fixture is parametrized to run tests against all 3 deployment methods:
    - Lambda Function URL (direct invocation)
    - API Gateway v1 (REST API)
    - API Gateway v2 (HTTP API)
    """
    deployment_type = request.param

    url_mapping = {
        "lambda_url": stack_outputs["UrlLambdaFunctionUrl"],
        "api_gateway_v1": stack_outputs["ServiceEndpoint"],
        "api_gateway_v2": stack_outputs["HttpApiUrl"],
    }

    return url_mapping[deployment_type].rstrip("/")


@pytest.fixture(scope="session")
def lambda_url(stack_outputs: dict[str, str]) -> str:
    """Lambda Function URL - for tests that need a specific deployment type."""
    return stack_outputs["UrlLambdaFunctionUrl"].rstrip("/")


@pytest.fixture(scope="session")
def api_gateway_v1_url(stack_outputs: dict[str, str]) -> str:
    """API Gateway v1 (REST) URL - for tests that need a specific deployment type."""
    return stack_outputs["ServiceEndpoint"].rstrip("/")


@pytest.fixture(scope="session")
def api_gateway_v2_url(stack_outputs: dict[str, str]) -> str:
    """API Gateway v2 (HTTP) URL - for tests that need a specific deployment type."""
    return stack_outputs["HttpApiUrl"].rstrip("/")

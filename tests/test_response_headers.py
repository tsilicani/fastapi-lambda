"""Test custom response headers."""

from typing import Any

import pytest

from fastapi_lambda import FastAPI, JSONResponse


@pytest.mark.asyncio
async def test_custom_headers_with_jsonresponse():
    """Test setting custom headers using JSONResponse."""
    app = FastAPI()

    @app.get("/items")
    def get_items():
        return JSONResponse(
            content={"items": [1, 2, 3]},
            headers={"Cache-Control": "max-age=3600, public", "X-Custom-Header": "custom-value"},
        )

    event: Any = {
        "httpMethod": "GET",
        "path": "/items",
        "headers": {},
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": "test-123",
            "accountId": "123456789012",
            "stage": "prod",
            "requestTime": "09/Apr/2015:12:34:56 +0000",
            "requestTimeEpoch": 1428582896000,
            "identity": {},
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "apiId": "abc123",
        },
    }

    response = await app(event, {})

    assert response["statusCode"] == 200
    assert response["headers"]["Cache-Control"] == "max-age=3600, public"
    assert response["headers"]["X-Custom-Header"] == "custom-value"
    assert response["body"] == '{"items":[1,2,3]}'

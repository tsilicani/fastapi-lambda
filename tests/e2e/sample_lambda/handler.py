"""Minimal FastAPI-Lambda application for end-to-end testing."""

from typing import Optional

from pydantic import BaseModel

from fastapi_lambda import FastAPI, JSONResponse, LambdaEvent
from fastapi_lambda.middleware.cors import CORSMiddleware


class Item(BaseModel):
    """Test item model."""

    name: str
    price: float
    description: Optional[str] = None


class ItemResponse(BaseModel):
    """Item response model."""

    id: int
    name: str
    price: float


app = FastAPI(title="E2E Test API", version="1.0.0", debug=True)

# Add CORS middleware for E2E testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com", "https://test.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Custom-Header"],
    allow_credentials=True,
    expose_headers=["X-Request-ID"],
    max_age=3600,
)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello from FastAPI-Lambda"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/cached")
def cached_endpoint():
    """Endpoint with custom cache headers."""
    return JSONResponse(
        content={"data": "cached-content", "timestamp": 1234567890},
        headers={
            "Cache-Control": "max-age=3600, public",
            "X-Custom-Header": "test-value",
        },
    )


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int) -> ItemResponse:
    """Get item by ID."""
    return ItemResponse(id=item_id, name=f"Item {item_id}", price=9.99 * item_id)


@app.post("/items", response_model=ItemResponse)
async def create_item(item: Item) -> ItemResponse:
    """Create new item."""
    # Note: status_code parameter not supported in FastAPI-Lambda router
    # Return 200 by default, or use Response object to set status
    return ItemResponse(id=42, name=item.name, price=item.price)


def handler(event: LambdaEvent, context) -> dict:
    """Lambda handler for API Gateway events."""
    import asyncio

    return asyncio.run(app(event, context))

"""
Comprehensive middleware stack tests.

This test suite verifies that the middleware implementation correctly replicates
FastAPI/Starlette behavior with pre-processing, post-processing, and short-circuit capabilities.

## Simplified Real-World Middleware Stack

A typical production API uses logging + authentication:

```
REQUEST
  ↓
┌─────────────────────────────────────┐
│ 1. LoggingMiddleware (OUTERMOST)   │
│    PRE:  Log request, start timer   │
│    POST: Log response, save to DB   │
│      ↓                               │
│    ┌───────────────────────────┐    │
│    │ 2. AuthMiddleware         │    │
│    │    PRE:  Validate API key │    │
│    │          SHORT-CIRCUIT    │    │
│    │    POST: Add X-Auth header│    │
│    │      ↓                     │    │
│    │    ┌─────────────────┐    │    │
│    │    │   HANDLER       │    │    │
│    │    │   Return data   │    │    │
│    │    └─────────────────┘    │    │
│    └───────────────────────────┘    │
└─────────────────────────────────────┘
  ↓
RESPONSE
```

## Mock External Dependencies (Realistic Pattern)

Instead of passing test_context, middleware use external services:

```python
# Mock logger (replaces logging.Logger)
logger = MockLogger()

# Mock database (replaces SQLAlchemy/DynamoDB)
db = MockDatabase()

# Middleware initialized with dependencies
app.add_middleware(LoggingMiddleware, logger=logger, db=db)
app.add_middleware(AuthMiddleware)
```

## Expected Execution Order

**Setup:**
```python
app.add_middleware(LoggingMiddleware, logger=logger, db=db)  # Added 1st → OUTERMOST
app.add_middleware(AuthMiddleware)                           # Added 2nd → INNERMOST
```

**Execution (happy path):**
```
1. Logging PRE     → logger.info("→ GET /api/data"), start timer
2. Auth PRE        → Validate API key
3. HANDLER         → Execute route logic
4. Auth POST       → Add X-Auth-User header
5. Logging POST    → logger.info("← 200 (0.05s)"), db.save(record)
```

**Execution (auth fails - short circuit):**
```
1. Logging PRE     → logger.info("→ GET /api/data")
2. Auth PRE        → INVALID KEY → return 403 ❌ SHORT-CIRCUIT
3. HANDLER         → ❌ SKIPPED
4. Auth POST       → ❌ SKIPPED (short-circuit doesn't run post)
5. Logging POST    → logger.info("← 403 (0.01s)"), db.save(record) ✅ (outer middleware still runs)
```
"""

import time
from typing import Any, Awaitable, Callable, Dict, List

from fastapi_lambda.requests import LambdaRequest
from fastapi_lambda.response import JSONResponse, LambdaResponse

# =============================================================================
# MOCK DEPENDENCIES (Realistic External Services)
# =============================================================================


class MockLogger:
    """Mock logger that records log entries (replaces logging.Logger)."""

    def __init__(self):
        self.logs: List[str] = []

    def info(self, message: str) -> None:
        """Log info message."""
        self.logs.append(f"INFO: {message}")

    def error(self, message: str) -> None:
        """Log error message."""
        self.logs.append(f"ERROR: {message}")


class MockDatabase:
    """Mock database that stores records (replaces DynamoDB/SQLAlchemy)."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def save(self, record: Dict[str, Any]) -> None:
        """Save record to database."""
        self.records.append(record)


# =============================================================================
# MIDDLEWARE IMPLEMENTATIONS (Test Fixtures)
# =============================================================================


class LoggingMiddleware:
    """
    Log request/response and save to database.

    Pre-processing:
      - Log incoming request (method + path)
      - Start timer

    Post-processing:
      - Calculate duration
      - Log response (status + duration)
      - Save to database
    """

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[LambdaResponse]],
        logger: MockLogger,
        db: MockDatabase,
    ):
        self.app = app
        self.logger = logger
        self.db = db

    async def __call__(self, request: LambdaRequest) -> LambdaResponse:
        # PRE-PROCESSING
        start_time = time.perf_counter()
        self.logger.info(f"→ {request.method} {request.path}")

        # CALL NEXT
        response = await self.app(request)

        # POST-PROCESSING
        duration = time.perf_counter() - start_time
        self.logger.info(f"← {response.status_code} ({duration:.3f}s)")

        # Save to database
        self.db.save(
            {
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration": duration,
            }
        )

        return response


class AuthMiddleware:
    """
    Validate API key and add user header.

    Pre-processing:
      - Extract X-API-Key header
      - Validate key format
      - SHORT-CIRCUIT: Return 401 if missing
      - SHORT-CIRCUIT: Return 403 if invalid

    Post-processing:
      - Add X-Auth-User header with user ID
    """

    def __init__(
        self,
        app: Callable[[LambdaRequest], Awaitable[LambdaResponse]],
    ):
        self.app = app

    async def __call__(self, request: LambdaRequest) -> LambdaResponse:
        # PRE-PROCESSING: Validate API key
        api_key = request.headers.get("x-api-key", "")

        if not api_key:
            # SHORT-CIRCUIT: Missing API key
            return JSONResponse(
                {"error": "Missing API key"},
                status_code=401,
            )

        # Simple validation: key format is "valid-key-{user_id}"
        if not api_key.startswith("valid-key-"):
            # SHORT-CIRCUIT: Invalid API key
            return JSONResponse(
                {"error": "Invalid API key"},
                status_code=403,
            )

        # Extract user_id from key
        user_id = api_key.split("-")[-1]

        # CALL NEXT
        response = await self.app(request)

        # POST-PROCESSING: Add user header
        response.headers["X-Auth-User"] = user_id

        return response


# =============================================================================
# TEST CASES
# =============================================================================

# TODO: Implement test cases:
# - test_middleware_happy_path()
# - test_middleware_auth_missing_key()
# - test_middleware_auth_invalid_key()
# - test_middleware_execution_order()

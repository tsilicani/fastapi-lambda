# FastAPI-Lambda - Lambda-Optimized FastAPI Framework

**Drop-in replacement for FastAPI** optimized for AWS Lambda with minimal cold start overhead and package size.

## Legal & License

**License:** MIT License

This project is derived from [FastAPI](https://github.com/fastapi/fastapi) by Sebastián Ramírez, also licensed under MIT.

### Attribution Requirements
- ✅ MIT License included in `LICENSE` file
- ✅ Original FastAPI copyright preserved
- ✅ Attribution in README.md
- ✅ NOTICE file with detailed attribution
- ✅ No trademark conflicts (using "FastAPI-Lambda" name)

See `LICENSE` and `NOTICE` files for full details.

## Overview

FastAPI-Lambda is a lightweight, Lambda-optimized framework that maintains FastAPI's intuitive API while removing unnecessary dependencies and features incompatible with serverless environments. Write standard FastAPI code, deploy to Lambda with improved performance.

**Key Benefits:**
- 🚀 **<500ms cold starts** (no ASGI layer overhead)
- 🔄 **Same FastAPI interfaces** - minimal code changes required
- 📦 **Pydantic v2.7+ only** - single lightweight dependency
- 🎯 **Lambda-native** - direct API Gateway event handling

## Maintained Features

✅ **HTTP REST API**
- All methods: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD
- Path/Query/Header
- Request body validation
- Response models

✅ **Validation & Serialization**
- **Pydantic v2 only** (v1 support removed for optimization)
- Type-based validation with Rust-powered performance
- JSON encoding/decoding

✅ **Dependency Injection**
- `Depends()` with sync/async functions
- Generator-based cleanup (`yield`)
- Dependency caching
- Request/Response injection

✅ **OpenAPI v3.1.0 Schema Generation**
- Automatic schema generation compliant with OpenAPI 3.1.0 specification
- **JSON-only output at `/openapi.json`** (Swagger UI/ReDoc removed)
- Complete request/response model documentation
- Examples and validation rules in schema
- Use external tools: Swagger Editor, Postman, Insomnia, Redocly
- Lean encoder (`_jsonable_encoder`) for type-safe examples serialization

✅ **Security (Simplified)**
- HTTP Bearer (JWT tokens)

✅ **Middleware** 🚧 (Refactoring in progress - see Active Development section)
- AsyncExitStack for DI cleanup
- Custom middleware support (currently post-processing only, being refactored to full pre/post pattern)

## Architecture

### Core Dependencies
pydantic > 2.7

### Phase 7: Simplified Dependency Injection (Future)
- Flatten recursive dependency resolution
- Pre-compute dependency graph at import time
- Reduce AsyncExitStack overhead

### Phase 8: Request Parsing Optimization (Future)
- Pre-compiled route patterns
- Cached parameter extractors
- Zero-copy where possible

## API Compatibility

**Goal:** Drop-in replacement for common FastAPI patterns

**Compatible:**

```python
from fastapi import FastAPI, Query, Depends, HTTPException

app = FastAPI()

def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/{item_id}")
def read_item(
    item_id: int,
    q: str = Query(None),
    db = Depends(get_db)
):
    if item_id not in db:
        raise HTTPException(status_code=404)
    return {"item_id": item_id, "q": q}
```

**Incompatible (Removed):**

```python
# ❌ WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    pass

# ❌ OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ❌ Background tasks
@app.post("/send-email")
def send_email(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_task)  # Never executes!
```

## Performance Targets

**Current FastAPI in Lambda:**
- Cold start: 1-2s (with ASGI layer)
- Package size: ~5.8MB
- Memory overhead: ASGI + middleware stack

**fastapi_lambda Target:**
- Cold start: <500ms (no ASGI, pre-compiled routes)
- Package size: ~3MB (50% reduction)
- Memory: Minimal overhead, direct event handling

## Implementation Guidelines

### Code Quality Principles

**Brevity & Leanness:**
- Keep functions short (20-30 lines max)
- Remove unnecessary abstractions
- Prefer flat over nested code
- Explicit over implicit

**File Structure:**
- **Follow FastAPI/Starlette naming conventions**
  - Match original source structure for familiarity and compatibility
  - Reference: [Starlette structure](https://github.com/encode/starlette)

**Speed:**
- Direct Lambda event handling (no ASGI overhead)
- Pre-compiled route patterns
- Minimal dependency chain
- Pydantic v2 Rust-powered validation

**Testing:**
- **Mandatory test coverage** for all new code
- Target: >80% coverage (currently 83%)
- Test edge cases and error paths
- **Always use `npm run test:cov`** for fast iterations (auto-excludes e2e tests)
- E2E tests require AWS deployment: use `npm run test:e2e` when needed

### Code Quality Tools

**Static Analysis:**
- **vulture** - Dead code detection
- **mypy** - Type checking
- **Pylance** - VS Code type analysis

**Testing:**
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **pytest-asyncio** - Async test support

**Coverage Importance:**
- Coverage is a **critical metric** for code health
- Minimum 80% coverage required for production
- 100% coverage for critical paths (DI, validation, OpenAPI)
- Use coverage to identify dead code and untested edge cases

**Example workflow:**

```bash
# Run tests with coverage (excludes e2e)
npm run test:cov

# Find dead code
npm run vulture

# Type checking
npm run typecheck

# E2E tests (requires AWS deployment)
npm run test:e2e
```

## Removed Features (Lambda Incompatible)

### Removed for Lambda Constraints
- **WebSockets** - Lambda doesn't support persistent connections
- **Background tasks** - Lambda execution stops after response
- **File uploads** - Use S3 pre-signed URLs instead
- **Streaming responses** - 6MB Lambda payload limit
- **OAuth2PasswordBearer** - Simplified to HTTP Bearer only
- **Swagger UI/ReDoc** - Removed to reduce package size (use external tools)

### Removed for Optimization
- **Starlette ASGI layer** - Direct event handling
- **Pydantic v1 compatibility** - v2.7+ only for performance
- **jsonable_encoder legacy code** - Simplified 48-line implementation
- **Unused FastAPI modules** - Cookie params, WebSocket params, etc.
- **Automatic sync/async mixing** - No threadpool for sync deps in async context (FastAPI has this via Starlette)

## References

- **Original FastAPI:** https://github.com/fastapi/fastapi
- **Starlette:** https://github.com/encode/starlette
- **Pydantic:** https://github.com/pydantic/pydantic
- **AWS Lambda:** https://aws.amazon.com/lambda/
- **API Gateway:** https://aws.amazon.com/api-gateway/

---

## 🚧 Active Development: Middleware Stack Refactor

### Goal
Replicate FastAPI/Starlette middleware behavior faithfully while maintaining Lambda-native architecture (no ASGI).

### Current Status: **IN PROGRESS**

**Problem identified:**
Current implementation applies middleware ONLY after routing (post-processing only). This prevents:
- ❌ Pre-request processing (auth checks, logging, request modification)
- ❌ Short-circuit behavior (early returns without calling handler)
- ❌ CORS preflight handling before routing
- ❌ Proper middleware stack execution order

**Target behavior (FastAPI/Starlette pattern):**
```
Request → Middleware A (PRE) → Middleware B (PRE) → Handler → Middleware B (POST) → Middleware A (POST) → Response
```

### Implementation Plan

#### Phase 1: Test Suite (TDD Approach) ✅ PRIORITY
**File:** `tests/test_middleware.py`

Test categories:
- **Stack execution order** - Verify LIFO execution (last added = outermost)
- **Pre-processing** - Middleware modifies request before routing
- **Post-processing** - Middleware modifies response after handler
- **Short-circuit** - Middleware returns early without calling handler (auth, rate limit, CORS preflight)
- **Lazy stack building** - Stack built on first request, invalidated when middleware added
- **Multiple middleware integration** - Realistic stack with 3+ layers
- **Mock/stub helpers** - `CallRecorderMiddleware`, `ShortCircuitMiddleware` for testing

**Coverage target:** 100% for middleware stack logic

#### Phase 2: Core Infrastructure (`app.py`)
- Add `_middleware_stack: Optional[Callable]` for lazy-built stack
- Implement `build_middleware_stack()` - reverse-order wrapping (chain of responsibility pattern)
- Refactor `__call__()` to use middleware stack
- Remove old post-routing middleware loop

#### Phase 3: CORS Rewrite (`cors.py`)
Convert from `process_request(request, response)` to:
```python
class CORSMiddleware:
    def __init__(self, app: Callable, **options):
        self.app = app  # Next layer in stack

    async def __call__(self, request: LambdaRequest) -> LambdaResponse:
        # PRE: Handle preflight (short-circuit)
        if is_preflight(request):
            return preflight_response()

        # CALL NEXT: Execute handler
        response = await self.app(request)

        # POST: Add CORS headers
        add_cors_headers(response)
        return response
```

#### Phase 4: Verify Compatibility
- All 19 existing CORS tests must pass unchanged
- No breaking changes to public API

#### Phase 5: APIRouter Implementation
**New file:** `fastapi_lambda/api_router.py`

Features:
- Route grouping with shared prefix/tags/dependencies
- Router-level middleware (applied only to router routes)
- `app.include_router(router)` support
- FastAPI-compatible API

#### Phase 6: APIRouter Tests
**File:** `tests/test_api_router.py`
- Router with prefix/tags
- Router-level middleware
- Nested routers

#### Phase 7: Documentation
- Update README with middleware examples
- Update ARCHITECTURE.md with stack diagram
- Migration notes (if any breaking changes)

### Key Technical Decisions

**Pattern:** Class-based middleware with `__call__` method (Starlette-compatible)
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

**Stack building:** Lazy initialization on first request, invalidated when middleware added

**Execution order:** Reverse order (LIFO) - last added middleware is outermost
```python
app.add_middleware(A)  # Innermost
app.add_middleware(B)
app.add_middleware(C)  # Outermost
# Execution: C-PRE → B-PRE → A-PRE → Handler → A-POST → B-POST → C-POST
```

**Lambda-native:** Replace ASGI `(scope, receive, send)` with `LambdaRequest → LambdaResponse`

### TODO Checklist

- [ ] **Phase 1:** Create `tests/test_middleware.py` with comprehensive test suite
  - [ ] Stack execution order tests (LIFO verification)
  - [ ] Pre-processing tests (request modification)
  - [ ] Post-processing tests (response modification)
  - [ ] Short-circuit tests (auth, rate limit, CORS preflight)
  - [ ] Lazy stack building tests
  - [ ] Mock/stub helper middleware classes
- [ ] **Phase 2:** Implement `build_middleware_stack()` in `app.py`
  - [ ] Add `_middleware_stack` attribute
  - [ ] Implement lazy stack building
  - [ ] Refactor `__call__()` to use stack
  - [ ] Remove old middleware loop
- [ ] **Phase 3:** Rewrite `CORSMiddleware` with `__call__` pattern
  - [ ] Convert to callable class with `app` parameter
  - [ ] Implement pre-processing (preflight short-circuit)
  - [ ] Implement post-processing (add CORS headers)
  - [ ] Keep all existing helper methods
- [ ] **Phase 4:** Verify all 19 CORS tests pass
  - [ ] Run `pytest tests/test_cors.py -v`
  - [ ] Fix any compatibility issues
- [ ] **Phase 5:** Implement `APIRouter` class
  - [ ] Create `fastapi_lambda/api_router.py`
  - [ ] Implement route decorators (get/post/put/delete/patch)
  - [ ] Add router-level middleware support
  - [ ] Implement `include_router()` in FastAPI class
- [ ] **Phase 6:** Create APIRouter tests
  - [ ] Prefix/tags tests
  - [ ] Router middleware tests
  - [ ] Nested router tests
- [ ] **Phase 7:** Update documentation
  - [ ] README.md - middleware examples
  - [ ] ARCHITECTURE.md - stack diagram
  - [ ] This file - mark as complete

### Estimated Timeline
- Phase 1: 3 hours (test-first approach)
- Phase 2: 2 hours (core refactor)
- Phase 3: 1 hour (CORS rewrite)
- Phase 4: 0.5 hours (verification)
- Phase 5: 2 hours (APIRouter)
- Phase 6: 1.5 hours (APIRouter tests)
- Phase 7: 1 hour (docs)

**Total: ~11 hours**

---

## Future implementations

### Testing & QA
- [x] End-to-end tests with Serverless Framework
  - ✅ Complete implementation with serverless.yml, pytest fixtures, and 24 tests
  - ✅ Tests all 3 deployment types: Lambda URL, API Gateway v1, API Gateway v2
  - ✅ Parametrized fixtures for comprehensive coverage
  - 📝 See `tests/e2e/README.md` for detailed setup and usage
- [ ] Integrate Bandit for security linting
- [ ] Add code complexity analysis (radon or flake8-mccabe)

### Tooling & Formatting
- [ ] Adopt isort (or confirm Black handles import ordering adequately)
- [x] Ensure consistent lint/format checks in CI
  - ✅ GitHub Actions CI workflow with tests, linting, type-check

### Development Experience
- [ ] Add live development server
  - [ ] Hot reload on code changes
  - [ ] Simulate Lambda execution locally
  - [ ] Mock API Gateway/Lambda context
  - [ ] Environment variable management
  - [ ] Consider using `uvicorn` or custom solution
  - Goal: `fastapi-lambda dev handler.py` for instant local testing
- [ ] Auto-threadpool for sync dependencies in async context
  - Currently: sync deps in async endpoints/deps raise `RuntimeError`
  - FastAPI behavior: auto-runs sync deps in threadpool via Starlette
  - Trade-off: adds complexity and minimal overhead vs explicit async/sync separation
  - Consider: optional flag `auto_threadpool=True` for FastAPI compatibility
- [ ] **Make all middleware assignment FastAPI compatible**
  - Currently: Only `app.add_middleware()` is implemented
  - Missing patterns:
    - [ ] Constructor `middleware` parameter (Starlette-style)
      - Accept `Optional[Sequence[Middleware]]` in `__init__`
      - Example: `app = FastAPI(middleware=[Middleware(CORS, ...)])`
    - [ ] `@app.middleware("http")` decorator
      - Implement `FastAPI.middleware(middleware_type: str)` method
      - Create `BaseHTTPMiddleware` helper class
      - Wraps function with `(request, call_next)` signature
      - Example:
        ```python
        @app.middleware("http")
        async def add_header(request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Custom"] = "value"
            return response
        ```
  - Implementation steps:
    - [ ] Add `middleware` param to `FastAPI.__init__` with `Sequence` type
    - [ ] Create `BaseHTTPMiddleware` class in `middleware/base.py`
    - [ ] Implement `FastAPI.middleware()` decorator method
    - [ ] Add comprehensive tests for all 3 patterns
    - [ ] Update docs with examples of all middleware assignment methods
  - Estimated effort: ~1.5 hours
  - Benefits: Full FastAPI API compatibility, more flexible middleware setup
- [🚧] `APIRouter` support - **IN PROGRESS** (see Active Development section)
  - Part of middleware stack refactor
  - Includes route grouping with shared prefix/tags/dependencies
  - Router-level middleware support

### CI/CD & Release
- [x] Set up GitHub Actions CI (tests, coverage, linting, type-check)
  - ✅ `.github/workflows/ci.yml` - Runs on main/PR
  - ✅ Tests on Python 3.10, 3.11, 3.12
- [x] Publish to PyPI (versioning, changelog, metadata)
  - ✅ `.github/workflows/publish.yml` - Auto-publish on `release` branch
  - ✅ Published: https://pypi.org/project/fastapi-lambda/
  - ✅ MIT License with proper FastAPI attribution
  - ✅ Complete package metadata

### Community & Outreach
- [ ] Share on Twitter/X with FastAPI community tag
- [ ] Post on Reddit
  - [ ] r/Python - Share as "Show & Tell"
  - [ ] r/aws - AWS Lambda optimization angle
  - [ ] r/FastAPI (if exists) or FastAPI Discord
- [ ] Write blog post on Dev.to or Hashnode
  - Topic: "FastAPI for Lambda: <500ms Cold Starts"
  - Include performance benchmarks vs standard FastAPI
- [ ] Create example projects showcasing different use cases
- [ ] Contribute to awesome-fastapi list (if accepted)

### Documentation & Examples
- [ ] Add an `examples/` folder with minimal sample projects
  - [ ] Basic CRUD API
  - [ ] JWT authentication example
  - [ ] Multi-function Lambda deployment
- [ ] Write a concise doc detailing unsupported FastAPI features and rationale (e.g., WebSockets, forms, background tasks)
- [x] Add PyPI and CI badges to `README.md`
- [ ] Add coverage badge when Codecov is set up
- [ ] Add an architecture diagram in this document (`CLAUDE.md`) showing class/function interactions
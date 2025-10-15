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

✅ **Middleware**
- AsyncExitStack for DI cleanup
- Custom middleware support

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

**Speed:**
- Direct Lambda event handling (no ASGI overhead)
- Pre-compiled route patterns
- Minimal dependency chain
- Pydantic v2 Rust-powered validation

**Testing:**
- **Mandatory test coverage** for all new code
- Target: >80% coverage (currently 83%)
- Test edge cases and error paths
- Use pytest with coverage reporting

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
# Run tests with coverage
poetry run pytest --cov=fastapi_lambda --cov-report=term-missing

# Find dead code
poetry run vulture fastapi_lambda/

# Type checking
mypy fastapi_lambda/
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
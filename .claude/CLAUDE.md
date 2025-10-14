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

FastAPIFn is a lightweight, Lambda-optimized framework that maintains FastAPI's intuitive API while removing unnecessary dependencies and features incompatible with serverless environments. Write standard FastAPI code, deploy to Lambda with improved performance.

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

**fastapifn Target:**
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
poetry run pytest --cov=fastapifn --cov-report=term-missing

# Find dead code
poetry run vulture fastapifn/

# Type checking
mypy fastapifn/
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

## References

- **Original FastAPI:** https://github.com/fastapi/fastapi
- **Starlette:** https://github.com/encode/starlette
- **Pydantic:** https://github.com/pydantic/pydantic
- **AWS Lambda:** https://aws.amazon.com/lambda/
- **API Gateway:** https://aws.amazon.com/api-gateway/

## Future implementations

### Testing & QA
- [x] End-to-end tests with AWS SAM Local for Lambda testing
  - ✅ Complete implementation with SAM template, pytest fixtures, and 8 tests
  - ✅ Uses official AWS Lambda runtime (Docker) - zero compatibility issues
  - ✅ Simple setup with `sam local start-api`
  - 📝 See `tests/e2e/README.md` for detailed setup and usage
- [ ] Integrate Bandit for security linting
- [ ] Add code complexity analysis (radon or flake8-mccabe)

### Tooling & Formatting
- [ ] Adopt isort (or confirm Black handles import ordering adequately)
- [ ] Ensure consistent lint/format checks in CI

### CI/CD & Release
- [ ] Set up GitHub Actions CI (tests, coverage, linting, type-check)
- [ ] Publish to PyPI (versioning, changelog, metadata)

### Documentation & Examples
- [ ] Add an `examples/` folder with minimal sample projects
- [ ] Write a concise doc detailing unsupported FastAPI features and rationale (e.g., WebSockets, forms, background tasks)
- [ ] Add coverage and McCabe complexity badges/summary to `README.md`
- [ ] Add an architecture diagram in this document (`CLAUDE.md`) showing class/function interactions
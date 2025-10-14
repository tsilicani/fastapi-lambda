# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-10-14

### Added
- Initial release of FastAPI-Lambda
- Core FastAPI-compatible API (GET, POST, PUT, DELETE, PATCH)
- Support for both sync (`def`) and async (`async def`) endpoints
- Path, Query, Header, and Body parameters
- Request/Response models with Pydantic v2.7+
- Dependency injection with `Depends()`
- OpenAPI 3.1.0 schema generation at `/openapi.json`
- HTTP Bearer security support
- Direct Lambda event handling (no ASGI layer)
- Support for Lambda Function URL, API Gateway v1, and API Gateway v2
- E2E tests with Serverless Framework
- Comprehensive unit test suite with >80% coverage

### Removed (from FastAPI)
- ASGI/Starlette dependency
- WebSocket support (Lambda incompatible)
- Background tasks (Lambda incompatible)
- File upload handling (use S3 pre-signed URLs)
- Streaming responses (Lambda payload limits)
- Swagger UI and ReDoc (reduced package size)
- Pydantic v1 compatibility

### Performance
- <500ms cold start (vs 1-2s with standard FastAPI)
- ~3MB package size (vs ~5.8MB with standard FastAPI)
- 48% package size reduction

### Documentation
- Complete README with usage examples
- E2E testing guide
- Architecture documentation
- Publishing guide for PyPI

[Unreleased]: https://github.com/tsilicani/fastapi-lambda/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tsilicani/fastapi-lambda/releases/tag/v0.1.0

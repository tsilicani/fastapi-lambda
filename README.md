# FastAPI-Lambda

**Drop-in replacement for FastAPI** - Optimized for AWS Lambda with minimal cold start overhead and package size.

[![PyPI version](https://badge.fury.io/py/fastapi-lambda.svg)](https://pypi.org/project/fastapi-lambda/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://static.pepy.tech/badge/fastapi-lambda)](https://pepy.tech/project/fastapi-lambda)
[![Development Status](https://img.shields.io/badge/status-alpha-red.svg)](https://github.com/tsilicani/fastapi-lambda)
[![Stability: Experimental](https://img.shields.io/badge/stability-experimental-orange.svg)](https://github.com/tsilicani/fastapi-lambda)
[![CI](https://github.com/tsilicani/fastapi-lambda/actions/workflows/ci.yml/badge.svg)](https://github.com/tsilicani/fastapi-lambda/actions/workflows/ci.yml)

---

## ⚠️ **EARLY DEVELOPMENT - NOT PRODUCTION READY**

> **WARNING:** This project is in **early alpha stage** and highly unstable. 
> 
> - 🚧 **Breaking changes** may occur without notice
> - 🐛 **Bugs and incomplete features** are expected
> - ❌ **NOT recommended for production use**
> - 📝 **API may change significantly** between versions
> 
> Use at your own risk! For production workloads, consider:
> - [FastAPI](https://github.com/fastapi/fastapi) (original) with [Mangum](https://github.com/jordaneremieff/mangum)
> - Wait for a stable 1.0.0 release of this project

---

## 🚀 Why FastAPI-Lambda?

FastAPI-Lambda is a lightweight, Lambda-optimized framework that maintains FastAPI's intuitive API while removing unnecessary dependencies and features incompatible with serverless environments.

**Key Benefits:**
- ⚡ **<500ms cold starts** - No ASGI layer overhead
- 🔄 **Same FastAPI interfaces** - Minimal code changes required
- 📦 **Lightweight** - Pydantic v2.7+ only (single dependency)
- 🎯 **Lambda-native** - Direct API Gateway event handling
- ✅ **Sync & Async** - Supports both `def` and `async def` endpoints

## 📊 Performance Comparison

| Metric | Standard FastAPI | FastAPI-Lambda |
|--------|-----------------|----------------|
| Cold Start | 1-2s (with ASGI) | <500ms (direct) |
| Package Size | ~5.8MB | ~3MB (48% reduction) |
| Dependencies | Starlette + extras | Pydantic only |
| Memory Overhead | ASGI + middleware | Minimal |

## 📥 Installation

```bash
pip install fastapi-lambda
```

## 🎯 Quick Start

```python
from fastapi_lambda import FastAPI

app = FastAPI()

# Both sync and async endpoints work!
@app.get("/")
def root():
    return {"message": "Hello from Lambda"}

@app.get("/async")
async def async_endpoint():
    return {"message": "Async works too!"}

# Lambda handler
from fastapi_lambda import create_lambda_handler
lambda_handler = create_lambda_handler(app)
```

## 🔌 Deployment

### Lambda Function URL
```yaml
# serverless.yml
functions:
  api:
    handler: handler.lambda_handler
    url:
      cors: true
```

### API Gateway v1 (REST)
```yaml
functions:
  api:
    handler: handler.lambda_handler
    events:
      - http:
          path: "/"
          method: ANY
      - http:
          path: "{proxy+}"
          method: ANY
```

### API Gateway v2 (HTTP)
```yaml
functions:
  api:
    handler: handler.lambda_handler
    events:
      - httpApi:
          path: "/{proxy+}"
          method: "*"
```

## ✅ Supported Features

### HTTP REST API
- ✅ All methods: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD
- ✅ Path/Query/Header parameters
- ✅ Request body validation
- ✅ Response models
- ✅ **Sync and async endpoints**

### Validation & Serialization
- ✅ **Pydantic v2 only** (Rust-powered performance)
- ✅ Type-based validation
- ✅ JSON encoding/decoding

### Dependency Injection
- ✅ `Depends()` with sync/async functions
- ✅ Generator-based cleanup (`yield`)
- ✅ Dependency caching
- ✅ Request/Response injection

### OpenAPI Schema
- ✅ Automatic OpenAPI 3.1.0 schema generation
- ✅ JSON endpoint at `/openapi.json`
- ✅ Complete request/response documentation
- 📝 Use external tools: Swagger Editor, Postman, Insomnia

### Security
- ✅ HTTP Bearer (JWT tokens)
- ✅ Custom security schemes

## ❌ Removed Features (Lambda Incompatible)

| Feature | Why Removed | Alternative |
|---------|-------------|-------------|
| WebSockets | Lambda doesn't support persistent connections | Use AWS API Gateway WebSocket API separately |
| Background Tasks | Lambda stops after response | Use SQS/EventBridge |
| File Uploads | Payload size limits | Use S3 pre-signed URLs |
| Streaming Responses | 6MB Lambda limit | Return URLs to S3 |
| Swagger UI/ReDoc | Reduce package size | Use external tools with `/openapi.json` |

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
npm run test

# With coverage
npm run test:cov

# Watch mode
npm run test:watch
```

### E2E Tests
```bash
# Setup (deploy to AWS)
npm run test:e2e:setup

# Run E2E tests
npm run test:e2e
```

E2E tests automatically run against **all 3 deployment types**:
- Lambda Function URL
- API Gateway v1 (REST)
- API Gateway v2 (HTTP)

See [tests/e2e/README.md](tests/e2e/README.md) for details.

## 📖 Documentation

- [E2E Testing Guide](tests/e2e/README.md)
- [Architecture & Design](.claude/CLAUDE.md)

## 🤝 Contributing

Contributions are welcome! Please ensure:
- ✅ Tests pass (`npm run test`)
- ✅ Coverage >80% (`npm run test:cov`)
- ✅ No linting errors (`npm run lint`)
- ✅ Type checking passes (`npm run typecheck`)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

This project is inspired by and derived from [FastAPI](https://github.com/fastapi/fastapi) by Sebastián Ramírez, licensed under the MIT License.

**FastAPI-Lambda** is an independent fork optimized specifically for AWS Lambda environments. It maintains API compatibility with FastAPI while removing ASGI dependencies and features incompatible with serverless execution.

### Key Differences from FastAPI

- **No ASGI layer** - Direct Lambda event handling
- **Minimal dependencies** - Pydantic v2.7+ only
- **Lambda-optimized** - <500ms cold starts
- **Smaller package** - ~48% size reduction

For traditional web applications or features like WebSockets, use the original [FastAPI](https://github.com/fastapi/fastapi).

## 🔗 Related Projects

- [FastAPI](https://github.com/fastapi/fastapi) - Original FastAPI framework
- [Starlette](https://github.com/encode/starlette) - ASGI framework (removed in this fork)
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Mangum](https://github.com/jordaneremieff/mangum) - ASGI adapter for AWS Lambda (alternative approach)

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/tsilicani/fastapi-lambda/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tsilicani/fastapi-lambda/discussions)

---

Made with ❤️ for the serverless community

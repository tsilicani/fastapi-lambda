# E2E Tests

End-to-end tests for FastAPIFn deployed on AWS Lambda with different integration methods.

## Deployment Types

The serverless configuration deploys the same Lambda function behind 3 different integration methods:

1. **Lambda Function URL** - Direct Lambda invocation via Function URL
2. **API Gateway v1 (REST API)** - Classic REST API Gateway
3. **API Gateway v2 (HTTP API)** - Modern HTTP API Gateway (cheaper, faster)

## Running Tests

### Setup (Deploy to AWS)
```bash
npm run test:e2e:setup
```

This will:
- Copy the `fastapifn` package to `sample_lambda/`
- Deploy using Serverless Framework
- Save deployment URLs to `stack-output.json`

### Run All E2E Tests
```bash
npm run test:e2e
```

Each test will run **3 times** (once for each deployment type):
- ✅ Lambda URL
- ✅ API Gateway v1 (REST)
- ✅ API Gateway v2 (HTTP)

### Run Tests for Specific Deployment Type

```bash
# Only Lambda URL
poetry run pytest tests/e2e/ -v -k "Lambda URL"

# Only API Gateway v1
poetry run pytest tests/e2e/ -v -k "API Gateway v1"

# Only API Gateway v2
poetry run pytest tests/e2e/ -v -k "API Gateway v2"
```

### Run Single Test

```bash
# Run health check on all 3 deployments
poetry run pytest tests/e2e/test_smoke.py::test_health_endpoint -v

# Run health check only on Lambda URL
poetry run pytest tests/e2e/test_smoke.py::test_health_endpoint -v -k "Lambda URL"
```

## Test Structure

### conftest.py

**`api_base_url` fixture** (parametrized):
- Automatically runs tests on all 3 deployment types
- Uses `pytest.mark.parametrize` to create 3 test variations

**Specific URL fixtures** (for targeted tests):
- `lambda_url` - Lambda Function URL only
- `api_gateway_v1_url` - API Gateway v1 only
- `api_gateway_v2_url` - API Gateway v2 only

### test_smoke.py

Basic smoke tests that verify:
- ✅ Root endpoint
- ✅ Health check
- ✅ GET with path parameters
- ✅ POST with request body
- ✅ OpenAPI schema generation
- ✅ Validation errors (422)
- ✅ Not found errors (404)

## Expected Output

When running tests, you'll see output like:

```
tests/e2e/test_smoke.py::test_root_endpoint[Lambda URL] PASSED
tests/e2e/test_smoke.py::test_root_endpoint[API Gateway v1 (REST)] PASSED
tests/e2e/test_smoke.py::test_root_endpoint[API Gateway v2 (HTTP)] PASSED
tests/e2e/test_smoke.py::test_health_endpoint[Lambda URL] PASSED
tests/e2e/test_smoke.py::test_health_endpoint[API Gateway v1 (REST)] PASSED
tests/e2e/test_smoke.py::test_health_endpoint[API Gateway v2 (HTTP)] PASSED
...
```

## Cleanup

To remove the deployed resources:

```bash
cd tests/e2e
serverless remove
```

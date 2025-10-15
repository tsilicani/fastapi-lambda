# CORS Middleware

FastAPI-Lambda includes a Lambda-native CORS (Cross-Origin Resource Sharing) middleware that works directly with API Gateway events, without requiring ASGI.

## Quick Start

```python
from fastapi_lambda import FastAPI
from fastapi_lambda.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
)

@app.get("/")
async def root():
    return {"message": "Hello with CORS!"}
```

## Configuration Options

### `allow_origins`
List of origins that are allowed to access the API.

```python
# Specific origins
allow_origins=["https://example.com", "https://app.example.com"]

# Allow all origins (use with caution!)
allow_origins=["*"]
```

### `allow_methods`
List of HTTP methods allowed in CORS requests.

```python
# Specific methods
allow_methods=["GET", "POST"]

# All methods
allow_methods=["*"]
# Expands to: ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
```

### `allow_headers`
List of HTTP headers that can be used in actual requests.

```python
# Specific headers
allow_headers=["Authorization", "Content-Type", "X-Custom-Header"]

# Allow all headers
allow_headers=["*"]
```

**Note:** The following headers are always allowed (CORS safelisted):
- `Accept`
- `Accept-Language`
- `Content-Language`
- `Content-Type`

### `allow_credentials`
Whether to allow credentials (cookies, authorization headers) in CORS requests.

```python
allow_credentials=True  # Allow cookies/auth headers
allow_credentials=False # Default: no credentials
```

**Important:** When `allow_credentials=True`, you cannot use `allow_origins=["*"]`. You must specify exact origins.

### `allow_origin_regex`
Regex pattern for allowed origins. Useful for matching multiple subdomains.

```python
allow_origin_regex=r"https://.*\.example\.com"
# Matches: https://app.example.com, https://api.example.com, etc.
```

### `expose_headers`
List of response headers that browsers are allowed to access.

```python
expose_headers=["X-Request-ID", "X-Custom-Header"]
```

### `max_age`
Maximum time (in seconds) that browsers should cache CORS preflight responses.

```python
max_age=3600  # Cache for 1 hour
max_age=600   # Default: 10 minutes
```

## Common Patterns

### Production API
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://example.com",
        "https://www.example.com",
        "https://app.example.com",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    expose_headers=["X-Request-ID"],
    max_age=3600,
)
```

### Development (Allow All)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

⚠️ **Warning:** Never use `allow_origins=["*"]` in production unless your API is truly public!

### Subdomain Matching
```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.mycompany\.com",
    allow_methods=["GET", "POST", "PUT"],
    allow_credentials=True,
)
```

### Multiple Environments
```python
import os

ALLOWED_ORIGINS = {
    "development": ["http://localhost:3000", "http://localhost:8080"],
    "staging": ["https://staging.example.com"],
    "production": ["https://example.com", "https://www.example.com"],
}

env = os.getenv("ENVIRONMENT", "development")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS[env],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## How CORS Works

### Simple Requests
For simple GET requests, the middleware adds CORS headers to the response:

```
Request:
  GET /api/data
  Origin: https://example.com

Response:
  Access-Control-Allow-Origin: https://example.com
  Access-Control-Allow-Credentials: true
```

### Preflight Requests
For complex requests (POST, PUT, DELETE, custom headers), browsers send a preflight OPTIONS request first:

```
Preflight Request:
  OPTIONS /api/data
  Origin: https://example.com
  Access-Control-Request-Method: POST
  Access-Control-Request-Headers: Authorization

Preflight Response:
  Access-Control-Allow-Origin: https://example.com
  Access-Control-Allow-Methods: GET, POST, PUT, DELETE
  Access-Control-Allow-Headers: Authorization, Content-Type
  Access-Control-Max-Age: 3600
```

The middleware automatically handles preflight requests and returns appropriate responses.

## Differences from Starlette CORS

FastAPI-Lambda's CORS middleware is adapted from Starlette but works directly with Lambda events:

| Feature | Starlette | FastAPI-Lambda |
|---------|-----------|----------------|
| Layer | ASGI middleware | Lambda-native |
| Async/Await | Required | Not required |
| Overhead | ASGI stack | Minimal |
| Event Handling | scope/receive/send | Direct Lambda event |

## Testing CORS

### Using curl
```bash
# Preflight request
curl -X OPTIONS https://your-api.com/endpoint \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -i

# Actual request
curl -X POST https://your-api.com/endpoint \
  -H "Origin: https://example.com" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}' \
  -i
```

### Using JavaScript
```javascript
fetch('https://your-api.com/endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_TOKEN',
  },
  credentials: 'include', // Send cookies
  body: JSON.stringify({ key: 'value' }),
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

## Troubleshooting

### CORS Error: "Origin not allowed"
**Problem:** Browser blocks request due to origin mismatch.

**Solution:** Add the origin to `allow_origins`:
```python
allow_origins=["https://your-frontend.com"]
```

### CORS Error: "Credentials flag is true, but Access-Control-Allow-Credentials is not"
**Problem:** Frontend sends credentials but backend doesn't allow them.

**Solution:** Enable credentials:
```python
allow_credentials=True
```

### CORS Error: "Method not allowed"
**Problem:** HTTP method not in `allow_methods`.

**Solution:** Add the method:
```python
allow_methods=["GET", "POST", "PUT", "DELETE"]
# Or allow all:
allow_methods=["*"]
```

### CORS Error: "Header not allowed"
**Problem:** Custom header not in `allow_headers`.

**Solution:** Add the header:
```python
allow_headers=["Authorization", "X-Custom-Header"]
# Or allow all:
allow_headers=["*"]
```

### No CORS headers in response
**Problem:** CORS middleware not processing requests.

**Causes:**
1. Request missing `Origin` header
2. Middleware not added to app
3. Origin not in allowed list

**Solution:** Verify middleware is added and origin is allowed.

## Security Best Practices

1. **Never use wildcards in production** unless your API is truly public:
   ```python
   # ❌ Dangerous in production
   allow_origins=["*"]
   
   # ✅ Explicit origins
   allow_origins=["https://example.com"]
   ```

2. **Be specific with allowed methods:**
   ```python
   # ❌ Too permissive
   allow_methods=["*"]
   
   # ✅ Only what you need
   allow_methods=["GET", "POST"]
   ```

3. **Use credentials wisely:**
   ```python
   # Only when necessary
   allow_credentials=True
   allow_origins=["https://trusted-app.com"]  # Must be specific!
   ```

4. **Validate origins carefully:**
   ```python
   # ✅ Use regex for subdomains
   allow_origin_regex=r"https://.*\.trusted\.com"
   
   # ✅ Or list explicitly
   allow_origins=["https://app1.com", "https://app2.com"]
   ```

5. **Set reasonable max_age:**
   ```python
   # Cache preflight for 1 hour (reduces OPTIONS requests)
   max_age=3600
   ```

## Examples

See [`examples/cors_example.py`](../examples/cors_example.py) for a complete working example.

## References

- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [W3C CORS Specification](https://www.w3.org/TR/cors/)
- [Starlette CORS Middleware](https://www.starlette.io/middleware/#corsmiddleware) (original implementation)

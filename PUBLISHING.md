# Publishing to PyPI

This guide explains how to publish `fastapi-lambda` to PyPI.

## Prerequisites

1. **Create PyPI Account**: https://pypi.org/account/register/
2. **Create API Token**: https://pypi.org/manage/account/token/
3. **Install build tools**:
   ```bash
   pip install build twine
   ```

## Publishing Steps

### 1. Update Version

Edit `pyproject.toml`:
```toml
[project]
version = "0.1.0"  # Increment this
```

### 2. Build Distribution

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build wheel and source distribution
python -m build
```

### 3. Check Distribution

```bash
# Verify the package
twine check dist/*
```

### 4. Test on TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ fastapi-lambda
```

### 5. Publish to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Or use API token
twine upload -u __token__ -p <your-api-token> dist/*
```

### 6. Verify Installation

```bash
pip install fastapi-lambda
```

## Automated Publishing with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

Then add your PyPI API token as a GitHub secret named `PYPI_API_TOKEN`.

## Version Numbering

Follow Semantic Versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Examples:
- `0.1.0` - Initial release
- `0.1.1` - Bug fix
- `0.2.0` - New feature
- `1.0.0` - Stable release

## Checklist Before Publishing

- [ ] All tests pass (`npm run test`)
- [ ] Coverage >80% (`npm run test:cov`)
- [ ] E2E tests pass (`npm run test:e2e`)
- [ ] README.md is up to date
- [ ] CHANGELOG.md is updated
- [ ] Version bumped in `pyproject.toml`
- [ ] LICENSE and NOTICE files are present
- [ ] No secrets or credentials in code

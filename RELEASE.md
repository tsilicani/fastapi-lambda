# Release Workflow

Guide for publishing new versions to PyPI using the `release` branch.

## 🔄 Workflow Overview

1. **Development** → `main` branch (CI tests on every push)
2. **Pre-release** → Bump version, update CHANGELOG
3. **Merge to `release`** → Auto-publish to PyPI
4. **Tag and GitHub Release** → Created automatically

## 📋 Release Checklist

### Before Release

- [ ] All tests pass on `main` (`npm run test`)
- [ ] Coverage >80% (`npm run test:cov`)
- [ ] E2E tests pass (`npm run test:e2e`)
- [ ] No linting errors (`npm run lint`)
- [ ] Type checking passes (`npm run typecheck`)

### Prepare Release

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"  # Increment
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [0.2.0] - 2025-10-XX
   
   ### Added
   - New feature X
   
   ### Fixed
   - Bug Y
   ```

3. **Commit changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: Bump version to 0.2.0"
   git push origin main
   ```

### Publish to PyPI

4. **Create/update `release` branch**:
   ```bash
   # If release branch doesn't exist yet
   git checkout -b release
   git push -u origin release
   
   # If it already exists
   git checkout release
   git merge main
   git push origin release
   ```

5. **GitHub Actions will automatically**:
   - ✅ Run all tests
   - ✅ Build the package
   - ✅ Validate with twine
   - ✅ Upload to PyPI
   - ✅ Create GitHub release with tag

6. **Monitor the workflow**:
   - Go to: https://github.com/tsilicani/fastapi-lambda/actions
   - Watch the "Publish to PyPI" workflow

### After Release

7. **Verify publication**:
   ```bash
   # Check PyPI
   pip install --upgrade fastapi-lambda
   
   # Verify version
xe   python -c "import fastapi_lambda; print(fastapi_lambda.__version__)"
   ```

8. **Merge back to main** (if needed):
   ```bash
   git checkout main
   git merge release
   git push origin main
   ```

## 🔑 Setup Requirements

### One-time Setup

1. **Create PyPI API Token**:
   - Go to: https://pypi.org/manage/account/token/
   - Create token with scope: "Entire account"
   - Copy the token (starts with `pypi-`)

2. **Add token to GitHub Secrets**:
   - Go to: https://github.com/tsilicani/fastapi-lambda/settings/secrets/actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Paste the token from PyPI
   - Click "Add secret"

3. **Create `release` branch** (first time only):
   ```bash
   git checkout -b release
   git push -u origin release
   git checkout main
   ```

## 🚀 Quick Release (TL;DR)

```bash
# 1. Bump version and update CHANGELOG
vim pyproject.toml CHANGELOG.md

# 2. Commit and push to main
git add .
git commit -m "chore: Bump version to X.Y.Z"
git push origin main

# 3. Merge to release and push
git checkout release
git merge main
git push origin release

# 4. Wait for GitHub Actions to publish
# 5. Verify on PyPI
```

## 🔄 Branch Strategy

```
main (default)
├── Development and testing
├── CI runs on every push
└── Merge to release when ready

release (publish trigger)
├── Triggers PyPI publication
├── Auto-creates GitHub release
└── Keep in sync with main after releases
```

## 📦 Alternative: Manual Publishing

If GitHub Actions fails or you prefer manual control:

```bash
# Build
python -m build

# Check
twine check dist/*

# Upload to TestPyPI (optional)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## 🐛 Troubleshooting

### GitHub Actions fails to publish

1. Check secrets are set correctly
2. Verify PyPI token is valid
3. Check if version already exists on PyPI (can't overwrite)

### Version conflict

PyPI doesn't allow re-uploading the same version:
- Bump version number in `pyproject.toml`
- Delete local `dist/` folder
- Rebuild and retry

### Tests fail in CI

- Run tests locally first
- Check Python version compatibility
- Ensure all dependencies are in `pyproject.toml`

# 📋 Pre-Publishing Checklist

Use this checklist before publishing to PyPI.

## ✅ Legal & Licensing

- [x] MIT License file created (`LICENSE`)
- [x] Original FastAPI attribution included
- [x] NOTICE file with detailed attribution
- [x] README credits section added
- [x] pyproject.toml license metadata set

## ✅ Package Metadata

- [x] Package name: `fastapi-lambda`
- [x] Description mentions FastAPI inspiration
- [x] Author information in pyproject.toml
- [x] Project URLs (homepage, issues, repository)
- [x] Python classifiers added
- [x] Keywords for discoverability

## ✅ Documentation

- [x] README.md with complete usage guide
- [x] CHANGELOG.md with version history
- [x] PUBLISHING.md with release instructions
- [x] E2E testing guide (tests/e2e/README.md)
- [x] Architecture documentation (.claude/CLAUDE.md)

## ✅ Code Quality

- [ ] All unit tests pass (`npm run test`)
- [ ] Coverage >80% (`npm run test:cov`)
- [ ] E2E tests pass (`npm run test:e2e`)
- [ ] No linting errors (`npm run lint`)
- [ ] Type checking passes (`npm run typecheck`)

## ✅ Package Quality

- [ ] No secrets or credentials in code
- [ ] .gitignore excludes build artifacts
- [ ] Dependencies are minimal and necessary
- [ ] No unused imports (check with vulture)

## 📝 Before Publishing

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Test build locally**:
   ```bash
   python -m build
   twine check dist/*
   ```
4. **Test on TestPyPI** (recommended)
5. **Create GitHub release** with tag
6. **Publish to PyPI**

## 🚀 Publishing Command

```bash
# Build
python -m build

# Check
twine check dist/*

# Upload
twine upload dist/*
```

## 📧 Post-Publishing

- [ ] Verify package on PyPI: https://pypi.org/project/fastapi-lambda/
- [ ] Test installation: `pip install fastapi-lambda`
- [ ] Update GitHub README badge with PyPI version
- [ ] Announce on social media / communities
- [ ] Monitor GitHub issues for feedback

## ⚠️ Important Notes

### Name Considerations

The name `fastapi-lambda` was chosen because:
- ✅ Clearly indicates it's for AWS Lambda
- ✅ Shows relationship to FastAPI without claiming to be official
- ✅ Reduces confusion vs `fastapifn` or similar
- ✅ SEO-friendly for "fastapi lambda" searches

### Legal Safety

- ✅ MIT License is permissive and compatible
- ✅ Attribution to original FastAPI is clear
- ✅ Package name doesn't claim official status
- ✅ README explicitly states it's a fork
- ✅ No trademark violations (FastAPI has no registered trademarks)

### Trademark Disclaimer

If Sebastián Ramírez (FastAPI creator) requests name change:
- Be prepared to rename to: `lambda-fastapi`, `fastfn`, or `fnapi`
- Package rename is disruptive but sometimes necessary
- Early versions make this easier

## 🔗 Useful Links

- **PyPI Publishing**: https://packaging.python.org/tutorials/packaging-projects/
- **Twine Documentation**: https://twine.readthedocs.io/
- **Semantic Versioning**: https://semver.org/
- **MIT License**: https://opensource.org/licenses/MIT

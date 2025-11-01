#!/bin/bash
set -e

echo "Starting version bump process..."

PYPROJECT_FILE="pyproject.toml"
INIT_FILE="fastapi_lambda/__init__.py"

if [[ ! -f "$PYPROJECT_FILE" ]]; then
    echo "Error: $PYPROJECT_FILE not found"
    exit 1
fi

if [[ ! -f "$INIT_FILE" ]]; then
    echo "Error: $INIT_FILE not found"
    exit 1
fi

echo "Reading current version from $PYPROJECT_FILE..."
CURRENT_VERSION=$(grep -E '^version = ' "$PYPROJECT_FILE" | sed 's/version = "\(.*\)"/\1/')

if [[ -z "$CURRENT_VERSION" ]]; then
    echo "Error: Could not extract version from $PYPROJECT_FILE"
    exit 1
fi

echo "Current version: $CURRENT_VERSION"

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

if [[ -z "$MAJOR" ]] || [[ -z "$MINOR" ]]; then
    echo "Error: Invalid version format: $CURRENT_VERSION"
    exit 1
fi

NEW_MINOR=$((MINOR + 1))
NEW_PATCH=0
NEW_VERSION="${MAJOR}.${NEW_MINOR}.${NEW_PATCH}"

echo "New version: $NEW_VERSION"

echo "Updating $PYPROJECT_FILE..."
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" "$PYPROJECT_FILE"
rm -f "${PYPROJECT_FILE}.bak"

echo "Updating $INIT_FILE..."
sed -i.bak "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" "$INIT_FILE"
rm -f "${INIT_FILE}.bak"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

echo "Committing version bump..."
git add "$PYPROJECT_FILE" "$INIT_FILE"
git commit -m "chore: Bump version to $NEW_VERSION"

echo "Creating git tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo "Pushing changes to origin/release..."
git push origin release
git push origin "v$NEW_VERSION"

echo "Version bump completed successfully: $CURRENT_VERSION → $NEW_VERSION"

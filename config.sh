#!/bin/bash

test() {
    echo "🧪 Testing..."
    poetry run pytest tests/ -k 'not e2e'
}

test_cov() {
    echo "🧪 Testing with coverage report..."
    poetry run pytest tests/ --cov=fastapi_lambda --cov-report=term-missing --cov-report=html -k 'not e2e'
}

typecheck() {
    echo "🔍 Type checking..."
    poetry run pyright
}

lint() {
    echo "🧹 Linting..."
    poetry run flake8 --statistics && echo "0 issues found"
}

check() {
    typecheck && echo && lint && echo && test && echo && echo "✅ All checks passed"
}
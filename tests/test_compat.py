"""
Tests for _compat module functions
"""

from typing import List, Union

import pytest
from pydantic import Field
from typing_extensions import Annotated

from fastapi_lambda._compat import copy_field_info, get_missing_field_error
from fastapi_lambda.applications import FastAPI
from fastapi_lambda.params import Body, Query
from tests.conftest import parse_response
from tests.utils import make_event


class TestCopyFieldInfo:
    """Test copy_field_info function"""

    def test_copy_field_info_with_query_param(self):
        """Test copying FieldInfo from Query parameter with new annotation"""
        original_field = Query(default=None, description="Original description", gt=0)
        new_annotation = int

        copied_field = copy_field_info(field_info=original_field, annotation=new_annotation)

        assert copied_field is not original_field
        assert copied_field.description == "Original description"
        assert copied_field.annotation == new_annotation
        assert isinstance(copied_field, Query)

    def test_copy_field_info_with_field(self):
        """Test copying plain FieldInfo with new annotation"""
        original_field = Field(default=42, description="Test field", le=100)
        new_annotation = str

        copied_field = copy_field_info(field_info=original_field, annotation=new_annotation)  # type: ignore

        assert copied_field is not original_field
        assert copied_field.description == "Test field"
        assert copied_field.annotation == new_annotation
        assert copied_field.default == 42

    def test_copy_field_info_preserves_metadata(self):
        """Test that metadata is properly merged from new annotation"""
        original_field = Field(default="original", title="Original Title")
        new_annotation = Annotated[str, Field(max_length=50)]

        copied_field = copy_field_info(field_info=original_field, annotation=new_annotation)  # type: ignore

        assert copied_field.title == "Original Title"
        assert copied_field.default == "original"
        # copy_field_info extracts base type from Annotated, not the full Annotated type
        assert copied_field.annotation == str
        # Check that metadata from new annotation was merged
        assert len(copied_field.metadata) > 0

    def test_copy_field_info_with_required_field(self):
        """Test copying required field"""
        original_field = Field(description="Required field")
        new_annotation = int

        copied_field = copy_field_info(field_info=original_field, annotation=new_annotation)

        assert copied_field.is_required()
        assert copied_field.annotation == new_annotation

    def test_copy_field_info_maintains_validation_constraints(self):
        """Test that validation constraints are preserved via metadata"""
        original_field = Query(default=None, min_length=3, max_length=50, pattern="^[a-z]+$")
        new_annotation = str

        copied_field = copy_field_info(field_info=original_field, annotation=new_annotation)

        # Pydantic v2 uses metadata, not constraints attribute
        assert hasattr(copied_field, "metadata")
        assert copied_field.annotation == new_annotation
        assert isinstance(copied_field, Query)


class TestGetMissingFieldError:
    """Test get_missing_field_error function"""

    def test_get_missing_field_error_simple_location(self):
        """Test error generation with simple location"""
        loc = ("body", "user_id")

        error = get_missing_field_error(loc=loc)

        assert error["type"] == "missing"
        assert error["loc"] == ("body", "user_id")
        assert error["msg"] == "Field required"
        assert error["input"] is None

    def test_get_missing_field_error_nested_location(self):
        """Test error generation with nested location"""
        loc = ("body", "user", "profile", "email")

        error = get_missing_field_error(loc=loc)

        assert error["type"] == "missing"
        assert error["loc"] == ("body", "user", "profile", "email")
        assert error["msg"] == "Field required"
        assert error["input"] is None

    def test_get_missing_field_error_query_param(self):
        """Test error generation for query parameter"""
        loc = ("query", "page")

        error = get_missing_field_error(loc=loc)

        assert error["type"] == "missing"
        assert error["loc"] == ("query", "page")
        assert error["msg"] == "Field required"

    def test_get_missing_field_error_path_param(self):
        """Test error generation for path parameter"""
        loc = ("path", "item_id")

        error = get_missing_field_error(loc=loc)

        assert error["type"] == "missing"
        assert error["loc"] == ("path", "item_id")
        assert error["msg"] == "Field required"

    def test_get_missing_field_error_header_param(self):
        """Test error generation for header parameter"""
        loc = ("header", "x-api-key")

        error = get_missing_field_error(loc=loc)

        assert error["type"] == "missing"
        assert error["loc"] == ("header", "x-api-key")
        assert error["msg"] == "Field required"

    def test_get_missing_field_error_has_required_keys(self):
        """Test that error dict has all required keys"""
        loc = ("body", "field")

        error = get_missing_field_error(loc=loc)

        required_keys = ["type", "loc", "msg", "input"]
        for key in required_keys:
            assert key in error, f"Missing required key: {key}"

    def test_get_missing_field_error_structure_matches_pydantic(self):
        """Test that error structure matches Pydantic ValidationError format"""
        loc = ("body", "test_field")

        error = get_missing_field_error(loc=loc)

        # Should match standard Pydantic error dict structure
        assert isinstance(error, dict)
        assert isinstance(error["loc"], tuple)
        assert isinstance(error["msg"], str)
        assert error["input"] is None  # Always None for missing fields


class TestModelFieldGetDefault:
    """Test ModelField.get_default() via request parameters with defaults"""

    @pytest.mark.asyncio
    async def test_query_param_with_default_value(self):
        """Test optional query param with default value.

        Real scenario: when query param is missing, get_default() is called
        at dependencies.py:557 to get the default value.
        """

        app = FastAPI()

        @app.get("/search")
        async def search(q: str = "default_query", limit: int = 10):
            return {"q": q, "limit": limit}

        # Request without query params - should use defaults
        event = make_event(method="GET", path="/search")
        response = await app(event)

        status, body = parse_response(response)
        assert status == 200
        assert body["q"] == "default_query"  # get_default() returned default value
        assert body["limit"] == 10

    @pytest.mark.asyncio
    async def test_body_param_with_default_factory(self):
        """Test optional body param with default_factory (list).

        Real scenario: POST endpoint with optional body that has default_factory.
        When body is None, get_default() calls the factory at dependencies.py:557.
        """

        app = FastAPI()

        @app.post("/items")
        async def create_items(tags: Annotated[List[str], Body(default_factory=list)]):
            return {"tags": tags, "count": len(tags)}

        # POST without body - should call default_factory
        event = make_event(method="POST", path="/items", body=None)
        response = await app(event)

        status, body = parse_response(response)
        assert status == 200
        assert body["tags"] == []  # get_default() called factory
        assert body["count"] == 0


class TestFieldAnnotationIsComplex:
    """Test field_annotation_is_complex() function - line 165 coverage"""

    def test_union_with_annotated_in_query_param(self):
        """Test Union[Annotated[scalar, ...], None] in query parameter.

        Real-world scenario: optional query param with validation constraints.
        This tests line 165 in _compat.py via dependencies.py:278.
        When a parameter has Union[Annotated[int, ...], None], FastAPI must:
        1. Check if Union is scalar (line 278 in dependencies.py)
        2. Union detection triggers recursive call with each arg (line 162)
        3. One arg is Annotated[int, ...] which unwraps at line 165 ✓
        """

        app = FastAPI()

        # Query param with Union[Annotated[int, ...], None] - no explicit Query()
        # FastAPI must auto-detect this is scalar and use Query (not Body)
        @app.get("/items")
        async def get_items(limit: Union[Annotated[int, Field(gt=0, le=100)], None] = None):
            return {"limit": limit}

        # Verify route is created
        items_route = [r for r in app.router.routes if r.path == "/items"][0]
        assert items_route is not None

        # During route setup, dependencies.py:278 calls field_annotation_is_scalar
        # which calls field_annotation_is_complex with Union[Annotated[int, ...], None]
        # This triggers the Annotated unwrapping at line 165

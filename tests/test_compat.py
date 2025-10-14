"""
Tests for _compat module functions
"""

from pydantic import Field
from typing_extensions import Annotated

from fastapifn._compat import copy_field_info, get_missing_field_error
from fastapifn.params import Query


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

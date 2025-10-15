"""
OpenAPI schema generation for Lambda-native FastAPI.

Simplified single-file implementation adapted from the original FastAPI OpenAPI utils.
Generates OpenAPI 3.1.0 schema from Lambda-native routes.
"""

import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path, PurePath
from typing import Any, Dict, List, Optional, Set, Tuple, cast
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import Literal

from fastapi_lambda._compat import (
    GenerateJsonSchema,
    JsonSchemaValue,
    ModelField,
    Undefined,
    get_compat_model_name_map,
    get_definitions,
    get_schema_from_model_field,
    lenient_issubclass,
)
from fastapi_lambda.dependencies import Dependant
from fastapi_lambda.params import Body, ParamTypes

# OpenAPI constants
REF_PREFIX = "#/components/schemas/"
REF_TEMPLATE = "#/components/schemas/{model}"

# Validation error schemas
validation_error_definition = {
    "title": "ValidationError",
    "type": "object",
    "properties": {
        "loc": {
            "title": "Location",
            "type": "array",
            "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "msg": {"title": "Message", "type": "string"},
        "type": {"title": "Error Type", "type": "string"},
    },
    "required": ["loc", "msg", "type"],
}

validation_error_response_definition = {
    "title": "HTTPValidationError",
    "type": "object",
    "properties": {
        "detail": {
            "title": "Detail",
            "type": "array",
            "items": {"$ref": REF_PREFIX + "ValidationError"},
        }
    },
}

status_code_ranges: Dict[str, str] = {
    "1XX": "Information",
    "2XX": "Success",
    "3XX": "Redirection",
    "4XX": "Client Error",
    "5XX": "Server Error",
    "DEFAULT": "Default Response",
}


# Helper functions


def _jsonable_encoder(obj: Any) -> Any:
    """
    Convert objects to JSON-serializable format for OpenAPI examples.

    Simplified encoder for OpenAPI schema examples only. Uses Pydantic v2
    native serialization where possible.
    """
    # Primitives pass through
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Pydantic models - use native v2 serialization
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", by_alias=True, exclude_none=True)

    # Common types in examples
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, datetime.time):
        return obj.isoformat()
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, Decimal):
        if obj.as_tuple().exponent >= 0:  # type: ignore[operator]
            return int(obj)
        return float(obj)
    if isinstance(obj, (Path, PurePath)):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode()

    # Collections - recursive encoding
    if isinstance(obj, dict):
        return {k: _jsonable_encoder(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable_encoder(item) for item in obj]
    if isinstance(obj, (set, frozenset)):
        return [_jsonable_encoder(item) for item in obj]

    # Fallback: convert to string
    return str(obj)


# Helper functions for flattening dependencies and extracting fields


def get_fields_from_routes(routes: List[Any]) -> List[ModelField]:
    """Extract all ModelFields from all routes for schema generation."""
    all_fields: List[ModelField] = []
    fields_seen: Set[int] = set()

    for route in routes:
        if not hasattr(route, "dependant"):
            continue

        # Skip routes that should not be included in schema
        if not getattr(route, "include_in_schema", True):
            continue

        # Get flat dependant with all parameters
        flat_dependant = get_flat_dependant(route.dependant, skip_repeats=True)

        # Collect all parameter fields
        for field in (
            flat_dependant.path_params
            + flat_dependant.query_params
            + flat_dependant.header_params
            + flat_dependant.body_params
        ):
            field_id = id(field)
            if field_id not in fields_seen:
                fields_seen.add(field_id)
                all_fields.append(field)

        # Collect response field if present
        if hasattr(route, "response_field") and route.response_field:
            field_id = id(route.response_field)
            if field_id not in fields_seen:
                fields_seen.add(field_id)
                all_fields.append(route.response_field)

    return all_fields


def get_flat_dependant(dependant: Dependant, *, skip_repeats: bool = False) -> Dependant:
    """Flatten nested dependencies into a single Dependant."""
    flat_dependant = Dependant(
        path_params=dependant.path_params.copy(),
        query_params=dependant.query_params.copy(),
        header_params=dependant.header_params.copy(),
        body_params=dependant.body_params.copy(),
        security_requirements=dependant.security_requirements.copy(),
    )

    visited: Set[Tuple[Any, Tuple[str, ...]]] = set()

    def flatten_dependencies(sub_dependant: Dependant) -> None:
        cache_key = sub_dependant.cache_key
        if skip_repeats and cache_key in visited:
            return
        visited.add(cache_key)

        flat_dependant.path_params.extend(sub_dependant.path_params)
        flat_dependant.query_params.extend(sub_dependant.query_params)
        flat_dependant.header_params.extend(sub_dependant.header_params)
        flat_dependant.body_params.extend(sub_dependant.body_params)
        flat_dependant.security_requirements.extend(sub_dependant.security_requirements)

        for sub_sub_dependant in sub_dependant.dependencies:
            flatten_dependencies(sub_sub_dependant)

    for sub_dependant in dependant.dependencies:
        flatten_dependencies(sub_dependant)

    return flat_dependant


def _get_flat_fields_from_params(params: List[ModelField]) -> List[ModelField]:
    """Get flat list of fields from parameter list."""
    flat_fields: List[ModelField] = []
    for param in params:
        if lenient_issubclass(param.type_, BaseModel):
            # Pydantic model as parameter - extract fields
            from fastapi_lambda._compat import get_cached_model_fields

            model_fields = get_cached_model_fields(param.type_)
            flat_fields.extend(model_fields)
        else:
            flat_fields.append(param)
    return flat_fields


# OpenAPI generation functions


def get_openapi_security_definitions(
    flat_dependant: Dependant,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Extract security definitions and requirements from dependant."""
    security_definitions = {}
    operation_security = []

    for security_requirement in flat_dependant.security_requirements:
        security_definition = _jsonable_encoder(security_requirement.security_scheme.model)
        security_name = security_requirement.security_scheme.scheme_name
        security_definitions[security_name] = security_definition
        operation_security.append({security_name: security_requirement.scopes or []})

    return security_definitions, operation_security


def _get_openapi_operation_parameters(
    *,
    dependant: Dependant,
    schema_generator: GenerateJsonSchema,
    model_name_map: Dict[Any, str],
    field_mapping: Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    separate_input_output_schemas: bool = True,
) -> List[Dict[str, Any]]:
    """Generate OpenAPI parameter definitions for operation."""
    parameters = []
    flat_dependant = get_flat_dependant(dependant, skip_repeats=True)

    path_params = _get_flat_fields_from_params(flat_dependant.path_params)
    query_params = _get_flat_fields_from_params(flat_dependant.query_params)
    header_params = _get_flat_fields_from_params(flat_dependant.header_params)

    parameter_groups = [
        (ParamTypes.path, path_params),
        (ParamTypes.query, query_params),
        (ParamTypes.header, header_params),
    ]

    # Determine default convert_underscores for headers
    default_convert_underscores = True
    if len(flat_dependant.header_params) == 1:
        first_field = flat_dependant.header_params[0]
        if lenient_issubclass(first_field.type_, BaseModel):
            default_convert_underscores = getattr(first_field.field_info, "convert_underscores", True)

    for param_type, param_group in parameter_groups:
        for param in param_group:
            field_info = param.field_info

            # Skip if not included in schema
            if not getattr(field_info, "include_in_schema", True):
                continue

            # Get schema for parameter
            param_schema = get_schema_from_model_field(
                field=param,
                schema_generator=schema_generator,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )

            # Determine parameter name
            name = param.alias
            convert_underscores = getattr(
                param.field_info,
                "convert_underscores",
                default_convert_underscores,
            )
            if param_type == ParamTypes.header and param.alias == param.name and convert_underscores:
                name = param.name.replace("_", "-")

            # Build parameter object
            parameter = {
                "name": name,
                "in": param_type.value,
                "required": param.required,
                "schema": param_schema,
            }

            # Add description if present
            if field_info.description:
                parameter["description"] = field_info.description

            # Add examples
            openapi_examples = getattr(field_info, "openapi_examples", None)
            example = getattr(field_info, "example", None)
            if openapi_examples:
                parameter["examples"] = _jsonable_encoder(openapi_examples)
            elif example != Undefined:
                parameter["example"] = _jsonable_encoder(example)

            # Mark as deprecated if needed
            if getattr(field_info, "deprecated", None):
                parameter["deprecated"] = True

            parameters.append(parameter)

    return parameters


def get_openapi_operation_request_body(
    *,
    body_field: Optional[ModelField],
    schema_generator: GenerateJsonSchema,
    model_name_map: Dict[Any, str],
    field_mapping: Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    separate_input_output_schemas: bool = True,
) -> Optional[Dict[str, Any]]:
    """Generate OpenAPI request body definition."""
    if not body_field:
        return None

    assert isinstance(body_field, ModelField)

    # Get schema for body
    body_schema = get_schema_from_model_field(
        field=body_field,
        schema_generator=schema_generator,
        model_name_map=model_name_map,
        field_mapping=field_mapping,
        separate_input_output_schemas=separate_input_output_schemas,
    )

    field_info = cast(Body, body_field.field_info)
    request_media_type = field_info.media_type
    required = body_field.required

    request_body_oai: Dict[str, Any] = {}
    if required:
        request_body_oai["required"] = required

    request_media_content: Dict[str, Any] = {"schema": body_schema}

    # Add examples
    if field_info.openapi_examples:
        request_media_content["examples"] = _jsonable_encoder(field_info.openapi_examples)
    elif field_info.example != Undefined:
        request_media_content["example"] = _jsonable_encoder(field_info.example)

    request_body_oai["content"] = {request_media_type: request_media_content}

    return request_body_oai


def get_openapi_operation_metadata(
    *,
    path: str,
    method: str,
    operation_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    deprecated: Optional[bool] = None,
) -> Dict[str, Any]:
    """Generate OpenAPI operation metadata."""
    operation: Dict[str, Any] = {}

    if operation_id:
        operation["operationId"] = operation_id

    if tags:
        operation["tags"] = tags

    if summary:
        operation["summary"] = summary

    if description:
        operation["description"] = description

    if deprecated:
        operation["deprecated"] = deprecated

    return operation


def get_openapi_path(
    *,
    route_path: str,
    method: str,
    dependant: Dependant,
    operation_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    response_field: Optional[ModelField] = None,
    responses: Optional[Dict[int, Dict[str, Any]]] = None,
    deprecated: Optional[bool] = None,
    schema_generator: GenerateJsonSchema,
    model_name_map: Dict[Any, str],
    field_mapping: Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    separate_input_output_schemas: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate OpenAPI path item for a single route.

    Returns: (path_item, security_schemes)
    """

    # Build operation metadata
    operation = get_openapi_operation_metadata(
        path=route_path,
        method=method,
        operation_id=operation_id,
        tags=tags,
        summary=summary,
        description=description,
        deprecated=deprecated,
    )

    # Add parameters
    parameters = _get_openapi_operation_parameters(
        dependant=dependant,
        schema_generator=schema_generator,
        model_name_map=model_name_map,
        field_mapping=field_mapping,
        separate_input_output_schemas=separate_input_output_schemas,
    )
    if parameters:
        operation["parameters"] = parameters

    # Add request body
    flat_dependant = get_flat_dependant(dependant)
    if flat_dependant.body_params:
        # Use first body param (FastAPI typically only has one)
        body_field = flat_dependant.body_params[0] if flat_dependant.body_params else None
        request_body = get_openapi_operation_request_body(
            body_field=body_field,
            schema_generator=schema_generator,
            model_name_map=model_name_map,
            field_mapping=field_mapping,
            separate_input_output_schemas=separate_input_output_schemas,
        )
        if request_body:
            operation["requestBody"] = request_body

    # Add responses
    operation_responses: Dict[str, Any] = {}

    # Add success response
    if response_field:
        response_schema = get_schema_from_model_field(
            field=response_field,
            schema_generator=schema_generator,
            model_name_map=model_name_map,
            field_mapping=field_mapping,
            separate_input_output_schemas=separate_input_output_schemas,
        )
        operation_responses["200"] = {
            "description": "Successful Response",
            "content": {"application/json": {"schema": response_schema}},
        }
    else:
        operation_responses["200"] = {"description": "Successful Response"}

    # Add validation error response if there are parameters
    if parameters or flat_dependant.body_params:
        operation_responses["422"] = {
            "description": "Validation Error",
            "content": {"application/json": {"schema": {"$ref": REF_PREFIX + "HTTPValidationError"}}},
        }

    # Add custom responses
    if responses:
        for status_code, response_data in responses.items():
            operation_responses[str(status_code)] = response_data

    operation["responses"] = operation_responses

    # Add security
    security_definitions, operation_security = get_openapi_security_definitions(flat_dependant)
    if operation_security:
        operation["security"] = operation_security

    return operation, security_definitions


def get_openapi_schema(
    *,
    title: str,
    version: str,
    openapi_version: str = "3.1.0",
    description: Optional[str] = None,
    routes: List[Any],
    tags: Optional[List[Dict[str, Any]]] = None,
    servers: Optional[List[Dict[str, str]]] = None,
    separate_input_output_schemas: bool = True,
) -> Dict[str, Any]:
    """
    Generate complete OpenAPI schema from routes.

    Main entry point for schema generation.
    """
    info: Dict[str, Any] = {"title": title, "version": version}
    if description:
        info["description"] = description

    output: Dict[str, Any] = {"openapi": openapi_version, "info": info}

    if servers:
        output["servers"] = servers

    components: Dict[str, Dict[str, Any]] = {}
    paths: Dict[str, Dict[str, Any]] = {}
    security_schemes: Dict[str, Any] = {}

    # Collect all fields from all routes FIRST
    all_fields = get_fields_from_routes(routes)

    # Generate schema definitions for all fields at once
    model_name_map = get_compat_model_name_map(all_fields)
    schema_generator = GenerateJsonSchema(ref_template=REF_TEMPLATE)
    field_mapping, all_definitions = get_definitions(
        fields=all_fields,
        schema_generator=schema_generator,
        model_name_map=model_name_map,
        separate_input_output_schemas=separate_input_output_schemas,
    )

    # Process each route
    for route in routes:
        if not hasattr(route, "dependant"):
            continue

        # Skip routes that should not be included in schema
        if not getattr(route, "include_in_schema", True):
            continue

        route_path = route.path
        methods = route.methods if hasattr(route, "methods") else ["GET"]

        for method in methods:
            method_lower = method.lower()

            # Generate operation
            operation, sec_schemes = get_openapi_path(
                route_path=route_path,
                method=method,
                dependant=route.dependant,
                operation_id=getattr(route, "operation_id", None),
                tags=getattr(route, "tags", None),
                summary=getattr(route, "summary", None),
                description=getattr(route, "description", None),
                response_field=getattr(route, "response_field", None),
                responses=getattr(route, "responses", None),
                deprecated=getattr(route, "deprecated", None),
                schema_generator=schema_generator,
                model_name_map=model_name_map,
                field_mapping=field_mapping,
                separate_input_output_schemas=separate_input_output_schemas,
            )

            # Add to paths
            if route_path not in paths:
                paths[route_path] = {}
            paths[route_path][method_lower] = operation

            # Collect security schemes
            security_schemes.update(sec_schemes)

    if paths:
        output["paths"] = paths

    if security_schemes:
        components["securitySchemes"] = security_schemes

    # Add validation error definitions
    all_definitions["ValidationError"] = validation_error_definition
    all_definitions["HTTPValidationError"] = validation_error_response_definition

    if all_definitions:
        components["schemas"] = all_definitions

    if components:
        output["components"] = components

    if tags:
        output["tags"] = tags

    return output

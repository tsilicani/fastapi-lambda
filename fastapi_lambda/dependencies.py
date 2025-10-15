"""
Lambda-native dependency injection.

Adapted from fastapi/dependencies/utils.py for Lambda events (no ASGI).

Simplified version - only implements what's needed for basic DI without
full ASGI integration.
"""

import inspect
import re
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from copy import copy, deepcopy
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from typing_extensions import Annotated, get_args, get_origin

from fastapi_lambda import params
from fastapi_lambda._compat import (
    ErrorWrapper,
    ModelField,
    RequiredParam,
    Undefined,
    _regenerate_error_with_loc,
    copy_field_info,
    evaluate_forwardref,
    field_annotation_is_scalar,
    get_annotation_from_field_info,
    get_missing_field_error,
    is_scalar_field,
    lenient_issubclass,
)
from fastapi_lambda.request import LambdaRequest
from fastapi_lambda.security import SecurityBase
from fastapi_lambda.utils import create_model_field

# Models for dependency injection


@dataclass
class SecurityRequirement:
    """Security requirement for a dependency."""

    security_scheme: SecurityBase
    scopes: Optional[Sequence[str]] = None


@dataclass
class Dependant:
    """Dependency graph node."""

    path_params: List[ModelField] = field(default_factory=list)
    query_params: List[ModelField] = field(default_factory=list)
    header_params: List[ModelField] = field(default_factory=list)
    body_params: List[ModelField] = field(default_factory=list)
    dependencies: List["Dependant"] = field(default_factory=list)
    security_requirements: List[SecurityRequirement] = field(default_factory=list)
    name: Optional[str] = None
    call: Optional[Callable[..., Any]] = None
    security_scopes: Optional[List[str]] = None
    use_cache: bool = True
    path: Optional[str] = None
    cache_key: Tuple[Optional[Callable[..., Any]], Tuple[str, ...]] = field(init=False)

    def __post_init__(self) -> None:
        self.cache_key = (self.call, tuple(sorted(set(self.security_scopes or []))))


if sys.version_info >= (3, 13):
    from inspect import iscoroutinefunction
else:
    from asyncio import iscoroutinefunction


def is_coroutine_callable(call: Callable[..., Any]) -> bool:
    """Check if callable is async."""
    import inspect

    if inspect.isroutine(call):
        return iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    dunder_call = getattr(call, "__call__", None)
    return iscoroutinefunction(dunder_call)


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    """Check if callable is async generator."""
    import inspect

    if inspect.isasyncgenfunction(call):
        return True
    dunder_call = getattr(call, "__call__", None)
    return inspect.isasyncgenfunction(dunder_call)


def is_gen_callable(call: Callable[..., Any]) -> bool:
    """Check if callable is generator (sync generators not allowed)."""
    import inspect

    if inspect.isgeneratorfunction(call):
        return True
    dunder_call = getattr(call, "__call__", None)
    return inspect.isgeneratorfunction(dunder_call)


async def solve_generator(
    *, call: Callable[..., Any], stack: AsyncExitStack, sub_values: Dict[str, Any], request: LambdaRequest
) -> Any:
    """Solve generator dependency (async only)."""
    if is_gen_callable(call):
        raise RuntimeError(f"Dependency {call} must use async generator (use 'async def' with 'yield')")
    elif is_async_gen_callable(call):
        # Auto-inject LambdaRequest if needed
        call_values = sub_values.copy()
        sig = inspect.signature(call)
        for param_name, param in sig.parameters.items():
            if param.annotation is LambdaRequest or (
                hasattr(param.annotation, "__origin__") and param.annotation.__origin__ is LambdaRequest
            ):
                call_values[param_name] = request

        cm = asynccontextmanager(call)(**call_values)
    else:
        raise RuntimeError(f"Expected generator function for {call}")
    return await stack.enter_async_context(cm)


# Helper functions for get_dependant


def get_path_param_names(path: str) -> set[str]:
    """Extract path parameter names from path string."""
    # Match {param} or {param:type}
    param_regex = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?\}")
    return {match.group(1) for match in param_regex.finditer(path)}


def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
    """Get typed signature of callable."""
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param.annotation, globalns),
        )
        for param in signature.parameters.values()
    ]
    return inspect.Signature(typed_params)


def get_typed_annotation(annotation: Any, globalns: Dict[str, Any]) -> Any:
    """Resolve string annotations."""
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
        if annotation is type(None):
            return None
    return annotation


@dataclass
class ParamDetails:
    """Parameter analysis result."""

    type_annotation: Any
    depends: Optional[params.Depends]
    field: Optional[ModelField]


def analyze_param(
    *,
    param_name: str,
    annotation: Any,
    value: Any,
    is_path_param: bool,
) -> ParamDetails:
    """
    Analyze parameter to extract Field or Depends.

    Simplified from ASGI version - no Request/Response/HTTPConnection support.
    """
    field_info = None
    depends = None
    type_annotation: Any = Any
    use_annotation: Any = Any

    if annotation is not inspect.Signature.empty:
        use_annotation = annotation
        type_annotation = annotation

    # Extract Annotated info
    if get_origin(use_annotation) is Annotated:
        annotated_args = get_args(annotation)
        type_annotation = annotated_args[0]
        fastapi_annotations = [arg for arg in annotated_args[1:] if isinstance(arg, (FieldInfo, params.Depends))]
        fastapi_specific_annotations = [
            arg for arg in fastapi_annotations if isinstance(arg, (params.Param, params.Body, params.Depends))
        ]

        if fastapi_specific_annotations:
            fastapi_annotation: Union[FieldInfo, params.Depends, None] = fastapi_specific_annotations[-1]
        else:
            fastapi_annotation = None

        # Set default for Annotated FieldInfo
        if isinstance(fastapi_annotation, FieldInfo):
            field_info = copy_field_info(field_info=fastapi_annotation, annotation=use_annotation)
            assert field_info.default is Undefined or field_info.default is RequiredParam, (
                f"`{field_info.__class__.__name__}` default value cannot be set in"
                f" `Annotated` for {param_name!r}. Set the default value with `=` instead."
            )
            if value is not inspect.Signature.empty:
                assert not is_path_param, "Path parameters cannot have default values"
                field_info.default = value
            else:
                field_info.default = RequiredParam

        # Get Annotated Depends
        elif isinstance(fastapi_annotation, params.Depends):
            depends = fastapi_annotation

    # Get Depends from default value
    if isinstance(value, params.Depends):
        assert depends is None, (
            "Cannot specify `Depends` in `Annotated` and default value" f" together for {param_name!r}"
        )
        assert field_info is None, (
            "Cannot specify a FastAPI annotation in `Annotated` and `Depends` as a"
            f" default value together for {param_name!r}"
        )
        depends = value

    # Get FieldInfo from default value
    elif isinstance(value, FieldInfo):
        assert field_info is None, (
            "Cannot specify FastAPI annotations in `Annotated` and default value" f" together for {param_name!r}"
        )
        field_info = value
        field_info.annotation = type_annotation

    # Get Depends from type annotation
    if depends is not None and depends.dependency is None:
        depends = copy(depends)
        depends.dependency = type_annotation

    # Special case: LambdaRequest should be injected, not validated
    # Skip creating field/depends - it will be injected during solve_dependencies
    if type_annotation is LambdaRequest or (
        hasattr(type_annotation, "__origin__") and type_annotation.__origin__ is LambdaRequest
    ):
        # Return early - no field or depends needed, will be injected automatically
        return ParamDetails(type_annotation=type_annotation, depends=None, field=None)

    # Handle default assignments
    field = None
    if field_info is None and depends is None:
        default_value = value if value is not inspect.Signature.empty else RequiredParam
        if is_path_param:
            field_info = params.Path(annotation=use_annotation)
        elif not field_annotation_is_scalar(annotation=type_annotation):
            field_info = params.Body(annotation=use_annotation, default=default_value)
        else:
            field_info = params.Query(annotation=use_annotation, default=default_value)

    # Create field
    if field_info is not None:
        if is_path_param:
            assert isinstance(field_info, params.Path), (
                f"Cannot use `{field_info.__class__.__name__}` for path param" f" {param_name!r}"
            )
        elif isinstance(field_info, params.Param) and getattr(field_info, "in_", None) is None:
            field_info.in_ = params.ParamTypes.query

        use_annotation_from_field_info = get_annotation_from_field_info(
            use_annotation,
            field_info,
        )

        if not field_info.alias and getattr(field_info, "convert_underscores", None):
            alias = param_name.replace("_", "-")
        else:
            alias = field_info.alias or param_name

        field_info.alias = alias

        field = create_model_field(
            name=param_name,
            type_=use_annotation_from_field_info,
            default=field_info.default,
            alias=alias,
            field_info=field_info,
        )

        if is_path_param:
            assert is_scalar_field(field=field), "Path params must be of one of the supported types"

    return ParamDetails(type_annotation=type_annotation, depends=depends, field=field)


def add_param_to_fields(*, field: ModelField, dependant: Dependant) -> None:
    """Add field to appropriate dependant list."""
    field_info = field.field_info
    field_info_in = getattr(field_info, "in_", None)

    if field_info_in == params.ParamTypes.path:
        dependant.path_params.append(field)
    elif field_info_in == params.ParamTypes.query:
        dependant.query_params.append(field)
    elif field_info_in == params.ParamTypes.header:
        dependant.header_params.append(field)
    else:
        raise ValueError(f"Invalid parameter type for {field.name}: {field_info_in}")


def get_param_sub_dependant(
    *,
    param_name: str,
    depends: params.Depends,
    path: str,
    security_scopes: Optional[List[str]] = None,
) -> Dependant:
    """Get sub-dependant for parameter."""
    assert depends.dependency
    return get_sub_dependant(
        depends=depends,
        dependency=depends.dependency,
        path=path,
        name=param_name,
        security_scopes=security_scopes,
    )


def get_sub_dependant(
    *,
    depends: params.Depends,
    dependency: Callable[..., Any],
    path: str,
    name: Optional[str] = None,
    security_scopes: Optional[List[str]] = None,
) -> Dependant:
    """Get sub-dependant."""
    security_requirement = None
    security_scopes = security_scopes or []

    if isinstance(depends, params.Security):
        dependency_scopes = depends.scopes
        security_scopes.extend(dependency_scopes)

    if isinstance(dependency, SecurityBase):
        security_requirement = SecurityRequirement(security_scheme=dependency, scopes=[])

    sub_dependant = get_dependant(
        path=path,
        # FIXME: type error
        call=dependency,  # type: ignore[arg-type]
        name=name,
        security_scopes=security_scopes,
        use_cache=depends.use_cache,
    )

    if security_requirement:
        sub_dependant.security_requirements.append(security_requirement)

    return sub_dependant


def get_dependant(
    *,
    path: str,
    call: Callable[..., Any],
    name: Optional[str] = None,
    security_scopes: Optional[List[str]] = None,
    use_cache: bool = True,
) -> Dependant:
    """
    Build dependency graph for endpoint.

    Lambda-native version - no Request/Response/HTTPConnection injection.
    """
    path_param_names = get_path_param_names(path)
    endpoint_signature = get_typed_signature(call)
    signature_params = endpoint_signature.parameters

    dependant = Dependant(
        call=call,
        name=name,
        path=path,
        security_scopes=security_scopes,
        use_cache=use_cache,
    )

    for param_name, param in signature_params.items():
        is_path_param = param_name in path_param_names

        param_details = analyze_param(
            param_name=param_name,
            annotation=param.annotation,
            value=param.default,
            is_path_param=is_path_param,
        )

        if param_details.depends is not None:
            # Nested dependency
            sub_dependant = get_param_sub_dependant(
                param_name=param_name,
                depends=param_details.depends,
                path=path,
                security_scopes=security_scopes,
            )
            dependant.dependencies.append(sub_dependant)
            continue

        # Skip if field is None (LambdaRequest will be auto-injected)
        if param_details.field is None:
            continue

        if isinstance(param_details.field.field_info, params.Body):
            dependant.body_params.append(param_details.field)
        else:
            add_param_to_fields(field=param_details.field, dependant=dependant)

    return dependant


@dataclass
class SolvedDependency:
    """Result of dependency resolution."""

    values: Dict[str, Any]
    errors: List[Any]
    response: Optional[Any]  # LambdaResponse - using Any to avoid circular import
    dependency_cache: Dict[Tuple[Callable[..., Any], Tuple[str]], Any]


async def solve_dependencies(
    *,
    request: LambdaRequest,
    dependant: Dependant,
    body: Optional[Dict[str, Any]] = None,
    dependency_cache: Optional[Dict[Tuple[Callable[..., Any], Tuple[str]], Any]] = None,
    async_exit_stack: AsyncExitStack,
) -> SolvedDependency:
    """
    Solve dependencies from Lambda request.

    Simplified from ASGI version - no scope/receive/send, no Response injection.
    """
    values: Dict[str, Any] = {}
    errors: List[Any] = []

    if dependency_cache is None:
        dependency_cache = {}

    # Resolve sub-dependencies recursively
    for sub_dependant in dependant.dependencies:
        sub_dependant.call = cast(Callable[..., Any], sub_dependant.call)
        sub_dependant.cache_key = cast(Tuple[Callable[..., Any], Tuple[str]], sub_dependant.cache_key)
        call = sub_dependant.call

        # Recursive resolution
        solved_result = await solve_dependencies(
            request=request,
            dependant=sub_dependant,
            body=body,
            dependency_cache=dependency_cache,
            async_exit_stack=async_exit_stack,
        )

        if solved_result.errors:
            errors.extend(solved_result.errors)
            continue

        # Check cache
        if sub_dependant.use_cache and sub_dependant.cache_key in dependency_cache:
            solved = dependency_cache[sub_dependant.cache_key]
        elif is_gen_callable(call) or is_async_gen_callable(call):
            # Generator dependency (with yield)
            solved = await solve_generator(
                call=call, stack=async_exit_stack, sub_values=solved_result.values, request=request
            )
        elif is_coroutine_callable(call):
            # Auto-inject LambdaRequest if needed
            call_values = solved_result.values.copy()
            sig = inspect.signature(call)
            for param_name, param in sig.parameters.items():
                if param.annotation is LambdaRequest or (
                    hasattr(param.annotation, "__origin__") and param.annotation.__origin__ is LambdaRequest
                ):
                    call_values[param_name] = request

            # Async function
            solved = await call(**call_values)
        else:
            # Lambda-optimized: all dependencies must be async
            raise RuntimeError(f"Dependency {call} must be async (use 'async def')")

        if sub_dependant.name is not None:
            values[sub_dependant.name] = solved

        if sub_dependant.cache_key not in dependency_cache:
            dependency_cache[sub_dependant.cache_key] = solved

    # Extract path params
    path_values, path_errors = extract_params_from_dict(dependant.path_params, request.path_params)

    # Extract query params
    query_values, query_errors = extract_params_from_dict(dependant.query_params, request.query_params)

    # Extract headers
    header_values, header_errors = extract_params_from_dict(dependant.header_params, request.headers)

    values.update(path_values)
    values.update(query_values)
    values.update(header_values)
    errors += path_errors + query_errors + header_errors

    # Extract body params
    if dependant.body_params:
        body_values, body_errors = await extract_body_params(
            body_fields=dependant.body_params,
            received_body=body,
        )
        values.update(body_values)
        errors.extend(body_errors)

    return SolvedDependency(
        values=values,
        errors=errors,
        response=None,  # No Response injection in Lambda-native
        dependency_cache=dependency_cache,
    )


def _validate_value_with_model_field(
    *, field: ModelField, value: Any, values: Dict[str, Any], loc: Tuple[str, ...]
) -> Tuple[Any, List[Any]]:
    """Validate value with Pydantic field."""
    if value is None:
        if field.required:
            return None, [get_missing_field_error(loc=loc)]
        else:
            return deepcopy(field.default), []

    v_, errors_ = field.validate(value, values, loc=loc)

    if isinstance(errors_, ErrorWrapper):
        return None, [errors_]
    elif isinstance(errors_, list):
        new_errors = _regenerate_error_with_loc(errors=errors_, loc_prefix=())
        return None, new_errors
    else:
        return v_, []


def extract_params_from_dict(
    fields: List[ModelField],
    received_params: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Any]]:
    """
    Extract and validate parameters from dict.

    Simplified from ASGI version - works with plain dicts.
    """
    values: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []

    if not fields:
        return values, errors

    first_field = fields[0]

    # Single Pydantic model as param
    if len(fields) == 1 and lenient_issubclass(first_field.type_, BaseModel):
        from fastapi_lambda._compat import get_cached_model_fields

        fields_to_extract = get_cached_model_fields(first_field.type_)
        single_not_embedded_field = True
    else:
        fields_to_extract = fields
        single_not_embedded_field = False

    # Extract values
    params_to_process: Dict[str, Any] = {}

    for field in fields_to_extract:  # noqa: F402
        alias = field.alias
        value = received_params.get(alias) or received_params.get(field.name)

        if value is not None:
            params_to_process[field.name] = value

    if single_not_embedded_field:
        field_info = first_field.field_info
        assert isinstance(field_info, params.Param), "Params must be subclasses of Param"
        loc: Tuple[str, ...] = (field_info.in_.value,)
        v_, errors_ = _validate_value_with_model_field(
            field=first_field, value=params_to_process, values=values, loc=loc
        )
        return {first_field.name: v_}, errors_

    # Validate each field
    for field in fields:
        alias = field.alias
        value = received_params.get(alias) or received_params.get(field.name)

        field_info = field.field_info
        assert isinstance(field_info, params.Param), "Params must be subclasses of Param"
        loc = (field_info.in_.value, field.alias)

        v_, errors_ = _validate_value_with_model_field(field=field, value=value, values=values, loc=loc)

        if errors_:
            errors.extend(errors_)
        else:
            values[field.name] = v_

    return values, errors


async def extract_body_params(
    body_fields: List[ModelField],
    received_body: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extract and validate body parameters.

    Adapted from ASGI version for Lambda events.
    """
    values: Dict[str, Any] = {}
    errors: List[Dict[str, Any]] = []

    assert body_fields, "extract_body_params() should be called with fields"

    # Determine if body should be embedded
    embed_body_fields = _should_embed_body_fields(body_fields)
    single_not_embedded_field = len(body_fields) == 1 and not embed_body_fields
    first_field = body_fields[0]

    if single_not_embedded_field:
        loc: Tuple[str, ...] = ("body",)
        v_, errors_ = _validate_value_with_model_field(field=first_field, value=received_body, values=values, loc=loc)
        return {first_field.name: v_}, errors_

    # Multiple body fields - validate each
    for field in body_fields:  # noqa: F402
        loc = ("body", field.alias)
        value: Optional[Any] = None

        if received_body is not None:
            try:
                value = received_body.get(field.alias)
            except AttributeError:
                # Body is not a dict
                errors.append(get_missing_field_error(loc))
                continue

        v_, errors_ = _validate_value_with_model_field(field=field, value=value, values=values, loc=loc)

        if errors_:
            errors.extend(errors_)
        else:
            values[field.name] = v_

    return values, errors


def _should_embed_body_fields(fields: List[ModelField]) -> bool:
    """Check if body fields should be embedded."""
    if not fields:
        return False

    # Count unique field names
    body_param_names_set = {field.name for field in fields}

    # Multiple fields must be embedded
    if len(body_param_names_set) > 1:
        return True

    first_field = fields[0]

    # Check if explicitly marked as embed
    if getattr(first_field.field_info, "embed", None):
        return True

    return False

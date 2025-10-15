import warnings
from collections import deque
from copy import copy
from dataclasses import dataclass, is_dataclass
from functools import lru_cache
from typing import (
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from pydantic import BaseModel, TypeAdapter
from pydantic import ValidationError as ValidationError
from pydantic._internal._typing_extra import eval_type_lenient
from pydantic._internal._utils import lenient_issubclass as lenient_issubclass
from pydantic.fields import FieldInfo
from pydantic.json_schema import GenerateJsonSchema as GenerateJsonSchema
from pydantic.json_schema import JsonSchemaValue as JsonSchemaValue
from pydantic_core import PydanticUndefined, PydanticUndefinedType
from typing_extensions import Annotated, Literal, get_args, get_origin

from fastapi_lambda.types import ModelNameMap, UnionType

sequence_annotation_to_type = {
    Sequence: list,
    List: list,
    list: list,
    Tuple: tuple,
    tuple: tuple,
    Set: set,
    set: set,
    FrozenSet: frozenset,
    frozenset: frozenset,
    Deque: deque,
    deque: deque,
}

sequence_types = tuple(sequence_annotation_to_type.keys())


try:
    from pydantic_core.core_schema import (
        with_info_plain_validator_function as with_info_plain_validator_function,
    )
except ImportError:  # pragma: no cover
    from pydantic_core.core_schema import (  # noqa: F401
        general_plain_validator_function as with_info_plain_validator_function,
    )

RequiredParam = PydanticUndefined
Undefined = PydanticUndefined
UndefinedType = PydanticUndefinedType
evaluate_forwardref = eval_type_lenient
Validator = Any


class ErrorWrapper(Exception):
    pass


@dataclass
class ModelField:
    field_info: FieldInfo
    name: str
    mode: Literal["validation", "serialization"] = "validation"

    @property
    def alias(self) -> str:
        a = self.field_info.alias
        return a if a is not None else self.name

    @property
    def required(self) -> bool:
        return self.field_info.is_required()

    @property
    def type_(self) -> Any:
        return self.field_info.annotation

    @property
    def default(self) -> Any:
        """Get default value for field."""
        return self.get_default()

    def __post_init__(self) -> None:
        with warnings.catch_warnings():
            # Pydantic >= 2.12.0 warns about field specific metadata that is unused
            # (e.g. `TypeAdapter(Annotated[int, Field(alias='b')])`). In some cases, we
            # end up building the type adapter from a model field annotation so we
            # need to ignore the warning:
            try:
                from pydantic.warnings import (
                    UnsupportedFieldAttributeWarning,  # type: ignore[import]
                )

                warnings.simplefilter("ignore", category=UnsupportedFieldAttributeWarning)
            except ImportError:
                # Pydantic < 2.12.0 doesn't have this warning
                pass
            self._type_adapter: TypeAdapter[Any] = TypeAdapter(Annotated[self.field_info.annotation, self.field_info])

    def get_default(self) -> Any:
        if self.field_info.is_required():
            return Undefined
        return self.field_info.get_default(call_default_factory=True)

    def validate(
        self,
        value: Any,
        values: Dict[str, Any] = {},  # noqa: B006
        *,
        loc: Tuple[Union[int, str], ...] = (),
    ) -> Tuple[Any, Union[List[Dict[str, Any]], None]]:
        try:
            return (
                self._type_adapter.validate_python(value, from_attributes=True),
                None,
            )
        except ValidationError as exc:
            return None, _regenerate_error_with_loc(errors=exc.errors(include_url=False), loc_prefix=loc)

    def __hash__(self) -> int:
        # Each ModelField is unique for our purposes, to allow making a dict from
        # ModelField to its JSON Schema.
        return id(self)


def get_annotation_from_field_info(annotation: Any, field_info: FieldInfo) -> Any:
    return annotation


def _normalize_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
    return errors  # type: ignore[return-value]


def _model_dump(model: BaseModel, mode: Literal["json", "python"] = "json", **kwargs: Any) -> Any:
    return model.model_dump(mode=mode, **kwargs)


def get_schema_from_model_field(
    *,
    field: ModelField,
    schema_generator: GenerateJsonSchema,
    model_name_map: ModelNameMap,
    field_mapping: Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    separate_input_output_schemas: bool = True,
) -> Dict[str, Any]:
    override_mode: Union[Literal["validation"], None] = None if separate_input_output_schemas else "validation"
    # This expects that GenerateJsonSchema was already used to generate the definitions
    json_schema = field_mapping[(field, override_mode or field.mode)]
    if "$ref" not in json_schema:
        json_schema["title"] = field.field_info.title or field.alias.title().replace("_", " ")
    return json_schema


def get_compat_model_name_map(fields: List[ModelField]) -> ModelNameMap:
    return {}


def get_definitions(
    *,
    fields: List[ModelField],
    schema_generator: GenerateJsonSchema,
    model_name_map: ModelNameMap,
    separate_input_output_schemas: bool = True,
) -> Tuple[
    Dict[Tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    Dict[str, Dict[str, Any]],
]:
    override_mode: Union[Literal["validation"], None] = None if separate_input_output_schemas else "validation"
    inputs = [(field, override_mode or field.mode, field._type_adapter.core_schema) for field in fields]
    field_mapping, definitions = schema_generator.generate_definitions(inputs=inputs)  # type: ignore[assignment]
    for item_def in cast(Dict[str, Dict[str, Any]], definitions).values():
        if "description" in item_def:
            item_description = cast(str, item_def["description"]).split("\f")[0]
            item_def["description"] = item_description
    return field_mapping, definitions  # type: ignore[return-value]


def is_scalar_field(field: ModelField) -> bool:
    from fastapi_lambda import params

    return field_annotation_is_scalar(field.field_info.annotation) and not isinstance(field.field_info, params.Body)


def copy_field_info(*, field_info: FieldInfo, annotation: Any) -> FieldInfo:
    cls = type(field_info)
    merged_field_info = cls.from_annotation(annotation)
    new_field_info = copy(field_info)
    new_field_info.metadata = merged_field_info.metadata
    new_field_info.annotation = merged_field_info.annotation
    return new_field_info


def get_missing_field_error(loc: Tuple[str, ...]) -> Dict[str, Any]:
    error = ValidationError.from_exception_data(
        "Field required", [{"type": "missing", "loc": loc, "input": {}}]
    ).errors(include_url=False)[0]
    error["input"] = None
    return error  # type: ignore[return-value]


def get_model_fields(model: Type[BaseModel]) -> List[ModelField]:
    return [ModelField(field_info=field_info, name=name) for name, field_info in model.model_fields.items()]


# Pydantic v1 support removed - fastfn requires Pydantic v2 for Lambda optimization


def _regenerate_error_with_loc(
    *, errors: Sequence[Any], loc_prefix: Tuple[Union[str, int], ...]
) -> List[Dict[str, Any]]:
    updated_loc_errors: List[Any] = [
        {**err, "loc": loc_prefix + err.get("loc", ())} for err in _normalize_errors(errors)
    ]

    return updated_loc_errors


def _annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
    if lenient_issubclass(annotation, (str, bytes)):
        return False
    return lenient_issubclass(annotation, sequence_types)


def field_annotation_is_sequence(annotation: Union[Type[Any], None]) -> bool:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        for arg in get_args(annotation):
            if field_annotation_is_sequence(arg):
                return True
        return False
    return _annotation_is_sequence(annotation) or _annotation_is_sequence(get_origin(annotation))


def _annotation_is_complex(annotation: Union[Type[Any], None]) -> bool:
    return (
        lenient_issubclass(annotation, (BaseModel, Mapping))
        or _annotation_is_sequence(annotation)
        or is_dataclass(annotation)
    )


def field_annotation_is_complex(annotation: Union[Type[Any], None]) -> bool:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        return any(field_annotation_is_complex(arg) for arg in get_args(annotation))

    if origin is Annotated:
        return field_annotation_is_complex(get_args(annotation)[0])

    return (
        _annotation_is_complex(annotation)
        or _annotation_is_complex(origin)
        or hasattr(origin, "__pydantic_core_schema__")
        or hasattr(origin, "__get_pydantic_core_schema__")
    )


def field_annotation_is_scalar(annotation: Any) -> bool:
    # handle Ellipsis here to make tuple[int, ...] work nicely
    return annotation is Ellipsis or not field_annotation_is_complex(annotation)


@lru_cache
def get_cached_model_fields(model: Type[BaseModel]) -> List[ModelField]:
    return get_model_fields(model)

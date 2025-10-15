import re
from typing import Any, Dict, Optional, Set

from pydantic import PydanticSchemaGenerationError
from pydantic.fields import FieldInfo
from typing_extensions import Literal

import fastapi_lambda
from fastapi_lambda._compat import ModelField, Undefined, Validator


def get_path_param_names(path: str) -> Set[str]:
    return set(re.findall("{(.*?)}", path))


def create_model_field(
    name: str,
    type_: Any,
    class_validators: Optional[Dict[str, Validator]] = None,
    default: Optional[Any] = Undefined,
    field_info: Optional[FieldInfo] = None,
    alias: Optional[str] = None,
    mode: Literal["validation", "serialization"] = "validation",
) -> ModelField:
    class_validators = class_validators or {}
    field_info = field_info or FieldInfo(annotation=type_, default=default, alias=alias)
    kwargs = {"name": name, "field_info": field_info}
    kwargs.update({"mode": mode})
    try:
        return ModelField(**kwargs)  # type: ignore[arg-type]
    except (RuntimeError, PydanticSchemaGenerationError):
        raise fastapi_lambda.exceptions.FastAPIError(
            "Invalid args for response field! Hint: "
            f"check that {type_} is a valid Pydantic field type. "
            "If you are using a return type annotation that is not a valid Pydantic "
            "field (e.g. Union[Response, dict, None]) you can disable generating the "
            "response model from the type annotation with the path operation decorator "
            "parameter response_model=None. Read more: "
            "https://fastapi.tiangolo.com/tutorial/response-model/"
        ) from None


def deep_dict_update(main_dict: Dict[Any, Any], update_dict: Dict[Any, Any]) -> None:
    for key, value in update_dict.items():
        if key in main_dict and isinstance(main_dict[key], dict) and isinstance(value, dict):
            deep_dict_update(main_dict[key], value)
        elif key in main_dict and isinstance(main_dict[key], list) and isinstance(update_dict[key], list):
            main_dict[key] = main_dict[key] + update_dict[key]
        else:
            main_dict[key] = value

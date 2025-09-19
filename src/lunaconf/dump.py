import json
import math
from typing import Any

import toml

from lunaconf.config_base import LunaConf


def _handle_special_values_dump_json(obj: dict[str, Any] | list[Any]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, float):
                if math.isnan(v):
                    obj[k] = "<nan>"
                elif v == float("inf"):
                    obj[k] = "<inf>"
                elif v == float("-inf"):
                    obj[k] = "<-inf>"
            elif isinstance(v, (list, dict)):
                _handle_special_values_dump_json(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, float):
                if math.isnan(v):
                    obj[i] = "<nan>"
                elif v == float("inf"):
                    obj[i] = "<inf>"
                elif v == float("-inf"):
                    obj[i] = "<-inf>"
            elif isinstance(v, (list, dict)):
                _handle_special_values_dump_json(v)
    else:
        raise TypeError(f"Expected dict or list but got {type(obj)}")


def lunaconf_dumps_json(
    config: LunaConf,
    indent: int = 2,
    **kwargs,
) -> str:
    dump_dict = config.model_dump(**kwargs)
    _handle_special_values_dump_json(dump_dict)
    return json.dumps(
        dump_dict,
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
    )


def _handle_special_values_dump_toml(obj: dict[str, Any] | list[Any]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None:
                obj[k] = "<null>"
            elif isinstance(v, (list, dict)):
                _handle_special_values_dump_toml(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if v is None:
                obj[i] = "<null>"
            elif isinstance(v, (list, dict)):
                _handle_special_values_dump_toml(v)
    else:
        raise TypeError(f"Expected dict or list but got {type(obj)}")


def lunaconf_dumps_toml(
    config: LunaConf,
    **kwargs,
) -> str:
    dump_dict = config.model_dump(**kwargs)
    _handle_special_values_dump_toml(dump_dict)
    return toml.dumps(dump_dict)

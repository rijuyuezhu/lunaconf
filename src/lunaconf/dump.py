import json
import math
from typing import Any

import toml

from lunaconf.config_base import LunaConf


def _fix_null_values_in_json(d: dict[str, Any] | list[Any]) -> None:
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, float):
                if math.isnan(v):
                    d[k] = "<nan>"
                elif v == float("inf"):
                    d[k] = "<inf>"
                elif v == float("-inf"):
                    d[k] = "<-inf>"
            elif isinstance(v, (list, dict)):
                _fix_null_values_in_json(v)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if isinstance(v, float):
                if math.isnan(v):
                    d[i] = "<nan>"
                elif v == float("inf"):
                    d[i] = "<inf>"
                elif v == float("-inf"):
                    d[i] = "<-inf>"
            elif isinstance(v, (list, dict)):
                _fix_null_values_in_json(v)
    else:
        raise TypeError(f"Expected dict or list but got {type(d)}")


def lunaconf_dumps_json(
    config: LunaConf,
    indent: int = 2,
    **kwargs,
) -> str:
    dump_dict = config.model_dump(**kwargs)
    _fix_null_values_in_json(dump_dict)
    return json.dumps(
        dump_dict,
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
    )


def _fix_null_values_in_toml(d: dict[str, Any] | list[Any]) -> None:
    if isinstance(d, dict):
        for k, v in d.items():
            if v is None:
                d[k] = "<null>"
            elif isinstance(v, (list, dict)):
                _fix_null_values_in_toml(v)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if v is None:
                d[i] = "<null>"
            elif isinstance(v, (list, dict)):
                _fix_null_values_in_toml(v)
    else:
        raise TypeError(f"Expected dict or list but got {type(d)}")


def lunaconf_dumps_toml(
    config: LunaConf,
    **kwargs,
) -> str:
    dump_dict = config.model_dump(**kwargs)
    _fix_null_values_in_toml(dump_dict)
    return toml.dumps(dump_dict)

import argparse
import json
from collections.abc import Sequence
from typing import Any, Callable, Literal, TypeAlias, TypeVar

import toml

from lunaconf.config_base import LunaConf
from lunaconf.dump import lunaconf_dumps_json, lunaconf_dumps_toml

_DEL_OBJ = object()


def adjust_conf(
    now: list[Any] | dict[str, Any] | None,
    keys: list[str],
    value: Any,
) -> list[Any] | dict[str, Any]:
    if len(keys) == 0:
        raise ValueError("Keys cannot be empty")
    key = keys[0]
    if len(keys) == 1:
        if key.isdigit():
            if now is None or not isinstance(now, list):
                now = []
            index = int(key)
            if value is _DEL_OBJ:
                if index < len(now):
                    del now[index]
            else:
                if index >= len(now):
                    # fill with None
                    now.extend([None] * (index - len(now) + 1))
                now[index] = value
        elif key.isidentifier():
            if now is None or not isinstance(now, dict):
                now = {}
            if value is _DEL_OBJ:
                if key in now:
                    del now[key]
            else:
                now[key] = value
        else:
            raise TypeError(f"Cannot set value for key '{key}' in {type(now)}")
    else:
        if key.isdigit():
            if now is None or not isinstance(now, list):
                now = []
            index = int(key)
            if index >= len(now):
                # fill with None
                now.extend([None] * (index - len(now) + 1))
            now[index] = adjust_conf(now[index], keys[1:], value)
        elif key.isidentifier():
            if now is None or not isinstance(now, dict):
                now = {}
            if key not in now:
                now[key] = None
            now[key] = adjust_conf(now[key], keys[1:], value)
        else:
            raise TypeError(f"Cannot set value for key '{key}' in {type(now)}")
    return now


def _handle_special_values(obj: Any) -> Any:
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = _handle_special_values(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _handle_special_values(v)
    elif isinstance(obj, str):
        match obj.lower():
            case "<null>":
                return None
            case "<del>":
                return _DEL_OBJ
            case "<inf>":
                return float("inf")
            case "<-inf>":
                return float("-inf")
            case "<nan>":
                return float("nan")
        objl = obj.lower()
        if objl.startswith("<env:") and objl.endswith(">"):
            env_var = obj[5:-1]
            import os

            res = os.getenv(env_var)
            if res is None:
                raise ValueError(f"Environment variable '{env_var}' is not set")
            return res
        if objl.startswith("<envint:") and objl.endswith(">"):
            env_var = obj[8:-1]
            import os

            res = os.getenv(env_var)
            if res is None:
                raise ValueError(f"Environment variable '{env_var}' is not set")
            try:
                return int(res)
            except ValueError as e:
                raise ValueError(
                    f"Environment variable '{env_var}' cannot be converted to int"
                ) from e
    return obj


def _parse_command_value(value_str: str) -> Any:
    def parse_inner(value_str: str) -> Any:
        try:
            return json.loads(value_str)
        except (TypeError, json.JSONDecodeError):
            pass

        if value_str.startswith("[") and value_str.endswith("]"):
            # add support for json format with list as the top level
            try:
                return json.loads(f'{{"object": {value_str}}}')["object"]
            except (TypeError, json.JSONDecodeError):
                pass
        return value_str

    return _handle_special_values(parse_inner(value_str))


def adjust_conf_command(config_dict: dict[str, Any], cmdline: str) -> None:
    for cmd in (s.strip() for s in cmdline.split(";")):
        if cmd.count("=") != 1:
            raise ValueError(f"Invalid command format: {cmd}")
        key_str, value_str = (s.strip() for s in cmd.split("="))
        keys = [s.strip() for s in key_str.split(".")]

        value = _parse_command_value(value_str)

        adjust_conf(config_dict, keys, value)


def adjust_conf_command_file(config_dict: dict[str, Any], filepath: str) -> None:
    args: list[str] = []

    with open(filepath) as f:
        lines = f.readlines()

    for line in lines:
        line = line.split("#", maxsplit=1)[0].strip()
        if not line:
            continue
        if line.startswith("-"):
            args.extend(line.split(maxsplit=1))
        else:
            args.append(line)
    lunaconf_gendict(config_dict, args)


def adjust_conf_multilevel_data_structure(
    config_dict: dict[str, Any],
    obj: dict[str, Any] | list[Any],
    prefix: list[str] | None = None,
) -> None:
    def adjust_inner(
        config_dict: dict[str, Any],
        obj: dict[str, Any] | list[Any],
        prefix: list[str] | None = None,
    ) -> None:
        if prefix is None:
            prefix = []
        if isinstance(obj, dict):
            if len(obj) == 0:
                adjust_conf(config_dict, prefix, {})
            else:
                for k, v in obj.items():
                    prefix.append(k)
                    if isinstance(v, (dict, list)):
                        adjust_inner(config_dict, v, prefix)
                    else:
                        adjust_conf(config_dict, prefix, v)
                    prefix.pop()
        elif isinstance(obj, list):
            if len(obj) == 0:
                adjust_conf(config_dict, prefix, [])
            else:
                for i, v in enumerate(obj):
                    prefix.append(str(i))
                    if isinstance(v, (dict, list)):
                        adjust_inner(config_dict, v, prefix)
                    else:
                        adjust_conf(config_dict, prefix, v)
                    prefix.pop()
        else:
            raise TypeError(f"Expected dict or list but got {type(obj)}")

    obj = _handle_special_values(obj)
    adjust_inner(config_dict, obj, prefix)


_AvaliTag: TypeAlias = Literal[
    "command",
    "command-file",
    "json",
    "json-file",
    "toml",
    "toml-file",
    "detect",
    "detect-file",
]


def _extend_action_with_tag(tag: _AvaliTag) -> type[argparse.Action]:
    class ExtendActionWithTag(argparse._ExtendAction):
        def __call__(self, parser, namespace, values, option_string=None):
            fix_values = [(tag, v) for v in values]  # type: ignore
            super().__call__(parser, namespace, fix_values, option_string)

    return ExtendActionWithTag


def _append_action_with_tag(tag: _AvaliTag) -> type[argparse.Action]:
    class AppendActionWithTag(argparse._AppendAction):
        def __call__(self, parser, namespace, values, option_string=None):
            fix_v = (tag, values)  # type: ignore
            super().__call__(parser, namespace, fix_v, option_string)

    return AppendActionWithTag


T = TypeVar("T", bound=LunaConf)


def lunaconf_gendict(
    config_dict: dict[str, Any],
    args: Sequence[str] | None = None,
    *,
    parser: argparse.ArgumentParser | None = None,
) -> argparse.Namespace:
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        type=str,
        nargs="*",
        action=_extend_action_with_tag("command"),
        help="Command to adjust configuration, of the format `key1.key2=value1; key3.key4=value2`",
    )
    parser.add_argument(
        "-C",
        "--command-file",
        dest="command",
        type=str,
        action=_append_action_with_tag("command-file"),
        help="Command file to adjust configuration, with content that serves as command line arguments",
    )
    parser.add_argument(
        "-j",
        "--json",
        dest="command",
        type=str,
        action=_append_action_with_tag("json"),
        help="String in JSON format, used to overload the default configuration",
    )
    parser.add_argument(
        "-J",
        "--json-file",
        dest="command",
        type=str,
        action=_append_action_with_tag("json-file"),
        help="Path to the configuration file in JSON format, used to overload the default configuration",
    )
    parser.add_argument(
        "-t",
        "--toml",
        dest="command",
        type=str,
        action=_append_action_with_tag("toml"),
        help="String in TOML format, used to overload the default configuration",
    )
    parser.add_argument(
        "-T",
        "--toml-file",
        dest="command",
        type=str,
        action=_append_action_with_tag("toml-file"),
        help="Path to the configuration file in TOML format, used to overload the default configuration",
    )
    parser.add_argument(
        "-d",
        "--detect",
        dest="command",
        type=str,
        action=_append_action_with_tag("detect"),
        help="Detect the format of the string and parse it accordingly",
    )
    parser.add_argument(
        "-D",
        "--detect-file",
        dest="command",
        type=str,
        action=_append_action_with_tag("detect-file"),
        help="Detect the format of the file and parse it accordingly",
    )

    argspace = parser.parse_args(args)
    command: list[tuple[_AvaliTag, str]] = argspace.command or []

    for tag, arg in command:
        match tag:
            case "command":
                adjust_conf_command(config_dict, arg)
            case "command-file":
                adjust_conf_command_file(config_dict, arg)
            case "json" | "json-file":
                if tag == "json-file":
                    with open(arg) as f:
                        arg = f.read()
                d = json.loads(arg)
                adjust_conf_multilevel_data_structure(config_dict, d)
            case "toml" | "toml-file":
                if tag == "toml-file":
                    with open(arg) as f:
                        arg = f.read()
                d = toml.loads(arg)
                adjust_conf_multilevel_data_structure(config_dict, d)
            case "detect" | "detect-file":
                if tag == "detect-file":
                    with open(arg) as f:
                        arg = f.read()
                try:
                    d = json.loads(arg)
                except (TypeError, json.JSONDecodeError):
                    try:
                        d = toml.loads(arg)
                    except toml.TomlDecodeError:
                        raise ValueError("Cannot detect the format of the string")
                adjust_conf_multilevel_data_structure(config_dict, d)
            case _:
                raise ValueError(f"Unknown tag: {tag}")
    return argspace


def lunaconf_cli(
    cls: type[T],
    args: Sequence[str] | None = None,
    *,
    init_from_defaults: bool = True,
    description: str = "Generate configuration",
    post_action_with_all: Callable[[T], None] = lambda _: None,
    post_action_without_all: Callable[[T], None] = lambda _: None,
) -> T:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Print all fields instead of only the non-default ones",
    )
    parser.add_argument(
        "-p",
        "--print-json",
        action="store_true",
        help="Print the generated configuration in JSON format and exit",
    )
    parser.add_argument(
        "--json-indent",
        type=int,
        default=2,
        help="Indentation level for JSON output (default: 2)",
    )
    parser.add_argument(
        "-P",
        "--print-toml",
        action="store_true",
        help="Print the generated configuration in TOML format and exit",
    )
    config_dict: dict[str, Any]
    if init_from_defaults:
        config_dict = cls.__lunaconf_default__().model_dump()
    else:
        config_dict = {}

    argspace = lunaconf_gendict(
        config_dict,
        args,
        parser=parser,
    )

    config = cls.model_validate(config_dict)

    if argspace.all:
        post_action_with_all(config)
    else:
        post_action_without_all(config)

    if argspace.print_json:
        print(
            lunaconf_dumps_json(
                config,
                indent=argspace.json_indent,
                exclude_defaults=not argspace.all,
            )
        )
        exit(0)
    elif argspace.print_toml:
        print(
            lunaconf_dumps_toml(
                config,
                exclude_defaults=not argspace.all,
            )
        )
        exit(0)
    return config

import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import argparse

from lunaconf.config_base import LunaConf


def adjust_conf(
    now: Union[List[Any], Dict[str, Any], None], keys: List[str], value: Any
) -> Union[List[Any], Dict[str, Any]]:
    if not keys:
        raise ValueError("Keys cannot be empty")
    key = keys[0]
    if len(keys) == 1:
        if key.isdigit():
            if now is None:
                now = []
            if not isinstance(now, list):
                raise TypeError(f"Expected list but got {type(now)}")
            index = int(key)
            if value is None:
                if index < len(now):
                    del now[index]
            else:
                if index >= len(now):
                    # fill with None
                    now.extend([None] * (index - len(now) + 1))
                now[index] = value
        elif key.isidentifier():
            if now is None:
                now = {}
            if not isinstance(now, dict):
                raise TypeError(f"Expected dict but got {type(now)}")
            now[key] = value
        else:
            raise TypeError(f"Cannot set value for key '{key}' in {type(now)}")
    else:
        if key.isdigit():
            if now is None:
                now = []
            if not isinstance(now, list):
                raise TypeError(f"Expected list but got {type(now)}")
            index = int(key)
            if value is None:
                if index < len(now):
                    del now[index]
            else:
                if index >= len(now):
                    # fill with None
                    now.extend([None] * (index - len(now) + 1))
            now[index] = adjust_conf(now[index], keys[1:], value)
        elif key.isidentifier():
            if now is None:
                now = {}
            if not isinstance(now, dict):
                raise TypeError(f"Expected dict but got {type(now)}")
            now[key] = adjust_conf(now[key], keys[1:], value)
        else:
            raise TypeError(f"Cannot set value for key '{key}' in {type(now)}")
    return now


def adjust_conf_str(config_dict: Dict[str, Any], cmdline: str) -> None:
    for cmd in (s.strip() for s in cmdline.split(";")):
        if cmd.count("=") != 1:
            raise ValueError(f"Invalid command format: {cmd}")
        key_str, value_str = (s.strip() for s in cmd.split("="))
        keys = [s.strip() for s in key_str.split(".")]

        try:
            value = json.loads(value_str)
        except (TypeError, json.JSONDecodeError):
            if value_str.startswith("[") and value_str.endswith("]"):
                # add support for json format with list the top level
                try:
                    value = json.loads(f'{{"object": {value_str}}}')["object"]
                except json.JSONDecodeError:
                    value = value_str
            else:
                value = value_str

        adjust_conf(config_dict, keys, value)


def extend_action_with_tag(tag: str) -> Type[argparse.Action]:
    class ExtendActionWithTag(argparse._ExtendAction):
        def __call__(self, parser, namespace, values, option_string=None):
            fix_values = [(tag, v) for v in values]  # type: ignore
            super().__call__(parser, namespace, fix_values, option_string)

    return ExtendActionWithTag


T = TypeVar("T", bound=LunaConf)


def lunaconf_cli(
    cls: Type[T],
    args: Optional[Sequence[str]] = None,
    *,
    description: str = "Generate configuration",
    indent: int = 2,
    post_action_with_all: Callable[[T], None] = lambda _: None,
    post_action_without_all: Callable[[T], None] = lambda _: None,
) -> T:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "command_list",
        type=str,
        nargs="*",
        action=extend_action_with_tag("str"),
        help="Command to adjust configuration, of the format `key1.key2=value1; key3.key4=value2`",
    )
    parser.add_argument(
        "-j",
        "--json",
        type=str,
        nargs="?",
        help="Path to the configuration file in JSON format. Use default config if not given",
    )
    parser.add_argument(
        "-f",
        "--command-file",
        dest="command_list",
        type=str,
        nargs="*",
        action=extend_action_with_tag("file"),
        help="Command file to adjust configuration, with content of the format `key1.key2=value1; key3.key4=value2`",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Initialize the configuration with all default values",
    )
    parser.add_argument(
        "-p",
        "--print-json",
        action="store_true",
        help="Print the generated configuration and exit",
    )

    argspace = parser.parse_args(args)

    config_dict: Dict[str, Any]

    if argspace.json:
        with open(argspace.json) as f:
            config_dict = json.load(f)
    else:
        config_dict = cls.__lunaconf_default__().model_dump()

    command_list: List[Tuple[str, str]] = argspace.command_list or []

    for tag, cmd in command_list:
        if tag == "str":
            adjust_conf_str(config_dict, cmd)
        elif tag == "file":
            with open(cmd) as f:
                for line in map(str.strip, f.readlines()):
                    if line and not line.startswith("#"):
                        adjust_conf_str(config_dict, line)

    config = cls.model_validate(config_dict)

    if argspace.all:
        post_action_with_all(config)
    else:
        post_action_without_all(config)

    if argspace.print_json:
        print(
            config.model_dump_json(
                indent=indent,
                exclude_defaults=not argspace.all,
            )
        )
        exit(0)

    return config

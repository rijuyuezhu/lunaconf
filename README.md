# LunaConf

LunaConf is a configuration management CLI for scientific experiments.

# Installation

```
pip install lunaconf
```

# Usage

It provides the following interfaces:

- `lunaconf.LunaConf`: A base class that every configuration class should inherit from. It is a subclass of `pydantic.BaseModel` and thus pydantic features can be used.

  ```python
  import typing, lunaconf, pydantic

  class Config(lunaconf.LunaConf):
      require: int
      opt_int: int = 10
      opt_str: str = "default"
      opt_list: List[int] = pydantic.Field(default_factory=lambda: [1, 2, 3])

      @classmethod
      def __lunaconf_default__(cls) -> typing.Self:
          return cls(require=42)
  ```

  Here `__lunaconf_default__` is a class method that shall be overloaded if the class has required fields. It should return a default instance of the class to set default values for the fields.

- `lunaconf.lunaconf_cli`: Load the configuration from CLI in the JSON file or default values, then using CLI to modify them.

  ```python
  # example.py
  import lunaconf

  config = lunaconf.lunaconf_cli(Config)
  ```

  Some CLI arguments and their corresponding generated configuration are as follows.

  ```bash
  $ python3 example.py
  # Config(require=42, opt_int=10, opt_str='default', opt_list=[1, 2, 3])

  $ python3 example.py -j config.json    # suppose config.json contains {"require": 100}
  # Config(require=100, opt_int=10, opt_str='default', opt_list=[1, 2, 3])

  $ python3 example.py opt_int=233
  # Config(require=42, opt_int=233, opt_str='default', opt_list=[1, 2, 3])

  $ python3 example.py opt_list.0=4
  # Config(require=42, opt_int=10, opt_str='default', opt_list=[4, 2, 3])
  ```

  The `.` in the CLI modifications can be used by nested fields and list indices:

  ```python
  # config
  class Inner(lunaconf.LunaConf):
      a: int = 1
  class Outer(lunaconf.LunaConf):
      inner: typing.Optional[Inner] = None
      lst: List[int] = lunaconf.Field(default_factory=lambda: [1, 2, 3])
  ```

  ```bash
  $ python3 example.py
  # Outer(inner=None, lst=[1, 2, 3])
  $ python3 example.py inner.a=10 lst.1=20
  # Outer(inner=Inner(a=10), lst=[1, 20, 3])
  ```

  All different command
  - `-j/--json <file>`: specify the JSON file to load the configuration. If not specified, the default configuration will be used
  - `command_list` positional arguments: specify the modifications to the configuration in the form of `key1.key2=value1; key3.key4=value2` etc. The `.` can be used to access nested fields and list indices
  - `-f/--file <file>`: just like the above `command_list` arguments, but load commands from a file
  - `-a/--all`: whether or not output all fields with `-p/--print-json` flags, and also affect the application of `post_action_with_all` or `post_action_without_all` callables passed to `lunaconf_cli`
  - `-p/--print-json [file]`: print the final configuration in JSON then exit

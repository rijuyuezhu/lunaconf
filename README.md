# lunaconf

lunaconf is a Python library to support easy-to-understand configuration for evaluations

# Installation

```bash
pip install lunaconf
```

# Usage

It provides the following interfaces:

- `lunaconf.LunaConf`: A base class that every configuration class should inherit from. It is a subclass of `pydantic.BaseModel` and thus Pydantic features can be used.

  ```python
  import typing, lunaconf, pydantic

  class Config(lunaconf.LunaConf):
      require: int
      opt_int: int = 10
      opt_str: str = "default"
      opt_list: list[int] = pydantic.Field(default_factory=lambda: [1, 2, 3])

      @classmethod
      def __lunaconf_default__(cls) -> typing.Self:
          return cls(require=42)
  ```

  Here `__lunaconf_default__` is a class method that should be overloaded if the class has required fields. It should return a default instance of the class to set default values for the fields.

- `lunaconf.lunaconf_cli`: Construct a configuration from the CLI.

  ```python
  # example.py
  import lunaconf

  config = lunaconf.lunaconf_cli(Config)
  ```

  Some CLI arguments and their corresponding generated configurations are as follows.

  ```bash
  $ python3 example.py
  # Config(require=42, opt_int=10, opt_str='default', opt_list=[1, 2, 3])

  $ python3 example.py -J config.json    # suppose config.json contains {"require": 100}
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
      lst: list[int] = lunaconf.Field(default_factory=lambda: [1, 2, 3])
  ```

  ```bash
  $ python3 example.py
  # Outer(inner=None, lst=[1, 2, 3])
  $ python3 example.py inner.a=10 lst.1=20
  # Outer(inner=Inner(a=10), lst=[1, 20, 3])
  ```

  Available command-line options:
  - `command` positional arguments: specify the modifications to the configuration in the form of `key1.key2=value1; key3.key4=value2` etc. The `.` can be used to access nested fields and list indices.
  - `-j <json_str> / -J <json_file>`: specify the JSON to overload the configuration.
  - `-t <toml_str> / -T <toml_file>`: specify the TOML to overload the configuration.
  - `-d <str> / -D <file>`: detect the format of the string/file and parse it accordingly. It will first try to parse it as JSON, if it fails, it will try to parse it as TOML. If both fail, an error will be raised.
  - `-C <file>`: the extra configuration file. This file contains command line arguments (one group per line) that will be parsed interleaved with the other command line arguments. Lines starting with `#` are treated as comments and ignored.
  - `-a`: whether or not output all fields with `-p / -P` flags, and also affect the application of `post_action_with_all` or `post_action_without_all` callables passed to `lunaconf_cli`.
  - `-p`: print the final configuration in JSON and exit.
  - `-P`: print the final configuration in TOML and exit.

## Special Values
The following special values can be used in the command line arguments to represent certain Python values, and are output in some cases for unsupported values in JSON/TOML:

- Input `<null>` leads to `None`; TOML will output `<null>` for `None`.
- Input `<del>` to delete element in an array, or reset the field to its default.
- Input `<inf>`, `<-inf>`, `<nan>` lead to `float('inf')`, `float('-inf')`, `float('nan')` respectively; JSON will output `<inf>`, `<-inf>`, `<nan>` for these values.
- Input `<env:VAR_NAME>` leads to the value of the environment variable `VAR_NAME`. An error is raised if the environment variable is not set. `<envint:VAR_NAME>` is similar but converts the value to an integer, and raises an error if the conversion fails.

Strings inside the angle brackets are case-insensitive.

# Examples

For more examples, please refer to the unit tests in the `tests` folder.
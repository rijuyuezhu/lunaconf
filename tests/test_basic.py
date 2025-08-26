from typing import Optional, Self, List

from pydantic import Field

import lunaconf
import multiprocessing as mp

def test_simple():
    class Conf(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
    args = []
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert conf.param1 == 42
    assert conf.param2 == "hello"

def test_modify():
    class Conf(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
        param3: Optional[int] = None
    args = ["param3=233", "param1=32;param2=what"]
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert conf.param1 == 32
    assert conf.param2 == "what"
    assert conf.param3 == 233

def test_multilevel():
    class ConfInner(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
        param3: Optional[int] = None
    class Conf(lunaconf.LunaConf):
        inner: ConfInner
        @classmethod
        def __lunaconf_default__(cls) -> Self:
            return cls(inner=ConfInner())

    args = ["inner.param1=32"]
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert conf.inner.param1 == 32

def test_list():
    class ConfInner(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
        param3: Optional[int] = None
    class Conf(lunaconf.LunaConf):
        inner: List[ConfInner] = Field(default_factory=list)

    args = ["inner.0.param1=32"]
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert len(conf.inner) == 1
    assert conf.inner[0].param1 == 32

def test_multilevel_list():
    class ConfInner(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
        param3: Optional[int] = None
    class Conf(lunaconf.LunaConf):
        inner: List[List[ConfInner]] = Field(default_factory=list)

    args = []
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert len(conf.inner) == 0

    args = ["inner.0.0.param1=32"]
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert len(conf.inner) == 1
    assert len(conf.inner[0]) == 1
    assert conf.inner[0][0].param1 == 32

def test_optional_field():
    class ConfInner(lunaconf.LunaConf):
        param1: int = 42
        param2: str = "hello"
        param3: Optional[int] = None
    class Conf(lunaconf.LunaConf):
        inner: Optional[ConfInner] = None

    args = []
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert conf.inner is None

    args = ["inner.param1=32"]
    conf = lunaconf.lunaconf_cli(Conf, args)
    assert conf.inner is not None
    assert conf.inner.param1 == 32

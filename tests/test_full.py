import tempfile

from lunaconf import LunaConf, lunaconf_cli
from pydantic import Field

from typing import Self


def gen_tf(content: str) -> str:
    tf = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
    tf.write(content)
    tf.close()
    return tf.name


class TagConf(LunaConf):
    k: str
    v: str

    @classmethod
    def __lunaconf_default__(cls) -> Self:
        return cls(k="default_key", v="default_value")


class FullConf(LunaConf):
    name: str
    age: int = 18
    tags: list[TagConf] = Field(default_factory=list)

    @classmethod
    def __lunaconf_default__(cls) -> Self:
        return cls(
            name="default_name",
            age=20,
            tags=[TagConf.__lunaconf_default__()],
        )


def test_json():
    j = """\
{
    "name": "default_name",
    "age": 20,
    "tags": [
        {
            "k": "default_key",
            "v": "default_value"
        }
    ]
}
"""
    expected = FullConf(
        name="default_name",
        age=20,
        tags=[TagConf(k="default_key", v="default_value")],
    )
    f = gen_tf(j)
    args = ["-j", j]
    conf = lunaconf_cli(FullConf, args)
    assert conf == expected
    args = ["-J", f]
    conf = lunaconf_cli(FullConf, args)
    assert conf == expected


def test_toml():
    t = """\
name = "default_name"
age = 20
[[tags]]
k = "default_key"
v = "default_value"
[[tags]]
k = "another_key"
v = "another_value"
"""
    expected = FullConf(
        name="default_name",
        age=20,
        tags=[
            TagConf(k="default_key", v="default_value"),
            TagConf(k="another_key", v="another_value"),
        ],
    )
    f = gen_tf(t)
    args = ["-t", t]
    conf = lunaconf_cli(FullConf, args)
    assert conf == expected
    args = ["-T", f]
    conf = lunaconf_cli(FullConf, args)
    assert conf == expected


def test_commands():
    patch1 = gen_tf(
        """\
name=what; age=200
tags.0.k=key1; tags.0.v=value1
"""
    )
    patch2 = gen_tf(
        """\
{
    "name": "another_name"
}
"""
    )
    patch3 = gen_tf(
        """\
age = 40
"""
    )
    argfile = gen_tf(
        f"""\
-C {patch1}
-J {patch2}
-T {patch3}
tags.0.k=what
"""
    )
    args = ["-C", argfile]
    conf = lunaconf_cli(FullConf, args)
    expected = FullConf(
        name="another_name",
        age=40,
        tags=[TagConf(k="what", v="value1")],
    )
    assert conf == expected

from typing import Self

from pydantic import BaseModel


class LunaConf(BaseModel):
    """The base class for all configurations."""

    @classmethod
    def __lunaconf_default__(cls) -> Self:
        return cls()

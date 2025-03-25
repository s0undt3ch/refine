"""
Abstract base classes for defining codemod types and their configurations.
"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar
from typing import Generic
from typing import TypeVar

from libcst.codemod import CodemodContext
from libcst.codemod import VisitorBasedCodemodCommand
from pydantic import BaseModel
from pydantic import ConfigDict


class BaseConfig(BaseModel):
    """
    Base configuration class for codemoders.
    """

    model_config = ConfigDict(frozen=True)


CodemodConfigType = TypeVar("CodemodConfigType", bound=BaseConfig)


class BaseCodemod(VisitorBasedCodemodCommand, ABC, Generic[CodemodConfigType]):
    """
    Base class for codemoders.
    """

    NAME: ClassVar[str]
    CONFIG_CLS: ClassVar[type[BaseConfig]]
    PRIORITY: ClassVar[int] = 0

    def __init__(self, context: CodemodContext, config: CodemodConfigType):
        super().__init__(context)
        self.config = config
        self.__post_codemod_init__()

    def __post_codemod_init__(self) -> None:
        """
        This method can implement additional codemod initialization.
        """


CodemodType = TypeVar("CodemodType", bound=BaseCodemod)

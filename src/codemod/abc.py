"""
Abstract base classes for defining codemod types and their configurations.
"""

from abc import ABC
from abc import abstractmethod
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


C = TypeVar("C", bound=BaseConfig)


class BaseCodemod(VisitorBasedCodemodCommand, ABC, Generic[C]):
    """
    Base class for codemoders.
    """

    @property
    @abstractmethod
    def NAME(self) -> str:  # noqa: N802
        """
        Enforce `NAME` to be defined in subclasses and flagged by mypy.
        """

    @property
    @abstractmethod
    def CONFIG_CLS(self) -> type[C]:  # noqa: N802
        """
        Enforce `CONFIG_CLS` to be defined in subclasses and flagged by mypy.
        """

    def __init__(self, context: CodemodContext, config: C):
        super().__init__(context)
        self.config = config
        self.__post_codemod_init__()

    def __post_codemod_init__(self) -> None:
        """
        This method can implement additional codemod initialization.
        """


CodemodType = TypeVar("CodemodType", bound=BaseCodemod)

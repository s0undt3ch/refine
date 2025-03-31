"""
Abstract base classes for defining codemod types and their configurations.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING
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

    @classmethod
    def get_short_description(cls) -> str:
        """
        Return a short description of the codemod.

        This short description is used in the CLI to list available codemods and should be a single line.

        By default, it returns the first line of the class docstring, override this method to provide a
        custom description.
        """
        doc = cls.__doc__
        if cls is None:
            error_msg = f"Codemod {cls.__name__} must have a docstring to be used in the CLI."
            raise TypeError(error_msg)
        if TYPE_CHECKING:
            assert doc is not None
        return doc.strip().splitlines()[0].strip()


CodemodType = TypeVar("CodemodType", bound=BaseCodemod)

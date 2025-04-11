"""
Abstract base classes for defining codemod types and their configurations.
"""

from __future__ import annotations

import fnmatch
import inspect
from abc import ABC
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar
from typing import Generic
from typing import Self
from typing import TypeAlias
from typing import TypeVar

import libcst as cst
import libcst.matchers as m
import msgspec
from libcst import MetadataDependent
from libcst.codemod import CodemodContext
from libcst.codemod import SkipFile
from libcst.codemod import VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.codemod.visitors import RemoveImportsVisitor
from libcst.metadata import ProviderT
from libcst.metadata import QualifiedNameProvider
from libcst.metadata import ScopeProvider

AddRemoveImport: TypeAlias = tuple[str, str | None, str | None]


class BaseConfig(msgspec.Struct, kw_only=True, frozen=True, forbid_unknown_fields=True):
    """
    Base configuration class for codemoders.
    """

    exclude: list[str] = msgspec.field(default_factory=list)
    """
    List of glob patterns to exclude paths from being processed.
    """


CodemodConfigType = TypeVar("CodemodConfigType", bound=BaseConfig)


class BaseCodemod(VisitorBasedCodemodCommand, ABC, Generic[CodemodConfigType]):
    """
    Base class for codemoders.
    """

    NAME: ClassVar[str]
    CONFIG_CLS: ClassVar[type[BaseConfig]]
    PRIORITY: ClassVar[int] = 0
    METADATA_DEPENDENCIES: ClassVar[Sequence[ProviderT]] = (QualifiedNameProvider, ScopeProvider)

    def __new__(cls, *_: Any, **__: Any) -> Self:
        """
        Make sure this class is not instantiated directly.

        Additionally, collect all metadata dependencies from the class and its superclasses.
        """
        if cls is BaseCodemod:
            error_msg = "BaseCodemod cannot be instantiated directly."
            raise TypeError(error_msg)
        dependencies: set[ProviderT] = set()
        for c in inspect.getmro(cls):
            if issubclass(c, MetadataDependent):
                dependencies.update(c.METADATA_DEPENDENCIES)
        cls.METADATA_DEPENDENCIES = tuple(dependencies)
        return super().__new__(cls)

    def __init__(self, context: CodemodContext, config: CodemodConfigType):
        for pattern in config.exclude:
            if TYPE_CHECKING:
                assert context.filename is not None
            if fnmatch.fnmatch(context.filename, pattern):
                error_msg = f"Excluded by pattern '{pattern}' defined in the '{self.NAME}' codemod configuration ."
                raise SkipFile(error_msg)
        super().__init__(context)
        self.config = config
        self._add_imports: set[AddRemoveImport] = set()
        self._remove_imports: set[AddRemoveImport] = set()
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
        if doc is None:
            error_msg = f"Codemod {cls.__name__} must have a docstring to be used in the CLI."
            raise TypeError(error_msg)
        if TYPE_CHECKING:
            assert doc is not None
        return doc.strip().splitlines()[0].strip()

    def add_import(self, module: str, obj: str | None = None, asname: str | None = None) -> None:
        """
        Schedule an import to be added to the updated module, if not already present.

        This method has the same signature as [add_needed_import][libcst.codemod.visitors.AddImportsVisitor],
        the only major difference is that we won't duplicate the imports even if you call this method multiple
        times, and, we pass the [context][libcst.codemod.CodemodContext] when actually updating the imports.
        """
        self._add_imports.add((module, obj, asname))

    def remove_import(self, module: str, obj: str | None = None, asname: str | None = None) -> None:
        """
        Schedule an import to be removed from the updated module, if present.

        This method has the same signature as [remove_unused_import][libcst.codemod.visitors.RemoveImportsVisitor],
        the only major difference is that we won't schedule duplicate import removals even if you call this method
        multiple times, and, we pass the [context][libcst.codemod.CodemodContext] when actually updating the imports.
        """
        self._remove_imports.add((module, obj, asname))

    @m.leave(m.Module())
    def _update_imports(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """
        Update the imports in the updated node based on the changes made in the original node.
        """
        if self._add_imports:
            for module, obj, asname in self._add_imports:
                AddImportsVisitor.add_needed_import(self.context, module=module, obj=obj, asname=asname)
            add_imports_visitor = AddImportsVisitor(self.context)
            updated_node = updated_node.visit(add_imports_visitor)

        if self._remove_imports:
            self.get_metadata(QualifiedNameProvider, original_node)
            for module, obj, asname in self._remove_imports:
                RemoveImportsVisitor.remove_unused_import(self.context, module=module, obj=obj, asname=asname)

        return updated_node


CodemodType = TypeVar("CodemodType", bound=BaseCodemod)

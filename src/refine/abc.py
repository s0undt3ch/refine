"""
Abstract base classes for defining codemod types and their configurations.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
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
from libcst.codemod import CodemodContext
from libcst.codemod import VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.codemod.visitors import RemoveImportsVisitor

AddRemoveImport: TypeAlias = tuple[str, str | None, str | None]

_SHARED_WRAPPER_KEY = "__refine_shared_wrapper__"
_PRISTINE_TREE_KEY = "__refine_pristine_tree__"


class BaseConfig(msgspec.Struct, kw_only=True, frozen=True, forbid_unknown_fields=True):
    """
    Base configuration class for codemoders.
    """

    exclude: list[str] = msgspec.field(default_factory=list)
    """
    List of glob patterns to exclude paths from being processed.
    """

    def cache_key_paths(self) -> list[str]:
        """
        Paths of external files whose CONTENTS affect this codemod's output.

        The run cache hashes these files' bytes into its context key so
        editing them invalidates cached results. Override in configs that
        reference external configuration files.
        """
        return []


CodemodConfigType = TypeVar("CodemodConfigType", bound=BaseConfig)


class BaseCodemod(VisitorBasedCodemodCommand, ABC, Generic[CodemodConfigType]):
    """
    Base class for codemoders.
    """

    NAME: ClassVar[str]
    CONFIG_CLS: ClassVar[type[BaseConfig]]
    PRIORITY: ClassVar[int] = 0

    def __new__(cls, *_: Any, **__: Any) -> Self:
        """
        Make sure this class is not instantiated directly.
        """
        if cls is BaseCodemod:
            error_msg = "BaseCodemod cannot be instantiated directly."
            raise TypeError(error_msg)
        return super().__new__(cls)

    def __init__(self, context: CodemodContext, config: CodemodConfigType):
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

    @classmethod
    def should_process(cls, source: str, filename: str) -> bool:
        """
        Cheap raw-text gate called BEFORE the file is parsed.

        Return ``False`` only when this codemod provably cannot change the
        file (false positives are fine, false negatives are forbidden).
        The default is to always process.
        """
        return True

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

    @contextmanager
    def _handle_metadata_reference(self, module: cst.Module) -> Generator[cst.Module, None, None]:
        """
        Reuse one MetadataWrapper per file across all chained codemods.

        libcst's default builds a fresh deep-copying wrapper per codemod per
        file. We keep the wrapper in ``context.scratch`` and only rebuild it
        when the tree object actually changed. The deep copy is skipped only
        for the pristine parser output (guaranteed duplicate-free); rebuilt
        wrappers for transformed trees keep libcst's safety copy.
        """
        oldwrapper = self.context.wrapper
        wrapper: cst.MetadataWrapper | None = self.context.scratch.get(_SHARED_WRAPPER_KEY)
        if wrapper is None or wrapper.module is not module:
            metadata_manager = self.context.metadata_manager
            filename = self.context.filename
            if metadata_manager is not None and filename:
                cache = metadata_manager.get_cache_for_path(filename)
            else:
                cache = {}
            pristine = self.context.scratch.get(_PRISTINE_TREE_KEY)
            wrapper = cst.MetadataWrapper(module, unsafe_skip_copy=module is pristine, cache=cache)
            self.context.scratch[_SHARED_WRAPPER_KEY] = wrapper
        with self.resolve(wrapper):
            self.context = replace(self.context, wrapper=wrapper)
            try:
                yield wrapper.module
            finally:
                self.context = replace(self.context, wrapper=oldwrapper)

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
            for module, obj, asname in self._remove_imports:
                RemoveImportsVisitor.remove_unused_import(self.context, module=module, obj=obj, asname=asname)

        return updated_node


CodemodType = TypeVar("CodemodType", bound=BaseCodemod)

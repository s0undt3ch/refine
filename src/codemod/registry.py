"""
Codemod registry.

This holds the information about what codemods are available to be used.
"""

import importlib.metadata
import inspect
import operator
from collections import OrderedDict
from collections.abc import Iterator
from importlib.machinery import SourceFileLoader
from pathlib import Path

from .abc import BaseCodemod
from .abc import CodemodConfigType
from .config import Config


class Registry:
    """
    Registry class to hold all available codemods.
    """

    __slots__ = ("_config", "_codemods")

    def __init__(self, config: Config) -> None:
        self._config = config
        self._codemods: OrderedDict[str, type[BaseCodemod]] = OrderedDict()

    def load(self) -> None:
        """
        Load all available codemods.
        """
        self._codemods.clear()
        codemods: list[type[BaseCodemod]] = []
        codemod: type[BaseCodemod]
        for codemod in self._collect_from_entrypoints():
            codemods.append(codemod)
        for path in self._config.codemod_paths:
            for codemod in self._collect_from_path(path):
                codemods.append(codemod)

        for codemod in sorted(codemods, key=operator.attrgetter("PRIORITY")):
            codemod_name: str = codemod.NAME
            self._codemods[codemod_name] = codemod

    def codemods(self, exclude_codemods=(), select_codemods=()):
        """
        Returns all available codemods, optionally skipping those passed in `excluded_names`.
        """
        for name in self._codemods:
            if select_codemods:
                if name in select_codemods:
                    yield name, self._codemods[name]
                continue
            if name in exclude_codemods:
                continue
            yield name, self._codemods[name]

    def fix_names(self):
        """
        Returns the list of the fix names.
        """
        return list(self.codemods)

    def _collect_from_entrypoints(self) -> Iterator[type[BaseCodemod[CodemodConfigType]]]:
        for entry_point in importlib.metadata.entry_points(group="codemod"):
            cls: type[BaseCodemod[CodemodConfigType]] = entry_point.load()
            if not inspect.isclass(cls):
                # Don't even bother if it's not a class
                continue
            if not issubclass(cls, BaseCodemod):
                # Don't even bother if it's not a subclass of BaseCodemod
                continue
            if cls is BaseCodemod:
                # We definitely do not want the BaseCodemod class itself
                continue
            yield cls

    def _collect_from_path(self, path: Path) -> Iterator[type[BaseCodemod[CodemodConfigType]]]:
        for fpath in path.glob("*.py"):
            loader = SourceFileLoader(fpath.name, str(fpath))
            module = loader.load_module()
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if not issubclass(cls, BaseCodemod):
                    # Don't even bother if it's not a subclass of BaseCodemod
                    continue
                if cls is BaseCodemod:
                    # We definitely do not want the BaseCodemod class itself
                    continue
                yield cls

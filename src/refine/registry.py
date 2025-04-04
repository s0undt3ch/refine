"""
Refine registry.

This holds the information about what codemods are available to be used.
"""

from __future__ import annotations

import importlib.metadata
import inspect
import logging
import operator
import sys
from collections.abc import Iterable
from collections.abc import Iterator
from importlib.machinery import SourceFileLoader
from pathlib import Path

from .abc import BaseCodemod
from .abc import CodemodConfigType

log = logging.getLogger(__name__)


class Registry:
    """
    Registry class to hold all available codemods.
    """

    __slots__ = ("_codemods",)

    def __init__(self) -> None:
        self._codemods: list[type[BaseCodemod]] = []

    def load(self, search_paths: list[Path]) -> None:
        """
        Load all available codemods.
        """
        codemods: dict[str, type[BaseCodemod]] = {}
        codemod: type[BaseCodemod]
        for codemod in self._collect_from_entrypoints():
            if codemod.NAME in codemods:
                log.warning("Already loaded a codemod by the name of %s", codemod.NAME)
                continue
            codemods[codemod.NAME] = codemod
        for path in search_paths:
            for codemod in self._collect_from_path(path):
                if codemod.NAME in codemods:
                    log.warning("Already loaded a codemod by the name of %s", codemod.NAME)
                    continue
                codemods[codemod.NAME] = codemod
        self._codemods[:] = sorted(codemods.values(), key=operator.attrgetter("PRIORITY"))

    def codemods(
        self, exclude_codemods: Iterable[str] = (), select_codemods: Iterable[str] = ()
    ) -> Iterator[type[BaseCodemod]]:
        """
        Returns all available codemods, optionally skipping those passed in `excluded_names`.
        """
        for codemod in self._codemods:
            if exclude_codemods and codemod.NAME in exclude_codemods:
                continue
            if select_codemods and codemod.NAME not in select_codemods:
                continue
            yield codemod

    def _collect_from_entrypoints(self) -> Iterator[type[BaseCodemod[CodemodConfigType]]]:
        for entry_point in importlib.metadata.entry_points(group="refine.mods"):
            try:
                cls: type[BaseCodemod[CodemodConfigType]] = entry_point.load()
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load entry point %s: %s", entry_point.name, exc)
                continue
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
        # Make sure custom codemod paths are in sys.path
        strpath = str(path)
        if strpath not in sys.path:
            sys.path.insert(0, strpath)
        for fpath in path.glob("*.py"):
            loader = SourceFileLoader(fpath.stem, str(fpath))
            module = loader.load_module()
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if not issubclass(cls, BaseCodemod):
                    # Don't even bother if it's not a subclass of BaseCodemod
                    continue
                if cls is BaseCodemod:
                    # We definitely do not want the BaseCodemod class itself
                    continue
                yield cls

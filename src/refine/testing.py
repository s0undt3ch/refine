"""
Refine testing support.
"""

from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING

from libcst import PartialParserConfig
from libcst import parse_module
from libcst.codemod import CodemodContext
from libcst.codemod import SkipFile

if TYPE_CHECKING:
    from refine.abc import BaseCodemod
    from refine.abc import BaseConfig

log = logging.getLogger(__name__)


@dataclass(kw_only=True, slots=True)
class Modcase:
    path: Path
    codemod: type[BaseCodemod] = field(repr=False)
    codemod_config: BaseConfig = field(repr=False)
    name: str = field(init=False)
    original: str = field(init=False, repr=False)
    updated: str = field(init=False, repr=False)
    require_changes: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        self.name = self.path.stem
        log.debug("Populating ModCase.original from: %s", self.path)
        self.original = self._dedent_contents(self.path)
        updated_path = self.path.with_stem(f"{self.path.stem}.updated")
        log.debug("Populating ModCase.updated from: %s", updated_path)
        self.updated = self._dedent_contents(updated_path)
        self.require_changes = self.original != self.updated

    def _dedent_contents(self, path: Path, strip_first_newline: bool = True) -> str:
        contents = path.read_text()
        if contents.startswith("\n") and strip_first_newline:
            contents = contents[1:]
        return textwrap.dedent(contents)

    def assert_codemod(self, expected_skip: bool = False) -> None:
        """
        This assertion is inspired by libCST's TestClass implementation.
        """
        # Make sure the original content does not match the updated content
        log.debug("Testing %s", self)
        assert self.original != self.updated
        context = CodemodContext(filename=str(self.path))
        transform_instance = self.codemod(context, self.codemod_config.model_copy())
        input_tree = parse_module(self.original, config=PartialParserConfig())
        try:
            output_tree = transform_instance.transform_module(input_tree)
        except SkipFile:
            if not expected_skip:
                raise
            output_tree = input_tree
        else:
            if expected_skip:
                error = "Expected SkipFile but was not raised"
                raise AssertionError(error)

        if self.require_changes:
            # Make sure changes were made
            assert output_tree.code != self.original
        else:
            # Make sure no changes were made
            assert output_tree.code == self.original

        # Match what we have on file
        assert output_tree.code == self.updated

"""
Refine configuration.
"""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path
from typing import Any

import msgspec

from refine.exc import ConfigLoadError
from refine.exc import InvalidConfigError

log = logging.getLogger(__name__)


def _cpu_count() -> int:
    # os.cpu_count() can return None, let's not.
    return max((os.cpu_count() or 1) - 1, 1)


class Config(msgspec.Struct, kw_only=True, frozen=True):
    """
    Main codemod configuration schema.
    """

    select: list[str] = msgspec.field(default_factory=list)
    """
    List of codemods to run.

    When no selection is made, all available codemods are run.
    """

    exclude: list[str] = msgspec.field(default_factory=list)
    """
    List of codemods to exclude.

    Only makes sense when `select` is empty and all codemods are run.
    """

    codemod_paths: list[str] = msgspec.field(default_factory=list)
    """
    List of additional paths to search for codemods.
    """

    process_pool_size: int = msgspec.field(default_factory=_cpu_count)
    """
    Number of processes to use for parallel processing.
    Defaults to the number of available CPUs.
    """

    repo_root: str = msgspec.field(default_factory=os.getcwd)
    """
    The root directory of the repository.
    Defaults to the current working directory.
    """

    fail_fast: bool = False
    """
    Stop processing as soon as possible after the first error.
    """

    respect_gitignore: bool = False
    """
    Ignore files and directories listed in `.gitignore`.
    """

    exclude_patterns: list[str] = msgspec.field(default_factory=list)
    """
    List of glob path patterns to exclude from processing. Note that the full path is checked against the glob.
    """

    __remaining_config__: dict[str, Any] = msgspec.field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """
        Load the configuration from a dictionary.

        Arguments:
            data: The configuration to load.

        Returns:
            Config instance.
        """
        try:
            config = msgspec.convert(data, type=Config)
            config.__remaining_config__.update({k: v for (k, v) in data.items() if k not in config.__struct_fields__})
        except msgspec.ValidationError as exc:
            error = f"Invalid configuration: {exc}"
            raise InvalidConfigError(error) from exc
        else:
            return config

    @classmethod
    def from_default_file(cls, path: Path) -> Config:
        """
        Load the configuration from a file.

        Arguments:
            path: The path to the configuration file.

        Returns:
            Config instance.
        """
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            error = f"Unable to parse {path}: {exc}"
            raise ConfigLoadError(error) from exc
        else:
            return cls.from_dict(data)

    @classmethod
    def from_pyproject_file(cls, path: Path) -> Config:
        """
        Load the configuration from a file.

        Arguments:
            path: The path to the configuration file.

        Returns:
            Config instance.
        """
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            error = f"Unable to parse {path}: {exc}"
            raise ConfigLoadError(error) from exc
        else:
            return cls.from_dict(data.get("tool", {}).get("refine", {}))

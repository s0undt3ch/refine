"""
Refine configuration.
"""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

log = logging.getLogger(__name__)


def _cpu_count() -> int:
    # os.cpu_count() can return None, let's not.
    return os.cpu_count() or 1


class ConfigError(ValueError):
    """
    Config related error.
    """


class ConfigLoadError(ConfigError):
    """
    Exception raised when failing to load the configuration from file.
    """


class InvalidConfigError(ConfigError):
    """
    Exception raised when the loaded configuration is not valid.
    """


class Config(BaseModel):
    """
    Main codemod configuration schema.
    """

    model_config = ConfigDict(
        # Don't allow the config object to be mutable.
        # Do note that mutable objects(set, list, dict) of the immutable config class remain mutable.
        frozen=True,
        # Allow extra keys, these will be codemods configs
        extra="allow",
    )

    select: list[str] = Field(
        default_factory=list,
        description="""
        List of codemods to run.

        When no selection is made, all available codemods are run.
        """,
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="""
        List of codemods to exclude.

        Only makes sense when `select` is empty and all codemods are run.
    """,
    )
    codemod_paths: list[Path] = Field(
        default_factory=list,
        description="""
        List of additional paths to search for codemods.
        """,
    )
    process_pool_size: int = Field(
        default_factory=_cpu_count,
        description="""
        Number of processes to use for parallel processing.
        Defaults to the number of available CPUs.
        """,
    )
    repo_root: Path = Field(
        default_factory=Path.cwd,
        description="""
        The root directory of the repository.
        Defaults to the current working directory.
        """,
    )
    fail_fast: bool = Field(
        default=False,
        description="""
        Stop processing as soon as possible after the first error.
        """,
    )
    respect_gitignore: bool = Field(
        default=False,
        description="""
        Ignore files and directories listed in `.gitignore`.
        """,
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="""
        List of glob path patterns to exclude from processing. Note that the full path is checked against the glob.
        """,
    )

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
            return Config(**data)
        except ValueError as exc:
            error = f"Invalid configuration: {exc}"
            raise InvalidConfigError(error) from exc

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

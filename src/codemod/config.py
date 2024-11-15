"""
Codemod configuration.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

log = logging.getLogger(__name__)


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
        # Don't allow changes to the configuration once loaded
        frozen=True,
        # Allow extra keys, these will be codemods configs
        extra="allow",
    )

    select: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    codemod_paths: list[Path] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """
        Load the configuration from a dictionary.

        :param data: The configuration to load.
        :return: Config instance.
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

        :param path: The path to the configuration file.
        :return: Config instance.
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

        :param path: The path to the configuration file.
        :return: Config instance.
        """
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            error = f"Unable to parse {path}: {exc}"
            raise ConfigLoadError(error) from exc
        else:
            prefix = "tool.codemod"
            config_data = {}
            for key, value in data.items():
                if not key.startswith(prefix):
                    continue
                # Handle <prefix>
                if key == prefix:
                    config_data[key[len(prefix) :]] = value
                    continue
                # Now '<prefix>.'
                config_data[key[len(prefix) + 1 :]] = value
            return cls.from_dict(config_data)

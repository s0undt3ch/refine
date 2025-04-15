from __future__ import annotations

import os
import pathlib
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from typing import Self
from unittest.mock import patch

import pytest
import tomli_w

from refine.cli import CLI as OriginalCLI  # noqa: N811
from refine.processor import ParallelTransformResult


class CLI(OriginalCLI):
    def with_config(self, **config: dict[str, Any]) -> Self:
        with open(pathlib.Path.cwd() / ".refine.toml", "w") as wfh:
            wfh.write(tomli_w.dumps(config))
        return self

    def run(self, *argv: str) -> int:  # type: ignore[override]
        """
        Run the CLI with the given arguments.
        """
        try:
            super().run([str(arg) for arg in argv])
        except SystemExit as exc:
            exitcode = exc.code
            if not isinstance(exitcode, int):
                return -10
            return exitcode


@dataclass
class MockedCodemod:
    NAME: str
    description: str
    PRIORITY: int = 0

    def get_short_description(self) -> str:
        return self.description


@pytest.fixture
def codemods():
    """
    Mocked codemods for testing purposes.
    """
    return [
        MockedCodemod(NAME=name, description=f"Example codemod description for {name}")
        for name in ("codemod-1", "codemod-2", "codemod-3")
    ]


@pytest.fixture
def _mock_registry_codemods(codemods):
    """Fixture to mock the Registry class."""
    with patch("refine.cli.Registry._load", return_value={mod.NAME: mod for mod in codemods}):
        yield


class MockedProcessor:
    def __init__(self, config, registry, codemods):
        """
        Initialize the mocked processor.
        """
        self.config = config
        self.registry = registry
        self.codemods = codemods
        self.files = []

    def process(self, files: list[pathlib.Path]) -> ParallelTransformResult:
        """
        Mocked process method for testing purposes.
        """
        self.files = files
        return ParallelTransformResult(successes=1, failures=0, warnings=0, skips=0, changed=0)


@pytest.fixture
def processor(_mock_registry_codemods):
    """
    Mocked processor for testing purposes.
    """
    with patch("refine.cli.Processor", MockedProcessor) as mocked_processor:
        yield mocked_processor


@pytest.fixture
def file_to_modify(tmp_path: pathlib.Path) -> pathlib.Path:
    """
    Create a temporary file to modify.
    """
    file_path = tmp_path / "test_file.py"
    with open(file_path, "w") as f:
        f.write("print('Hello, World!')")
    return file_path


@pytest.fixture
def cli(tmp_path: pathlib.Path, processor) -> Generator[CLI, None, None]:
    """
    Create a CLI instance with a temporary directory.
    """
    current_cwd = pathlib.Path.cwd()
    try:
        os.chdir(tmp_path)
        yield CLI()
    finally:
        os.chdir(current_cwd)

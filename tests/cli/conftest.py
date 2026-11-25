from __future__ import annotations

import logging
import os
import pathlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from typing import Self
from unittest.mock import patch

import pytest
import tomli_w

from refine.abc import BaseCodemod
from refine.cli import CLI as OriginalCLI  # noqa: N811
from refine.config import Config
from refine.processor import ParallelTransformResult


class CLI(OriginalCLI):
    def __init__(self, cwd: pathlib.Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cwd = cwd

    def with_config(self, **config: dict[str, Any]) -> Self:
        with open(self.cwd / ".refine.toml", "w") as wfh:
            wfh.write(tomli_w.dumps(config))
        return self

    def run(self, *argv: str) -> int:  # type: ignore[override]
        """
        Run the CLI with the given arguments.
        """
        with self.with_cwd(self.cwd):
            try:
                super().run([str(arg) for arg in argv])
            except SystemExit as exc:
                exitcode = exc.code
                if not isinstance(exitcode, int):
                    return -10
                return exitcode

    @contextmanager
    def with_cwd(self, cwd: pathlib.Path) -> Iterator[Self]:
        current_cwd = pathlib.Path.cwd()
        try:
            os.chdir(cwd)
            yield self
        finally:
            os.chdir(current_cwd)

    def default_config(self) -> Config:
        """
        Return the default configuration.
        """
        return Config()


@pytest.fixture
def codemods() -> list[type[BaseCodemod]]:
    """
    Three minimal codemods. The ``cli`` fixture's registry returns only these, so listings and
    selections don't depend on the built-in codemods.
    """
    return [
        type(
            f"Codemod{index}",
            (BaseCodemod,),
            {"__doc__": f"Example codemod description for codemod-{index}", "NAME": f"codemod-{index}"},
        )
        for index in (1, 2, 3)
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
def real_cli(tmp_path: pathlib.Path) -> CLI:
    """
    CLI instance with the real registry and processor, nothing patched.
    """
    cli_cwd = tmp_path / "cli-cwd"
    cli_cwd.mkdir()
    return CLI(cli_cwd)


@pytest.fixture
def cli(real_cli: CLI, processor) -> CLI:
    """
    CLI instance whose registry only knows the ``codemods`` fixture and whose processor is faked.
    """
    return real_cli


@pytest.fixture
def file_to_modify(cli: CLI) -> pathlib.Path:
    """
    Create a temporary file to modify.
    """
    file_path = cli.cwd / "test_file.py"
    with open(file_path, "w") as f:
        f.write("print('Hello, World!')")
    return file_path


@pytest.fixture
def restore_log_levels():
    """
    Put back the root and ``py_walk`` log levels that ``--quiet``/``--verbose`` change.
    """
    loggers = [logging.getLogger(), logging.getLogger("py_walk")]
    levels = [logger.level for logger in loggers]
    yield
    for logger, level in zip(loggers, levels, strict=True):
        logger.setLevel(level)

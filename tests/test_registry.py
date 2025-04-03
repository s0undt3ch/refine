from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from refine.abc import BaseCodemod
from refine.registry import Registry


class MockCodemod(BaseCodemod):
    NAME = "mock"
    PRIORITY = 10


class AnotherCodemod(BaseCodemod):
    NAME = "another"
    PRIORITY = 5


class LastCodemod(BaseCodemod):
    NAME = "last"
    PRIORITY = 1


@pytest.fixture
def registry():
    """Fixture to create a fresh instance of the Registry."""
    return Registry()


def test_registry_initialization(registry):
    """Test that the Registry initializes correctly."""
    assert registry._codemods == []


def test_load_from_entrypoints(registry):
    """Test loading codemods from entry points."""
    with patch("refine.registry.Registry._collect_from_entrypoints", return_value=iter([MockCodemod])) as mock_collect:
        registry.load([])
        assert registry._codemods == [MockCodemod]
        mock_collect.assert_called_once()


def test_load_from_path(registry):
    """Test loading codemods from a specified path."""
    with (
        patch("refine.registry.Registry._collect_from_entrypoints", return_value=iter([])),
        patch("refine.registry.Registry._collect_from_path", return_value=iter([AnotherCodemod])) as mock_collect,
    ):
        test_path = Path("/some/path")
        registry.load([test_path])
        assert registry._codemods == [AnotherCodemod]
        mock_collect.assert_called_once_with(test_path)


def test_load_combined_sources(registry):
    """Test loading codemods from both entry points and paths."""
    with patch("refine.registry.Registry._collect_from_entrypoints", return_value=iter([MockCodemod])) as mock_entry:
        with patch("refine.registry.Registry._collect_from_path", return_value=iter([AnotherCodemod])) as mock_path:
            test_path = Path("/some/path")
            registry.load([test_path])
            assert registry._codemods == [AnotherCodemod, MockCodemod]
            assert registry._codemods[0].PRIORITY < registry._codemods[1].PRIORITY  # Ensure sorting
            mock_entry.assert_called_once()
            mock_path.assert_called_once_with(test_path)


def test_codemods_with_selection(registry):
    """Test retrieving codemods with selection filters."""
    registry._codemods = [MockCodemod, AnotherCodemod, LastCodemod]
    selected = list(registry.codemods(select_codemods=["mock"]))
    assert selected == [MockCodemod]

    selected = list(registry.codemods(select_codemods=["mock"], exclude_codemods=["last"]))
    assert selected == [MockCodemod]

    # Exclusion takes precedence
    selected = list(registry.codemods(select_codemods=["mock"], exclude_codemods=["mock"]))
    assert selected == []


def test_codemods_with_exclusion(registry):
    """Test retrieving codemods with exclusion filters."""
    registry._codemods = [MockCodemod, AnotherCodemod, LastCodemod]
    selected = list(registry.codemods(exclude_codemods=["mock"]))
    assert selected == [AnotherCodemod, LastCodemod]


def test_collect_from_entrypoints(registry):
    """Test collecting codemods from entry points."""
    mock_entry = MagicMock()
    mock_entry.load.return_value = MockCodemod

    with patch("importlib.metadata.entry_points", return_value=[mock_entry]):
        collected = list(registry._collect_from_entrypoints())
        assert collected == [MockCodemod]


def test_collect_from_path(registry):
    """Test collecting codemods from a directory path."""
    mock_file = MagicMock()
    mock_file.name = "mock_codemod.py"

    with patch("refine.registry.Path.glob", return_value=[mock_file]) as mock_glob:
        with patch("refine.registry.SourceFileLoader") as mock_loader:
            mock_loader.return_value.load_module.return_value = MagicMock()

            with patch("inspect.getmembers", return_value=[("MockCodemod", MockCodemod)]):
                collected = list(registry._collect_from_path(Path("/some/path")))

            assert collected == [MockCodemod]
            mock_glob.assert_called_once()
            mock_loader.assert_called_once_with(mock_file.stem, str(mock_file))


def test_duplicate_codemod_handling_with_caplog(registry, caplog):
    """Test handling of duplicate codemod names using caplog."""
    with patch(
        "refine.registry.Registry._collect_from_entrypoints",
        return_value=iter([MockCodemod, MockCodemod]),
    ):
        with caplog.at_level("WARNING"):
            registry.load([])

            assert len(registry._codemods) == 1
            assert "Already loaded a codemod by the name of mock" in caplog.text

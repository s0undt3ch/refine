from __future__ import annotations

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


BUILTIN_CODEMODS = {"cli-dashes-over-underscores", "sqlfmt"}


def test_load_finds_builtin_codemods_from_entrypoints(registry):
    registry.load([])

    assert {codemod.NAME for codemod in registry.codemods()} == BUILTIN_CODEMODS


def test_load_adds_codemods_from_search_paths(registry, tmp_path, write_codemod):
    write_codemod(tmp_path, name="custom")

    registry.load([str(tmp_path)])

    assert {codemod.NAME for codemod in registry.codemods()} == BUILTIN_CODEMODS | {"custom"}


def test_load_sorts_codemods_by_priority(registry, tmp_path, write_codemod):
    write_codemod(tmp_path, name="custom", priority=-1)

    registry.load([str(tmp_path)])

    assert next(registry.codemods()).NAME == "custom"


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


def test_collect_from_entrypoints_yields_builtin_codemods(registry):
    collected = list(registry._collect_from_entrypoints())

    assert {codemod.NAME for codemod in collected} == BUILTIN_CODEMODS


def test_collect_from_path_imports_codemod_modules(registry, tmp_path, write_codemod):
    module_name = write_codemod(tmp_path, name="custom")

    collected = list(registry._collect_from_path(str(tmp_path)))

    assert [(cls.NAME, cls.__module__) for cls in collected] == [("custom", module_name)]


def test_load_keeps_builtin_codemod_when_path_codemod_reuses_its_name(registry, tmp_path, write_codemod, caplog):
    write_codemod(tmp_path, name="sqlfmt")

    with caplog.at_level("WARNING"):
        registry.load([str(tmp_path)])

    [sqlfmt] = [codemod for codemod in registry.codemods() if codemod.NAME == "sqlfmt"]
    assert sqlfmt.__module__ == "refine.mods.sql.fmt"
    assert "Already loaded a codemod by the name of sqlfmt" in caplog.text

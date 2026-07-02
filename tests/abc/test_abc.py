from __future__ import annotations

import pathlib

import libcst as cst
import pytest
from libcst.metadata import QualifiedNameProvider
from libcst.metadata import WhitespaceInclusivePositionProvider

from refine.abc import BaseCodemod
from refine.abc import BaseConfig
from refine.mods.cli.flags import CliDashes
from refine.mods.sql.fmt import FormatSQL
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files"


class MyCustomModcaseConfig(BaseConfig, frozen=True):
    add_imports: bool = False
    remove_imports: bool = False


class MyCustomModcase(BaseCodemod):
    """
    Custom codemod class for testing purposes.
    """

    NAME = "my-custom-mod"
    CONFIG_CLS = MyCustomModcaseConfig
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    def __post_codemod_init__(self) -> None:
        """
        This method can implement additional codemod initialization.
        """

    def visit_Module(self, node: cst.Module) -> bool:  # noqa: N802
        super().visit_Module(node)
        if self.config.remove_imports:
            self.remove_import("logging")
            self.remove_import("datetime", "datetime")
            self.remove_import("enum")
        if self.config.add_imports:
            self.add_import("enum", "StrEnum")
        # Continue processing
        return True


@pytest.fixture
def add_imports_case() -> Modcase:
    return Modcase(
        path=FILES_PATH / "add-imports.py",
        codemod=MyCustomModcase,
        codemod_config=MyCustomModcaseConfig(add_imports=True, remove_imports=False),
    )


@pytest.fixture
def remove_imports_case() -> Modcase:
    return Modcase(
        path=FILES_PATH / "remove-imports.py",
        codemod=MyCustomModcase,
        codemod_config=MyCustomModcaseConfig(add_imports=False, remove_imports=True),
    )


@pytest.fixture
def add_remove_imports_case() -> Modcase:
    return Modcase(
        path=FILES_PATH / "add-remove-imports.py",
        codemod=MyCustomModcase,
        codemod_config=MyCustomModcaseConfig(add_imports=True, remove_imports=True),
    )


def test_add_imports(add_imports_case: Modcase):
    add_imports_case.assert_codemod()


def test_remove_imports(remove_imports_case: Modcase):
    remove_imports_case.assert_codemod()


def test_add_remove_imports(add_remove_imports_case: Modcase):
    add_remove_imports_case.assert_codemod()


def test_should_process_defaults_to_true():
    assert BaseCodemod.should_process("anything", "x.py") is True


def test_base_codemod_declares_no_metadata_dependencies():
    assert tuple(BaseCodemod.METADATA_DEPENDENCIES) == ()


def test_codemod_gets_exactly_declared_dependencies():
    assert set(FormatSQL.get_inherited_dependencies()) == {WhitespaceInclusivePositionProvider}


def test_codemod_without_declarations_gets_none():
    assert set(CliDashes.get_inherited_dependencies()) == set()

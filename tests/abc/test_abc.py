from __future__ import annotations

import pathlib

import libcst as cst
import pytest
from libcst.codemod import CodemodContext
from libcst.metadata import QualifiedNameProvider
from libcst.metadata import WhitespaceInclusivePositionProvider

from refine.abc import _PRISTINE_TREE_KEY
from refine.abc import _SHARED_WRAPPER_KEY
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

    def visit_Module(self, node: cst.Module) -> bool:
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


class _ModuleSkipper(BaseCodemod):
    """
    Declines the whole module in visit_Module, like real codemods whose
    module-level check finds nothing to do (e.g. deprecated-settings-imports).

    IMPORTANT libcst behavior this test leans on: a full traversal rebuilds
    the Module object even when nothing changed, so identity-based wrapper
    sharing only kicks in when a codemod short-circuits (visit_Module ->
    False) or never traverses. That IS the common case once gates have
    filtered: chained codemods that decline the module share one wrapper.
    """

    NAME = "module-skipper"
    CONFIG_CLS = BaseConfig
    METADATA_DEPENDENCIES = (WhitespaceInclusivePositionProvider,)

    def visit_Module(self, node: cst.Module) -> bool:
        self.get_metadata(WhitespaceInclusivePositionProvider, node)
        return False


def test_wrapper_is_shared_across_codemods_on_unchanged_tree():
    tree = cst.parse_module("pass\n")
    context = CodemodContext(filename="x.py")
    context.scratch[_PRISTINE_TREE_KEY] = tree

    first = _ModuleSkipper(context=context, config=BaseConfig())
    out1 = first.transform_module(tree)
    wrapper_after_first = context.scratch[_SHARED_WRAPPER_KEY]
    # unsafe_skip_copy on the pristine tree: yielded module is the parsed tree itself
    assert wrapper_after_first.module is tree
    # visit_Module -> False preserves module identity
    assert out1 is tree

    second = _ModuleSkipper(context=context, config=BaseConfig())
    second.transform_module(out1)
    # Unchanged tree -> same wrapper object, no re-wrap, no re-resolve
    assert context.scratch[_SHARED_WRAPPER_KEY] is wrapper_after_first


def test_wrapper_rebuilt_when_tree_changes():
    class _Renamer(BaseCodemod):
        """Renames every Name to force a tree change."""

        NAME = "renamer"
        CONFIG_CLS = BaseConfig

        def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
            return updated_node.with_changes(value=updated_node.value + "_x")

    tree = cst.parse_module("a = 1\n")
    context = CodemodContext(filename="x.py")
    context.scratch[_PRISTINE_TREE_KEY] = tree

    changed = _Renamer(context=context, config=BaseConfig()).transform_module(tree)
    wrapper_one = context.scratch[_SHARED_WRAPPER_KEY]
    assert changed.code == "a_x = 1\n"

    _ModuleSkipper(context=context, config=BaseConfig()).transform_module(changed)
    wrapper_two = context.scratch[_SHARED_WRAPPER_KEY]
    assert wrapper_two is not wrapper_one

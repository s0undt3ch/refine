from __future__ import annotations

import importlib.util
import itertools
import sys
import textwrap
from collections.abc import Callable
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make sure the assertion we do in refine/testing.py gets rewritten by pytest for proper visualization
# of assertion failures
pytest.register_assert_rewrite("refine.testing")

# tests/tools/ needs the toolr venv: `toolr project venv run -- pytest tests/tools/`
if importlib.util.find_spec("toolr") is None:
    collect_ignore = ["tools"]


@pytest.fixture
def codemod_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """
    Directory to hold codemod modules that the registry loads by path.

    Loading by path adds the directory to ``sys.path`` and the modules to ``sys.modules``. Both are
    undone on teardown for anything under this test's ``tmp_path``.
    """
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield tmp_path
    for name, module in list(sys.modules.items()):
        if str(tmp_path) in str(getattr(module, "__file__", None) or ""):
            del sys.modules[name]


@pytest.fixture
def write_codemod(codemod_dir: Path) -> Callable[..., str]:
    """
    Factory writing a real codemod module to disk, as a user's ``codemod_paths`` entry would hold.

    The codemod renames ``x`` to ``x_refined``. ``directory`` must be under ``tmp_path``. Returns the
    generated module name, which differs from ``codemod_name``.
    """
    module_numbers = itertools.count()

    def _write(directory: Path, *, codemod_name: str, priority: int = 0) -> str:
        module_name = f"refine_test_codemod_{next(module_numbers)}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{module_name}.py").write_text(
            textwrap.dedent(
                f'''
                import libcst as cst

                from refine.abc import BaseCodemod


                class CustomCodemod(BaseCodemod):
                    """Custom codemod {codemod_name}."""

                    NAME = {codemod_name!r}
                    PRIORITY = {priority}

                    def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.Name:
                        if updated.value == "x":
                            return updated.with_changes(value="x_refined")
                        return updated
                '''
            )
        )
        return module_name

    return _write

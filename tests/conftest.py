from __future__ import annotations

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

_module_counter = itertools.count()


@pytest.fixture
def write_codemod(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., str]]:
    """
    Factory writing a real codemod module to disk, as a user's ``codemod_paths`` entry would hold.

    Returns the module name. Each module gets a unique name and is dropped from ``sys.modules`` on
    teardown, because loading it from a path registers it there.
    """
    monkeypatch.setattr(sys, "path", list(sys.path))
    written: list[str] = []

    def _write(directory: Path, *, name: str, priority: int = 0) -> str:
        module_name = f"refine_test_codemod_{next(_module_counter)}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{module_name}.py").write_text(
            textwrap.dedent(
                f'''
                from refine.abc import BaseCodemod


                class CustomCodemod(BaseCodemod):
                    """Custom codemod {name}."""

                    NAME = {name!r}
                    PRIORITY = {priority}
                '''
            )
        )
        written.append(module_name)
        return module_name

    yield _write

    for module_name in written:
        sys.modules.pop(module_name, None)

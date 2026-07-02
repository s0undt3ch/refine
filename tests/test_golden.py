"""
End-to-end golden test.

Runs the full Processor (the same code path as the CLI) over copies of every
fixture file and asserts byte-identical output with the recorded `.updated`
fixtures. This is the parity gate for execution-model changes: gates, metadata
resolution, wrapper sharing and caching must never alter output.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from refine.config import Config
from refine.processor import Processor
from refine.registry import Registry

TESTS_DIR = Path(__file__).parent

CORPUS = [
    # (fixture directory, codemod name)
    (TESTS_DIR / "mods" / "cli" / "files" / "flags", "cli-dashes-over-underscores"),
    (TESTS_DIR / "mods" / "sql" / "files" / "fmt", "sqlfmt"),
]


def _dedent(path: Path) -> str:
    contents = path.read_text()
    contents = contents.removeprefix("\n")
    return textwrap.dedent(contents)


def _collect_cases():
    for fixture_dir, codemod_name in CORPUS:
        for original in sorted(fixture_dir.glob("*.py")):
            if original.stem.endswith(".updated"):
                continue
            updated = original.with_stem(f"{original.stem}.updated")
            if not updated.exists():
                continue
            yield pytest.param(original, updated, codemod_name, id=f"{codemod_name}/{original.stem}")


@pytest.mark.parametrize(("original", "updated", "codemod_name"), list(_collect_cases()))
def test_golden_end_to_end(tmp_path, original, updated, codemod_name):
    target = tmp_path / original.name
    target.write_text(_dedent(original))

    registry = Registry()
    registry.load([])
    codemods = list(registry.codemods(select_codemods=[codemod_name]))
    assert codemods, f"codemod {codemod_name} not found"

    config = Config.from_dict(
        {
            "repo_root": str(tmp_path),
            "process_pool_size": 1,
            "hide_progress": True,
            "sqlfmt": {"dialect": "mysql"},
        }
    )
    processor = Processor(config=config, registry=registry, codemods=codemods)
    result = processor.process([target])

    assert result.failures == 0
    assert target.read_text() == _dedent(updated)

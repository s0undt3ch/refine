"""
CI related utilities.
"""

from __future__ import annotations

import json
import os
import tomllib
from enum import StrEnum
from pathlib import Path

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from toolr import Context
from toolr import command_group

group = command_group("ci", "CI utilities", docstring=__doc__)

# Every CPython the test matrix covers. The first entry must match the
# `requires-python` floor in the root `pyproject.toml`.
TEST_PYTHONS = ["3.11", "3.12", "3.13", "3.14", "3.15"]

LINUX = "ubuntu-latest"
NARROW_OSES = ("windows-latest", "macos-latest")


class Workflow(StrEnum):
    """The matrix shape to emit."""

    CI = "ci"
    FULL = "full"


def python_floor(pyproject: Path) -> str:
    """Return the ``3.N`` floor of ``project.requires-python`` in ``pyproject``."""
    requires_python = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["requires-python"]
    for specifier in SpecifierSet(requires_python):
        release = Version(specifier.version).release
        if specifier.operator == ">=" and len(release) > 1:
            return f"{release[0]}.{release[1]}"
    msg = f"requires-python {requires_python!r} has no `>=3.N` clause"
    raise ValueError(msg)


def select_workflow() -> tuple[Workflow, str]:
    """Pick the matrix shape from the GitHub event context, with the reason for it."""
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name == "pull_request":
        return Workflow.CI, "pull request — every Python on Linux, oldest and newest on Windows and macOS."
    return Workflow.FULL, f"event=`{event_name or '(unset)'}` — every Python on every OS."


def build_test_matrix(workflow: Workflow) -> list[dict[str, str]]:
    """Return the ``{os, python-version}`` entries of the test matrix."""
    narrow_pythons = TEST_PYTHONS if workflow == Workflow.FULL else [TEST_PYTHONS[0], TEST_PYTHONS[-1]]
    matrix = [{"os": LINUX, "python-version": version} for version in TEST_PYTHONS]
    matrix.extend({"os": os_name, "python-version": version} for os_name in NARROW_OSES for version in narrow_pythons)
    return matrix


@group.command
def generate_build_matrix(ctx: Context, workflow: Workflow | None = None) -> None:
    """
    Emit the test matrix consumed by the CI workflow.

    Writes the `test-matrix` key to `$GITHUB_OUTPUT`: a JSON list of
    `{"os": ..., "python-version": ...}` objects for the `tests` job's
    `matrix.include`. Also writes the chosen matrix and the reason for it
    to `$GITHUB_STEP_SUMMARY`.

    Args:
        workflow: Matrix shape to emit. When omitted, pull requests get the
            `ci` shape and every other event gets the `full` shape.
    """
    floor = python_floor(ctx.repo_root / "pyproject.toml")
    if floor != TEST_PYTHONS[0]:
        ctx.error(f"TEST_PYTHONS starts at {TEST_PYTHONS[0]} but requires-python's floor is {floor}")
        ctx.exit(1)

    if workflow is None:
        workflow, reason = select_workflow()
    else:
        reason = f"caller forced `--workflow {workflow}`."

    github_output = os.environ.get("GITHUB_OUTPUT")
    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_output is None or github_step_summary is None:
        ctx.error("GITHUB_OUTPUT and GITHUB_STEP_SUMMARY must both be set")
        ctx.exit(1)

    matrix = build_test_matrix(workflow)
    with open(github_step_summary, "a", encoding="utf-8") as wfh:
        wfh.write(f"## Test matrix ({workflow})\n\n_{reason}_\n\n")
        wfh.write("| OS | Python |\n|----|--------|\n")
        wfh.writelines(f"| {entry['os']} | {entry['python-version']} |\n" for entry in matrix)

    ctx.info(f"Emitting {len(matrix)} test jobs for workflow={workflow!s} ({reason})")
    with open(github_output, "a", encoding="utf-8") as wfh:
        wfh.write(f"test-matrix={json.dumps(matrix)}\n")

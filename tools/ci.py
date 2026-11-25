"""
CI related utilities.
"""

from __future__ import annotations

import json
import os

from toolr import Context
from toolr import command_group

group = command_group("ci", "CI utilities", docstring=__doc__)

# Every CPython the test matrix covers, oldest first. Keep the first entry
# on the `requires-python` floor in the root `pyproject.toml`.
TEST_PYTHONS = ["3.11", "3.12", "3.13", "3.14", "3.15"]


def build_test_matrix(*, narrow: bool) -> list[dict[str, str]]:
    """
    Return the ``{os, python-version}`` entries of the test matrix.

    Linux always gets every Python. With ``narrow``, Windows and macOS get only the oldest and newest.
    """
    other_pythons = [TEST_PYTHONS[0], TEST_PYTHONS[-1]] if narrow else TEST_PYTHONS
    matrix = [{"os": "ubuntu-latest", "python-version": version} for version in TEST_PYTHONS]
    matrix.extend(
        {"os": os_name, "python-version": version}
        for os_name in ("windows-latest", "macos-latest")
        for version in other_pythons
    )
    return matrix


@group.command
def generate_build_matrix(ctx: Context) -> None:
    """
    Emit the test matrix consumed by the CI workflow.

    Writes the `test-matrix` key to `$GITHUB_OUTPUT`: a JSON list of
    `{"os": ..., "python-version": ...}` objects for the `tests` job's
    `matrix.include`. Pull requests get every Python on Linux but only the
    oldest and newest on Windows and macOS. Every other event gets every
    Python on every OS. The matrix also goes to `$GITHUB_STEP_SUMMARY`
    when that is set.
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output is None:
        ctx.error("GITHUB_OUTPUT is not set")
        ctx.exit(1)

    narrow = os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    matrix = build_test_matrix(narrow=narrow)
    ctx.info(f"Emitting {len(matrix)} test jobs ({'narrow' if narrow else 'full'} matrix)")
    with open(github_output, "a", encoding="utf-8") as wfh:
        wfh.write(f"test-matrix={json.dumps(matrix)}\n")

    github_step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_step_summary is not None:
        with open(github_step_summary, "a", encoding="utf-8") as wfh:
            wfh.write(f"## Test matrix ({'narrow, pull request' if narrow else 'full'})\n\n")
            wfh.write("| OS | Python |\n|----|--------|\n")
            wfh.writelines(f"| {entry['os']} | {entry['python-version']} |\n" for entry in matrix)

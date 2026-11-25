from __future__ import annotations

import json
from pathlib import Path

import pytest
from toolr.testing import make_context

from tools.ci import TEST_PYTHONS
from tools.ci import Workflow
from tools.ci import generate_build_matrix


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(f'[project]\nrequires-python = ">={TEST_PYTHONS[0]},<4"\n')
    return tmp_path


@pytest.fixture
def github_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return output, summary


def _emitted_matrix(output: Path) -> list[dict[str, str]]:
    key, value = output.read_text().strip().split("=", 1)
    assert key == "test-matrix"
    return json.loads(value)


def _pythons_by_os(matrix: list[dict[str, str]]) -> dict[str, list[str]]:
    by_os: dict[str, list[str]] = {}
    for entry in matrix:
        by_os.setdefault(entry["os"], []).append(entry["python-version"])
    return by_os


def test_pull_request_narrows_windows_and_macos(repo_root, github_files, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    output, summary = github_files

    generate_build_matrix(make_context(repo_root))

    narrow = [TEST_PYTHONS[0], TEST_PYTHONS[-1]]
    assert _pythons_by_os(_emitted_matrix(output)) == {
        "ubuntu-latest": TEST_PYTHONS,
        "windows-latest": narrow,
        "macos-latest": narrow,
    }
    assert "## Test matrix (ci)" in summary.read_text()


@pytest.mark.parametrize("event_name", ["push", "workflow_dispatch", ""])
def test_other_events_get_the_full_matrix(repo_root, github_files, monkeypatch, event_name):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event_name)
    output, _ = github_files

    generate_build_matrix(make_context(repo_root))

    assert _pythons_by_os(_emitted_matrix(output)) == {
        "ubuntu-latest": TEST_PYTHONS,
        "windows-latest": TEST_PYTHONS,
        "macos-latest": TEST_PYTHONS,
    }


def test_workflow_argument_overrides_the_event(repo_root, github_files, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    output, _ = github_files

    generate_build_matrix(make_context(repo_root), workflow=Workflow.FULL)

    assert len(_emitted_matrix(output)) == 3 * len(TEST_PYTHONS)


def test_floor_mismatch_fails(repo_root, github_files):
    (repo_root / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.10"\n')
    ctx = make_context(repo_root)

    with pytest.raises(SystemExit) as exc:
        generate_build_matrix(ctx)

    assert exc.value.code == 1
    assert "requires-python's floor is 3.10" in ctx.stderr
    assert not github_files[0].exists()


def test_missing_github_output_fails(repo_root, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with pytest.raises(SystemExit) as exc:
        generate_build_matrix(make_context(repo_root))

    assert exc.value.code == 1

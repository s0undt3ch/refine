from __future__ import annotations

import json
from pathlib import Path

import pytest
from toolr.testing import make_context

from tools.ci import TEST_PYTHONS
from tools.ci import generate_build_matrix


@pytest.fixture
def github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return output


def _pythons_by_os(output: Path) -> dict[str, list[str]]:
    key, value = output.read_text().strip().split("=", 1)
    assert key == "test-matrix"
    by_os: dict[str, list[str]] = {}
    for entry in json.loads(value):
        by_os.setdefault(entry["os"], []).append(entry["python-version"])
    return by_os


def test_pull_request_narrows_windows_and_macos(tmp_path, github_output, monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    summary = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    generate_build_matrix(make_context(tmp_path))

    narrow = [TEST_PYTHONS[0], TEST_PYTHONS[-1]]
    assert _pythons_by_os(github_output) == {
        "ubuntu-latest": TEST_PYTHONS,
        "windows-latest": narrow,
        "macos-latest": narrow,
    }
    assert "## Test matrix (narrow, pull request)" in summary.read_text()


@pytest.mark.parametrize("event_name", ["push", "workflow_dispatch", ""])
def test_other_events_get_the_full_matrix(tmp_path, github_output, monkeypatch, event_name):
    monkeypatch.setenv("GITHUB_EVENT_NAME", event_name)

    generate_build_matrix(make_context(tmp_path))

    assert _pythons_by_os(github_output) == {
        "ubuntu-latest": TEST_PYTHONS,
        "windows-latest": TEST_PYTHONS,
        "macos-latest": TEST_PYTHONS,
    }


def test_missing_github_output_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    with pytest.raises(SystemExit) as exc:
        generate_build_matrix(make_context(tmp_path))

    assert exc.value.code == 1

from __future__ import annotations

import pathlib

import pytest

from refine.mods.cli.flags import CliDashes
from refine.mods.cli.flags import CliDashesConfig
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "flags"


def _get_case_id(case: Modcase) -> str:
    return case.name


def _get_cases() -> list[Modcase]:
    cases = []
    for path in FILES_PATH.glob("*.py"):
        if ".updated." in path.name:
            # We don't want to collect the .updated files
            continue
        cases.append(
            Modcase(
                path=path,
                codemod=CliDashes,
                codemod_config=CliDashesConfig(),
            )
        )
    return cases


@pytest.fixture(params=_get_cases(), ids=_get_case_id)
def dash_case(request) -> Modcase:
    return request.param


def test_cli_flags(dash_case: Modcase):
    dash_case.assert_codemod()


def test_should_process_true_for_underscore_flag():
    assert CliDashes.should_process('parser.add_argument("--dry_run")\n', "x.py") is True


def test_should_process_false_without_underscore_flags():
    assert CliDashes.should_process('parser.add_argument("--dry-run")\n', "x.py") is False


def test_should_process_true_for_leading_underscore_flag():
    assert CliDashes.should_process('parser.add_argument("--_debug")\n', "x.py") is True


def test_should_process_true_for_trailing_underscore_flag():
    assert CliDashes.should_process('parser.add_argument("--verbose_")\n', "x.py") is True

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

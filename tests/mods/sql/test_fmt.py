from __future__ import annotations

import pathlib

import pytest

from refine.mods.sql.fmt import FormatSQL
from refine.mods.sql.fmt import FormatSQLConfig
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "fmt"


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
                codemod=FormatSQL,
                codemod_config=FormatSQLConfig(),
            )
        )
    return cases


@pytest.fixture(params=_get_cases(), ids=_get_case_id)
def fmt_case(request) -> Modcase:
    return request.param


def test_format_sql(fmt_case: Modcase):
    fmt_case.assert_codemod()

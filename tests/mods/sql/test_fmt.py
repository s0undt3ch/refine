from __future__ import annotations

import pathlib

import libcst as cst
import pytest
from libcst.codemod import CodemodContext

from refine.exc import InvalidConfigError
from refine.mods.sql import sqruff_backend
from refine.mods.sql.fmt import FormatSQL
from refine.mods.sql.fmt import FormatSQLConfig
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "fmt"
SQRUFF_FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "fmt-sqruff"


def _get_case_id(case: Modcase) -> str:
    return case.name


def _get_cases(files_path: pathlib.Path, config: FormatSQLConfig) -> list[Modcase]:
    cases = []
    for path in files_path.glob("*.py"):
        if ".updated." in path.name:
            # We don't want to collect the .updated files
            continue
        cases.append(
            Modcase(
                path=path,
                codemod=FormatSQL,
                codemod_config=config,
            )
        )
    return cases


@pytest.fixture(
    params=_get_cases(FILES_PATH, FormatSQLConfig(backend="sqlfluff", dialect="mysql")),
    ids=_get_case_id,
)
def fmt_case(request) -> Modcase:
    return request.param


@pytest.fixture(
    params=_get_cases(SQRUFF_FILES_PATH, FormatSQLConfig(backend="sqruff", dialect="mysql")),
    ids=_get_case_id,
)
def fmt_sqruff_case(request) -> Modcase:
    return request.param


def test_format_sql(fmt_case: Modcase):
    fmt_case.assert_codemod()


def test_format_sql_sqruff(fmt_sqruff_case: Modcase):
    fmt_sqruff_case.assert_codemod()


def test_should_process_true_for_sql_text():
    src = 'QUERY = "SELECT name FROM users WHERE id = 1"\n'
    assert FormatSQL.should_process(src, "x.py") is True


def test_should_process_false_without_sql_keywords():
    src = "def add(a, b):\n    return a + b\n"
    assert FormatSQL.should_process(src, "x.py") is False


def test_should_process_true_for_multiline_update_set():
    src = 'QUERY = """\nupdate foo\nset bar = 1\nwhere baz = 2\n"""\n'
    assert FormatSQL.should_process(src, "x.py") is True


def test_default_backend_is_sqruff():
    assert FormatSQLConfig().backend == "sqruff"


def test_sqlfluff_backend_is_accepted():
    assert FormatSQLConfig(backend="sqlfluff").backend == "sqlfluff"


def test_unknown_backend_is_rejected():
    with pytest.raises(InvalidConfigError):
        FormatSQLConfig(backend="handwriting")


def test_backend_failure_warns_and_leaves_query_unchanged(monkeypatch):
    monkeypatch.setattr(sqruff_backend, "format_sql", lambda *_args, **_kwargs: None)

    source = 'QUERY = "SELECT a FROM b"\n'
    context = CodemodContext(filename="x.py")
    mod = FormatSQL(context=context, config=FormatSQLConfig(backend="sqruff"))
    mod.transform_module(cst.parse_module(source))

    assert context.warnings, "backend failure must surface via context.warnings"
    assert any("could not format" in w for w in context.warnings)

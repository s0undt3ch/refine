from __future__ import annotations

import pathlib

import libcst as cst
import msgspec
import pytest
from libcst.codemod import CodemodContext

from refine.mods.sql import sqruff_backend
from refine.mods.sql.fmt import FormatSQL
from refine.mods.sql.fmt import FormatSQLConfig
from refine.mods.sql.fmt import SqlBackend
from refine.testing import Modcase

FILES_PATH = pathlib.Path(__file__).parent.resolve() / "files" / "fmt"

# Shared input files; the expected output for each lives in a per-backend
# subdirectory (``fmt/sqlfluff/`` and ``fmt/sqruff/``).
SQL_INPUTS = sorted(path for path in FILES_PATH.glob("*.py") if not path.stem.endswith(".updated"))


@pytest.fixture(params=[SqlBackend.SQLFLUFF, SqlBackend.SQRUFF], ids=lambda backend: backend.value)
def fmt_sql_config(request: pytest.FixtureRequest) -> FormatSQLConfig:
    return FormatSQLConfig(backend=request.param, dialect="mysql")


@pytest.fixture(params=SQL_INPUTS, ids=lambda path: path.stem)
def fmt_case(request: pytest.FixtureRequest, fmt_sql_config: FormatSQLConfig) -> Modcase:
    input_path: pathlib.Path = request.param
    expected_path = FILES_PATH / fmt_sql_config.backend.value / f"{input_path.stem}.updated.py"
    return Modcase(
        path=input_path,
        updated_path=expected_path,
        codemod=FormatSQL,
        codemod_config=fmt_sql_config,
    )


def test_format_sql(fmt_case: Modcase):
    fmt_case.assert_codemod()


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
    assert FormatSQLConfig().backend is SqlBackend.SQRUFF


def test_sqlfluff_backend_is_accepted():
    assert msgspec.convert({"backend": "sqlfluff"}, FormatSQLConfig).backend is SqlBackend.SQLFLUFF


def test_unknown_backend_is_rejected():
    # Validation happens at the deserialization boundary Processor uses to build
    # codemod configs; Processor surfaces this ValidationError as an InvalidConfigError.
    with pytest.raises(msgspec.ValidationError):
        msgspec.convert({"backend": "handwriting"}, FormatSQLConfig)


def test_backend_failure_warns_and_leaves_query_unchanged(monkeypatch):
    monkeypatch.setattr(sqruff_backend, "format_sql", lambda *_args, **_kwargs: None)

    source = 'QUERY = "SELECT a FROM b"\n'
    context = CodemodContext(filename="x.py")
    mod = FormatSQL(context=context, config=FormatSQLConfig(backend=SqlBackend.SQRUFF))
    mod.transform_module(cst.parse_module(source))

    assert context.warnings, "backend failure must surface via context.warnings"
    assert any("could not format" in w for w in context.warnings)

from __future__ import annotations

import pytest

from refine.mods.sql import sqruff_backend

pytestmark = pytest.mark.skipif(sqruff_backend.find_sqruff() is None, reason="sqruff binary not available")


def test_formats_simple_query():
    result = sqruff_backend.format_sql("select a,b from t where x=1", dialect="ansi", max_line_length=120)
    assert result is not None
    assert "select" in result
    assert result == result.rstrip("\n")


def test_unparsable_returns_none():
    result = sqruff_backend.format_sql("THIS IS NOT ((( SQL", dialect="ansi", max_line_length=120)
    assert result is None


def test_max_line_length_is_respected():
    long_query = "select " + ", ".join(f"column_number_{i}" for i in range(12)) + " from a_table"  # noqa: S608
    result = sqruff_backend.format_sql(long_query, dialect="ansi", max_line_length=60)
    assert result is not None
    assert all(len(line) <= 60 for line in result.splitlines())


def test_already_clean_query_is_returned_unchanged():
    query = "select a, b\nfrom t\nwhere x = 1\n"
    result = sqruff_backend.format_sql(query.rstrip("\n"), dialect="ansi", max_line_length=120)
    assert result is not None
    assert result == query.rstrip("\n")


def test_config_dir_overrides_bundled_config(tmp_path):
    config_dir = tmp_path
    (config_dir / ".sqruff").write_text("[sqruff]\ndialect = ansi\nmax_line_length = 120\n")
    result = sqruff_backend.format_sql(
        "select a,b from t",
        dialect="ansi",
        max_line_length=120,
        config_dir=config_dir,
    )
    assert result is not None
    assert "select a, b from t" in result


def test_find_sqruff_returns_a_path():
    binary = sqruff_backend.find_sqruff()
    assert binary is not None

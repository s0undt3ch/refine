from __future__ import annotations

import pathlib

import pytest

from refine.mods.sql.utils import match_sql_query_string

THIS_FILE_DIR = pathlib.Path(__file__).resolve().parent
FILES_PATH = THIS_FILE_DIR / "files" / "fmt"


@pytest.mark.parametrize(
    ("query", "expected_match"),
    [
        ("SELECT * FROM users", True),
        ("SELECT * FROM users WHERE id = 1", True),
        ("INSERT INTO users (name) VALUES ('John')", True),
        ("UPDATE users SET name = 'John' WHERE id = 1", True),
        ("DELETE FROM users WHERE id = 1", True),
        ("-- This is a comment\nSELECT * FROM users", True),
        ("/* This is a comment */ SELECT * FROM users", True),
        ("This is not a SQL query", False),
        (
            """
            exists (select 0
                        from accounts_company%sauth a
                        where a.company_id = t.company_id);""",
            True,
        ),
        (
            """
                /* customers_search #%(company)s */
                select user_id
                from metrics_customer
                where company_id = %(company)s
                and (lower(email) like concat('%%', %(query)s, '%%')
                        or lower(display_name) like concat('%%', %(query)s, '%%'))
            """,
            True,
        ),
    ],
)
def test_match_sql_query_string(query: str, expected_match: bool):
    """
    Check if a string is a SQL query.
    """
    if expected_match:
        assert match_sql_query_string(query) is not None
    else:
        assert match_sql_query_string(query) is None


def test_match_sql_query_string_groups():
    query = """
        /* customers_search #%(company)s */
        select user_id
        from metrics_customer
        where company_id = %(company)s
        and (lower(email) like concat('%%', %(query)s, '%%')
                or lower(display_name) like concat('%%', %(query)s, '%%'))
    """
    match = match_sql_query_string(query)
    assert match.group("comment") is not None
    assert match.group("query") is not None

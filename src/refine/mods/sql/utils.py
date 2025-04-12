"""
SQL mod related utility functions.
"""

from __future__ import annotations

import logging
import re
from functools import cache

import libcst as cst

from refine import utils

log = logging.getLogger(__name__)


SQL_RE = re.compile(
    r"""
    ^
    \s*
    (?P<comment>
        # Match single-line and multi-line comments
        (?:--[^\n]*|/\*.*?\*/)\s*
    )?
    (?P<query>
        # Match common SQL keywords
        (?:
            exists\s*\(
            |
            select\s.*from\s
            |
            delete\s+from\s
            |
            insert\s+into\s.*values\s
            |
            update\s.*set\s
        ).*
    )
    """,
    re.IGNORECASE | re.DOTALL | re.MULTILINE | re.VERBOSE,
)


def is_sql_query(node: cst.CSTNode) -> bool:
    return match_sql_query(node) is not None


def match_sql_query(node: cst.CSTNode) -> re.Match[str] | None:
    """
    Check if a node is a SQL query.
    """
    if not isinstance(node, cst.SimpleString):
        return None
    evaluated_string = utils.evaluated_string(node)
    if evaluated_string is None:
        # We will only process strings
        return None
    return match_sql_query_string(evaluated_string)


@cache
def match_sql_query_string(string: str) -> re.Match[str] | None:
    """
    Check if a string is a SQL query.
    """
    return SQL_RE.match(string)

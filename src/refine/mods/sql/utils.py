"""
SQL mod related utility functions.
"""

from __future__ import annotations

import logging
import re

import libcst as cst

from refine import utils

log = logging.getLogger(__name__)

SQL_RE = re.compile(
    r"""
    .*
    (
        # Match single-line and multi-line comments
        (?:--.*?$|/\*.*?\*)?
        # Match common SQL keywords
        (?:
            select\s.*from\s
            |
            delete\s+from\s
            |
            insert\s+into\s.*values\s
            |
            update\s.*set\s
        )+
    )
    .*
    """,
    re.IGNORECASE | re.DOTALL | re.MULTILINE | re.VERBOSE,
)


def is_sql_query(node: cst.CSTNode) -> bool:
    if not isinstance(node, cst.SimpleString):
        return False
    evaluated_string = utils.evaluated_string(node)
    if not isinstance(evaluated_string, str):
        # We will only process strings
        return False
    return SQL_RE.match(utils.evaluated_string(node)) is not None

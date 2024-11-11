"""
Codemod utilities.
"""

import re
from ast import literal_eval
from functools import cache

from libcst import SimpleString

INDENT_RE = re.compile(r"(?P<indent>[ ]+)(.*)")


@cache
def evaluated_string(node: SimpleString) -> str:
    """
    Evaluate a SimpleString node into a python string.
    """
    return literal_eval(node.value)


@cache
def find_indent(text: str) -> str:
    """
    Find the indentation of a string.
    """
    starting_newline: str = text.startswith("\n") and "\n" or ""
    indent = ""
    if starting_newline:
        text = text[1:]
    match = INDENT_RE.match(text)
    if match:
        indent = match.group("indent")
    return indent

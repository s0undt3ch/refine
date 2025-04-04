"""
Refine utilities.
"""

from __future__ import annotations

import re
from ast import literal_eval
from functools import cache

import libcst as cst

INDENT_RE = re.compile(r"(?P<indent>[ ]+)(.*)")


@cache
def evaluated_string(node: cst.SimpleString) -> str:
    """
    Evaluate a SimpleString node into a python string.
    """
    return literal_eval(node.value)


def remove_leading_whitespace(string: str) -> str:
    return "\n".join([line.lstrip() for line in string.splitlines()])


def get_full_module_name(module: cst.Module) -> str:
    """
    Return a fully qualified name of a module.
    """
    parts: list[str] = []
    while isinstance(module, cst.Attribute):
        parts.insert(0, module.attr.value)
        module = module.value
    if isinstance(module, cst.Name):
        parts.insert(0, module.value)
    return ".".join(parts)

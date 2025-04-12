"""
Refine utilities.
"""

from __future__ import annotations

from ast import literal_eval
from functools import cache

import libcst as cst


@cache
def evaluated_string(node: cst.SimpleString) -> str | None:
    """
    Evaluate a SimpleString node into a python string.
    """
    try:
        evaluated_string = literal_eval(node.value)
    except Exception:  # noqa: BLE001
        # We can't evaluate the string, return None
        return None
    else:
        if not isinstance(evaluated_string, str):
            # We only want strings
            return None
        return evaluated_string


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

"""
Codemod utilities.
"""

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

r"""
This codemod enforces the use of dashes over underscores in CLI arguments.

For example, it will transform this code:
```python
parser.add_argument("--a_command")
```
into this code:
```python
parser.add_argument("--a-command")
```

It handles all CLI arguments by looking for strings matching the pattern `--[\w]+_[\w]+` that are arguments to a
function call.
"""

from __future__ import annotations

import logging
from typing import cast

import libcst as cst
from libcst import matchers as m

from refine import utils
from refine.abc import BaseCodemod
from refine.abc import BaseConfig

log = logging.getLogger(__name__)


class CliDashesConfig(BaseConfig, frozen=True):
    """
    Config for the `CliDashes` codemod.
    """


class CliDashes(BaseCodemod):
    """
    Replace `_` with `-`, ie, `--a-command` instead of `--a_command` in CLI commands.
    """

    NAME = "cli-dashes-over-underscores"
    CONFIG_CLS = CliDashesConfig

    @m.leave(m.Arg(value=m.SimpleString()))
    def leave_simple_string_arg(self, original: cst.Arg, updated: cst.Arg) -> cst.Arg:
        # Parse the string literal to get the unquoted value
        unquoted = utils.evaluated_string(updated.value)
        if unquoted is None:
            # This wasn't a string, apparently!?
            return updated

        # Fast path: if string doesn't start with '--', skip it
        if not unquoted.startswith("--") or "_" not in unquoted:
            return updated

        # Convert underscores to dashes
        replaced = unquoted.replace("_", "-")
        if replaced == unquoted:
            return updated

        # Reconstruct the string with the original quote style
        quote = cast("cst.SimpleString", original.value).quote
        return updated.with_changes(
            value=cst.SimpleString(
                value=f"{quote}{replaced}{quote}",
                lpar=original.value.lpar,
                rpar=original.value.rpar,
            )
        )

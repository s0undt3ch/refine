"""
This codemod enforces the use of dashes over underscores in CLI arguments of [ArgumentParser][argparse.ArgumentParser].

For example, it will transform this code:
```python
parser.add_argument("--a_command")
```
into this code:
```python
parser.add_argument("--a-command")
```
"""

from __future__ import annotations

import logging
import pathlib
from ast import literal_eval
from typing import TYPE_CHECKING
from typing import cast

import libcst as cst
import libcst.matchers as m
from libcst.codemod import SkipFile

from refine.abc import BaseCodemod
from refine.abc import BaseConfig

log = logging.getLogger(__name__)


class CliDashesConfig(BaseConfig):
    django_base_command_package: str = "django.core.management"
    django_base_command_class_name: str = "BaseCommand"


class CliDashes(BaseCodemod):
    """
    Replace `_` with `-`, ie, `--a-command` instead of `--a_command` in CLI commands.

    This works if the parser argument is typed and only for ArgumentParser. `def foo(parser: ArgumentParser)`.
    """

    NAME = "cli-dashes-over-underscores"
    CONFIG_CLS = CliDashesConfig

    def __post_codemod_init__(self) -> None:
        """
        Additional class setup.
        """
        self.typed_parameters: dict[str, str] = {}
        self.typed_assignments: dict[str, str] = {}

    def visit_Module(self, mod: cst.Module) -> bool:
        filename: str | None = self.context.filename
        if TYPE_CHECKING:
            assert filename is not None
        if pathlib.Path(filename).name.startswith("test_"):
            skip_reason = "Not touching test files"
            raise SkipFile(skip_reason)
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # Collect type annotations of parameters
        self.typed_parameters = {}
        for param in node.params.params:
            if param.annotation:
                param_name = param.name.value
                annotation = param.annotation.annotation
                if isinstance(annotation, cst.Name) and annotation.value == "ArgumentParser":
                    self.typed_parameters[param_name] = annotation.value

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef) -> cst.FunctionDef:
        # Clear state when leaving the function
        self.typed_parameters = {}
        self.typed_assignments = {}
        return updated

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if isinstance(node.target, cst.Name):
            var_name = node.target.value
            annotation = node.annotation.annotation
            if isinstance(annotation, cst.Name) and annotation.value == "ArgumentParser":
                self.typed_assignments[var_name] = annotation.value

    def visit_Assign(self, node: cst.Assign) -> None:
        # NOTE: we're not taking into account import aliases
        assign_target: cst.AssignTarget
        for assign_target in node.targets:
            if not isinstance(assign_target.target, cst.Name):
                # We only want to handle simple assignments:
                # var_a = value_a
                # We're not handling assignment expansion, ie
                # var_a, var_b = value_a, value_b
                continue
            target: cst.Name = cast("cst.Name", assign_target.target)
            var_name = target.value
            if m.matches(
                node.value,
                m.OneOf(
                    # blah = ArgumentParser
                    m.Call(func=m.Name("ArgumentParser")),
                    # blah = argparse.ArgumentParser
                    m.Call(func=m.Attribute(value=m.Name("argparse"), attr=m.Name("ArgumentParser"))),
                ),
            ):
                self.typed_assignments[var_name] = "ArgumentParser"

    def leave_Call(self, original: cst.Call, updated: cst.Call) -> cst.Call:
        # Check for `<something>.add_argument(...)` calls
        if m.matches(
            original.func,
            m.Attribute(attr=m.Name("add_argument"), value=m.Name()),
        ):
            # The `<something>` in `<something>.add_argument`
            caller_func_attribute = cast("cst.Attribute", original.func)
            caller_func_attribute_name = cast("cst.Name", caller_func_attribute.value)
            caller_name = caller_func_attribute_name.value

            # Verify if the caller object is typed as ArgumentParser
            if caller_name not in self.typed_parameters and caller_name not in self.typed_assignments:
                return updated

            args: list[cst.Arg] = []
            for arg in updated.args:
                if not isinstance(arg.value, cst.SimpleString):
                    args.append(arg)
                    continue
                simple_string = arg.value
                flag = literal_eval(simple_string.value)
                if not flag.startswith("--"):
                    args.append(arg)
                    continue
                if "_" not in flag:
                    args.append(arg)
                    continue
                updated_flag_value = f"{simple_string.quote}{flag.replace('_', '-')}{simple_string.quote}"
                updated_simple_string = simple_string.with_changes(value=updated_flag_value)
                updated_arg = arg.with_changes(value=updated_simple_string)
                args.append(updated_arg)
            return updated.with_changes(args=args)
        return updated

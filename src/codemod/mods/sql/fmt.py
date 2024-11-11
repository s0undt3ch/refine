import pathlib
import textwrap
from functools import cache
from typing import TYPE_CHECKING
from typing import cast

import libcst as cst
import libcst.matchers as m
import sqlfluff.api
from libcst.codemod import SkipFile
from sqlfluff.api.simple import get_simple_config
from sqlfluff.core import FluffConfig

from codemod import utils
from codemod.abc import BaseCodemod
from codemod.abc import BaseConfig

from .utils import is_sql_query

BUILNTIN_SQLFLUFF_CONFIG_FILE = pathlib.Path(__file__).parent / ".sqlfluff"


class FormatSQLConfig(BaseConfig):
    dialect: str = "ansi"
    sqlfluff_config_file: str = str(BUILNTIN_SQLFLUFF_CONFIG_FILE)


class FormatSQL(BaseCodemod[FormatSQLConfig]):
    NAME = "sqlfmt"
    CONFIG_CLS = FormatSQLConfig
    DESCRIPTION: str = "Format SQL queries using the `sqlfluff` python package"

    def visit_Module(self, mod: cst.Module) -> bool:
        filename: str | None = self.context.filename
        if TYPE_CHECKING:
            assert filename is not None
        if pathlib.Path(filename).name.startswith("test_"):
            skip_reason = "Not touching test files"
            raise SkipFile(skip_reason)
        return True

    def leave_Assign(self, original: cst.Assign, updated: cst.Assign) -> cst.Assign:
        extracts = m.extract(
            original,
            m.Assign(
                value=m.SaveMatchedNode(  # type: ignore[arg-type]
                    m.MatchIfTrue(is_sql_query),
                    "query",
                ),
            ),
        )
        if extracts:
            string_node = cast(cst.SimpleString, extracts["query"])
            query = self.__format_sql(utils.evaluated_string(string_node))
            if string_node.quote.startswith("'"):
                return updated.with_changes(
                    value=string_node.__class__(
                        f"""{string_node.quote}{query}{string_node.quote}"""
                    )
                )
            return updated.with_changes(
                value=string_node.__class__(f"""{string_node.quote}{query}{string_node.quote}""")
            )
        return updated

    def leave_Call(self, original: cst.Call, updated: cst.Call) -> cst.Call:
        args = []
        matched = False
        for arg in original.args:
            if not isinstance(arg.value, cst.SimpleString):
                args.append(arg)
                continue
            if not is_sql_query(arg.value):
                args.append(arg)
                continue

            matched = True
            string_node = cast(cst.SimpleString, arg.value)
            unquoted_string = utils.evaluated_string(string_node)
            indent = utils.find_indent(unquoted_string)
            query = self.__format_sql(unquoted_string)
            if "\n" in query and string_node.quote in ('"""', "'''"):
                last_line = f"{indent}"
            else:
                last_line = ""
            if string_node.quote.startswith("'"):
                args.append(
                    arg.with_changes(
                        value=string_node.__class__(
                            f"""{string_node.quote}{query}{last_line}{string_node.quote}"""
                        )
                    )
                )
            else:
                args.append(
                    arg.with_changes(
                        value=string_node.__class__(
                            f"""{string_node.quote}{query}{last_line}{string_node.quote}"""
                        )
                    )
                )
        if matched:
            return updated.with_changes(args=args)
        return updated

    @cache  # noqa: B019
    def __get_sqlfluff_config(self) -> FluffConfig:
        # Load config and cache it
        return get_simple_config(config_path=str(self.config.sqlfluff_config_file))

    def __format_sql(self, query: str) -> str:
        # We want a copy of the config so that we can modify it
        config = self.__get_sqlfluff_config().copy()
        starting_newline: str = query.startswith("\n") and "\n" or ""
        indent = utils.find_indent(query)
        if starting_newline:
            query = query[1:]

        # Since we will need to indent code, and still want sqlfluff to respect it's max width setting
        config.set_value("max_linelength", config.get("max_line_length") - len(indent))

        formated = sqlfluff.api.fix(
            query,
            dialect="mysql",
            config=config,
            fix_even_unparsable=False,
        )
        ending_newline: str = (
            (starting_newline or ("\n" in formated and not formated.endswith("\n"))) and "\n" or ""
        )
        indented_query = (
            f"{starting_newline}{textwrap.indent(formated, prefix=indent)}{ending_newline}"
        )
        if indented_query.count("\n") == 1 and indented_query.endswith("\n"):
            # If we really only have
            return indented_query[:-1]
        if indented_query.endswith("\n\n"):
            # We don't really want two new lines at the end
            return indented_query[:-1]
        return indented_query

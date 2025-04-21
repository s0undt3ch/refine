"""
SQL Formatting codemod.

This codemod uses the [sqlfluff](https://docs.sqlfluff.com) python package to format SQL queries.
"""

from __future__ import annotations

import logging
import pathlib
import textwrap
from functools import cache
from typing import TYPE_CHECKING
from typing import cast

import libcst as cst
import sqlfluff.api
from libcst.metadata import WhitespaceInclusivePositionProvider
from sqlfluff.api.simple import get_simple_config

from refine import utils
from refine.abc import BaseCodemod
from refine.abc import BaseConfig
from refine.exc import InvalidConfigError

from .utils import cst_module_has_query_strings
from .utils import is_sql_query

if TYPE_CHECKING:
    from sqlfluff.core import FluffConfig

# Quiet down sqlfluff logs during tests
logging.getLogger("sqlfluff").setLevel(logging.WARNING)

log = logging.getLogger(__name__)

BUILNTIN_SQLFLUFF_CONFIG_FILE = pathlib.Path(__file__).parent / ".sqlfluff"
SUPPORTED_SQLFLUFF_DIALECTS: tuple[str, ...] = tuple(dialect.label for dialect in sqlfluff.list_dialects())


class FormatSQLConfig(BaseConfig, frozen=True):
    """
    Configuration for the SQL Formatting codemod.
    """

    dialect: str = "ansi"
    """The SQL dialect to use when formatting the SQL queries."""

    sqlfluff_config_file: str = str(BUILNTIN_SQLFLUFF_CONFIG_FILE)
    """
    The path to a sqlfluff configuration file.

    If not provided, a default, opionated, configuration will be used.
    """

    def __post_init__(self) -> None:
        """
        This method can implement additional codemod initialization.
        """
        if not pathlib.Path(self.sqlfluff_config_file).exists():
            error_msg = f"SQLFluff config file not found: {self.sqlfluff_config_file}"
            raise InvalidConfigError(error_msg)
        if self.dialect not in SUPPORTED_SQLFLUFF_DIALECTS:
            error_msg = (
                f"Unsupported SQL dialect: {self.dialect}. Supported dialects are: "
                f"{', '.join(SUPPORTED_SQLFLUFF_DIALECTS)}"
            )
            raise InvalidConfigError(error_msg)


class FormatSQL(BaseCodemod[FormatSQLConfig]):
    """
    Format SQL queries using the `sqlfluff` python package.
    """

    NAME = "sqlfmt"
    CONFIG_CLS = FormatSQLConfig

    METADATA_DEPENDENCIES = (WhitespaceInclusivePositionProvider,)

    def visit_Module(self, mod: cst.Module) -> bool:
        # Let's just check if there's any SQL like query in the source code
        return cst_module_has_query_strings(mod)

    def leave_Assign(self, original: cst.Assign, updated: cst.Assign) -> cst.Assign:
        if not isinstance(updated.value, cst.SimpleString) or not is_sql_query(updated.value):
            return updated

        string_node = cast("cst.SimpleString", updated.value)
        unquoted_string = utils.evaluated_string(string_node)
        if unquoted_string is None:
            # We will only process strings
            return updated
        if isinstance(unquoted_string, bytes):
            # We're not handling bytestrings
            return updated

        # We can only get metadata information from the original node, not the updated one
        position = self.get_metadata(WhitespaceInclusivePositionProvider, original)
        query = self.__format_sql(unquoted_string, indent=position.start.column + 4)
        quote = string_node.quote
        if "\n" in query and string_node.quote in ('"""', "'''"):
            first_line = "\n"
            last_line = " " * position.start.column
        elif "\n" in query and string_node.quote in ('"', "'"):
            first_line = "\n"
            last_line = " " * position.start.column
            quote = '"""'
        else:
            last_line = first_line = ""
        return updated.with_changes(value=string_node.__class__(f"""{quote}{first_line}{query}{last_line}{quote}"""))
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

            string_node = cast("cst.SimpleString", arg.value)
            unquoted_string = utils.evaluated_string(string_node)

            if unquoted_string is None:
                # We will only process strings
                args.append(arg)
                continue

            if isinstance(unquoted_string, bytes):
                # We're not handling bytestrings
                args.append(arg)
                continue

            matched = True
            # We can only get metadata information from the original node, not the updated one
            position = self.get_metadata(WhitespaceInclusivePositionProvider, string_node)
            query = self.__format_sql(unquoted_string, indent=position.start.column)
            quote = string_node.quote
            if "\n" in query and string_node.quote in ('"""', "'''"):
                first_line = "\n"
                last_line = " " * position.start.column
            elif "\n" in query and string_node.quote in ('"', "'"):
                first_line = "\n"
                last_line = " " * position.start.column
                quote = '"""'
            else:
                last_line = first_line = ""
            args.append(
                arg.with_changes(value=string_node.__class__(f"""{quote}{first_line}{query}{last_line}{quote}"""))
            )
        if matched:
            return updated.with_changes(args=args)
        return updated

    @cache  # noqa: B019
    def __get_sqlfluff_config(self) -> FluffConfig:
        # Load config and cache it
        return get_simple_config(config_path=str(self.config.sqlfluff_config_file))

    def __format_sql(self, query: str, indent: int) -> str:
        # We want a copy of the config so that we can modify it
        config = self.__get_sqlfluff_config().copy()
        starting_newline: str = (query.startswith("\n") and "\n") or ""
        if starting_newline:
            query = query[1:]

        query = utils.remove_leading_whitespace(query)

        # Since we will need to indent code, and still want sqlfluff to respect it's max width setting
        config.set_value("max_linelength", config.get("max_line_length") - indent)

        formated = (
            sqlfluff.api.fix(
                query,
                dialect="mysql",
                config=config,
                fix_even_unparsable=False,
            )
            # Remove the ending newline
            .rstrip()
        )
        if "\n" not in formated:
            # If the query is a single line, we don't need to indent it
            log.debug("Formatted SQL Query >>>>>>>>>%s<<<<<<<<<<<<<<", formated)
            return formated

        log.debug("Formatted SQL Query >>>>>>>>>\n%s\n<<<<<<<<<<<<<<", formated)

        indent_query = textwrap.indent(formated, prefix=" " * indent)
        if "\n" in indent_query and not indent_query.endswith("\n"):
            # Multiline queries must end with a line break
            indent_query += "\n"
        log.debug("Indented SQL Query >>>>>>>>>\n%s\n<<<<<<<<<<<<<<", indent_query)
        return indent_query

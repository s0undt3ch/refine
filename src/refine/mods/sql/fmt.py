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
from refine.mods.sql import sqruff_backend

from .utils import RAW_SQL_HINT_RE
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

    backend: str = "sqruff"
    """The formatting backend: ``sqruff`` (fast, default) or ``sqlfluff``."""

    sqlfluff_config_file: str = str(BUILNTIN_SQLFLUFF_CONFIG_FILE)
    """
    The path to a sqlfluff configuration file.

    If not provided, a default, opionated, configuration will be used.
    """

    sqruff_config_file: str | None = None
    """
    The path to a ``.sqruff`` configuration file.

    If not provided, a default, opionated, configuration will be used.
    """

    def __post_init__(self) -> None:
        """
        This method can implement additional codemod initialization.
        """
        if self.backend not in ("sqruff", "sqlfluff"):
            error_msg = f"Unsupported sqlfmt backend: {self.backend}. Choose 'sqruff' or 'sqlfluff'."
            raise InvalidConfigError(error_msg)
        if not pathlib.Path(self.sqlfluff_config_file).exists():
            error_msg = f"SQLFluff config file not found: {self.sqlfluff_config_file}"
            raise InvalidConfigError(error_msg)
        if self.sqruff_config_file is not None:
            sqruff_config_path = pathlib.Path(self.sqruff_config_file)
            if not sqruff_config_path.exists():
                error_msg = f"Sqruff config file not found: {self.sqruff_config_file}"
                raise InvalidConfigError(error_msg)
            if sqruff_config_path.name != ".sqruff":
                error_msg = f"Sqruff config file must be named '.sqruff', got: {self.sqruff_config_file}"
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

    @classmethod
    def should_process(cls, source: str, filename: str) -> bool:
        # If no SQL-looking text exists anywhere in the raw source there is
        # nothing for this codemod to do — skip the parse entirely.
        return RAW_SQL_HINT_RE.search(source) is not None

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
        starting_newline: str = (query.startswith("\n") and "\n") or ""
        if starting_newline:
            query = query[1:]

        query = utils.remove_leading_whitespace(query)

        if self.config.backend == "sqruff":
            formated = self.__format_sql_sqruff(query, indent=indent)
        else:
            formated = self.__format_sql_sqlfluff(query, indent=indent)
        if formated is None:
            # Backend could not fix the query: leave it untouched and warn.
            log.warning("sqlfmt(%s) could not format a query; leaving it unchanged", self.config.backend)
            formated = query.rstrip()

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

    def __format_sql_sqlfluff(self, query: str, indent: int) -> str | None:
        # We want a copy of the config so that we can modify it
        config = self.__get_sqlfluff_config().copy()
        # Since we will need to indent code, and still want sqlfluff to respect
        # its max width setting
        config.set_value("max_linelength", config.get("max_line_length") - indent)
        return (
            sqlfluff.api.fix(
                query,
                dialect=self.config.dialect,
                config=config,
                fix_even_unparsable=False,
            )
            # Remove the ending newline
            .rstrip()
        )

    def __format_sql_sqruff(self, query: str, indent: int) -> str | None:
        max_line_length = self.__get_sqlfluff_config().get("max_line_length") - indent
        config_dir = None
        if self.config.sqruff_config_file is not None:
            config_dir = pathlib.Path(self.config.sqruff_config_file).parent
        return sqruff_backend.format_sql(
            query,
            dialect=self.config.dialect,
            max_line_length=max_line_length,
            config_dir=config_dir,
        )

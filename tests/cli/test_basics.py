from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from refine import __version__
from refine.exc import InvalidConfigError
from refine.exc import RefineSystemExit
from refine.processor import ParallelTransformResult


def test_help(cli, capsys):
    """
    Test the help command.
    """
    exitcode = cli.run("--help")
    assert exitcode == 0
    captured = capsys.readouterr()
    assert "usage: refine [-h]" in captured.out


def test_version(cli, capsys):
    """
    Test the version command.
    """
    exitcode = cli.run("--version")
    assert exitcode == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_list_codemods(cli, caplog, codemods):
    """
    Test the list-codemods command.
    """
    with caplog.at_level("INFO"):
        exitcode = cli.run("--list-codemods")
    assert exitcode == 0
    logged_output = caplog.text
    assert "Available codemods:" in logged_output
    for codemod in codemods:
        assert f"- {codemod.NAME}: {codemod.get_short_description()}" in logged_output


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (
            ("--verbose", "--quiet"),
            "--quiet/-q: not allowed with argument --verbose/-v",
        ),
        (
            ("--select=A", "--select-extend=B"),
            "--select-codemod-extend/--select-extend: not allowed with argument --select-codemod/--select",
        ),
        (
            ("--exclude=A", "--exclude-extend=B"),
            "--exclude-codemod-extend/--exclude-extend: not allowed with argument --exclude-codemod/--exclude",
        ),
        (
            ("--codemods-path=A", "--codemods-path-extend=B"),
            "--codemods-path-extend: not allowed with argument --codemods-path",
        ),
    ],
)
def test_mutualy_exlusive_options_error_out(cli, capsys, args, message):
    """
    Test that mutually exclusive options raise an error.
    """
    exitcode = cli.run(*args)
    assert exitcode == 2
    captured = capsys.readouterr()
    assert message in captured.err


def test_select_overrides_config(cli, codemods, file_to_modify):
    cli.with_config(select=["codemod-1"])
    exitcode = cli.run("--select=codemod-2", file_to_modify)
    assert exitcode == 0
    loaded_codemod_names = [mod.NAME for mod in cli.codemods]
    assert loaded_codemod_names == ["codemod-2"]


def test_select_extend_extends_config(cli, codemods, file_to_modify):
    cli.with_config(select=["codemod-1"])
    exitcode = cli.run("--select-extend=codemod-2", file_to_modify)
    assert exitcode == 0
    loaded_codemod_names = [mod.NAME for mod in cli.codemods]
    assert loaded_codemod_names == ["codemod-1", "codemod-2"]


def test_exclude_overrides_config(cli, codemods, file_to_modify):
    cli.with_config(exclude=["codemod-1"])
    exitcode = cli.run("--exclude=codemod-2", file_to_modify)
    assert exitcode == 0
    loaded_codemod_names = [mod.NAME for mod in cli.codemods]
    assert loaded_codemod_names == ["codemod-1", "codemod-3"]


def test_exclude_extend_extends_config(cli, codemods, file_to_modify):
    cli.with_config(exclude=["codemod-1"])
    exitcode = cli.run("--exclude-extend=codemod-2", file_to_modify)
    assert exitcode == 0
    loaded_codemod_names = [mod.NAME for mod in cli.codemods]
    assert loaded_codemod_names == ["codemod-3"]


def test_codemods_path_overrides_config(cli, file_to_modify):
    cli.with_config(codemod_paths=["codemod-1"])
    exitcode = cli.run("--codemods-path=codemod-2", file_to_modify)
    # The codemod-2 path is not a directory
    assert exitcode == 1
    os.makedirs(os.path.join(cli.config.repo_root, "codemod-2"))
    exitcode = cli.run("--codemods-path=codemod-2", file_to_modify)
    assert exitcode == 0
    assert cli.config.codemod_paths == ["codemod-2"]


def test_codemods_path_extend_extends_config(cli, file_to_modify):
    cli.with_config(codemod_paths=["codemod-1"])
    exitcode = cli.run("--codemods-path-extend=codemod-2", file_to_modify)
    # The codemod-2 path is not a directory
    assert exitcode == 1
    os.makedirs(os.path.join(cli.config.repo_root, "codemod-2"))
    exitcode = cli.run("--codemods-path-extend=codemod-2", file_to_modify)
    assert exitcode == 0
    assert cli.config.codemod_paths == ["codemod-1", "codemod-2"]


# Tests for hide_progress config override
def test_hide_progress_functionality(cli, file_to_modify, subtests):
    """
    Test all hide_progress CLI flag and config functionality using subtests.
    """
    with subtests.test("CLI flag overrides config when config has hide_progress=False"):
        cli.with_config(hide_progress=False)
        exitcode = cli.run("--hide-progress", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True

    with subtests.test("CLI flag overrides config when config has hide_progress=True"):
        cli.with_config(hide_progress=True)
        exitcode = cli.run("--hide-progress", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True

    with subtests.test("CLI flag works with default config (hide_progress=False)"):
        cli.with_config()  # Reset to default config
        exitcode = cli.run("--hide-progress", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True

    with subtests.test("Config setting is preserved when no CLI flag is provided"):
        cli.with_config(hide_progress=True)
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True

    with subtests.test("Defaults to False when neither config nor CLI flag is set"):
        cli.with_config()  # Reset to default config
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is False


# Tests for other config overrides
def test_fail_fast_functionality(cli, file_to_modify, subtests):
    """
    Test all fail_fast CLI flag and config functionality using subtests.
    """
    with subtests.test("CLI flag overrides config when config has fail_fast=False"):
        cli.with_config(fail_fast=False)
        exitcode = cli.run("--fail-fast", file_to_modify)
        assert exitcode == 0
        assert cli.config.fail_fast is True

    with subtests.test("Config setting is preserved when no CLI flag is provided"):
        cli.with_config(fail_fast=True)
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.fail_fast is True

    with subtests.test("Defaults to False when neither config nor CLI flag is set"):
        cli.with_config()  # Reset to default config
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.fail_fast is False


def test_respect_gitignore_functionality(cli, file_to_modify, subtests):
    """
    Test that --respect-gitignore CLI flag works correctly.
    """
    with subtests.test("CLI flag overrides config when config has respect_gitignore=False"):
        cli.with_config(respect_gitignore=False)
        exitcode = cli.run("--respect-gitignore", file_to_modify)
        assert exitcode == 0
        # CLI flag should override config setting
        assert cli.config.respect_gitignore is True

    with subtests.test("CLI flag overrides config when config has respect_gitignore=True"):
        cli.with_config(respect_gitignore=True)
        exitcode = cli.run("--respect-gitignore", file_to_modify)
        assert exitcode == 0
        assert cli.config.respect_gitignore is True

    with subtests.test("No CLI flag preserves config setting"):
        cli.with_config(respect_gitignore=True)
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.respect_gitignore is True

    with subtests.test("Default config has respect_gitignore=False"):
        cli.with_config()  # Reset to default config
        exitcode = cli.run(file_to_modify)
        assert exitcode == 0
        assert cli.config.respect_gitignore is False


def test_multiple_cli_flag_overrides(cli, file_to_modify, subtests):
    """
    Test that multiple CLI flags can override config simultaneously using subtests.
    """
    with subtests.test("Multiple flags override config values"):
        cli.with_config(hide_progress=False, fail_fast=False, respect_gitignore=False)
        exitcode = cli.run("--hide-progress", "--fail-fast", "--respect-gitignore", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True
        assert cli.config.fail_fast is True
        assert cli.config.respect_gitignore is True

    with subtests.test("Partial flags override only specified config values"):
        cli.with_config(hide_progress=False, fail_fast=True, respect_gitignore=False)
        exitcode = cli.run("--hide-progress", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True
        assert cli.config.fail_fast is True  # Preserved from config
        assert cli.config.respect_gitignore is False  # Preserved from config

    with subtests.test("Mixed flags work with default config"):
        cli.with_config()  # Reset to default config
        exitcode = cli.run("--hide-progress", "--fail-fast", file_to_modify)
        assert exitcode == 0
        assert cli.config.hide_progress is True
        assert cli.config.fail_fast is True
        assert cli.config.respect_gitignore is False  # Default value preserved


# Tests for system exits and error handling
def test_no_codemods_selected_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when no codemods are selected.
    """
    # Exclude all available codemods
    cli.with_config(exclude=["codemod-1", "codemod-2", "codemod-3"])

    with caplog.at_level("ERROR"):
        exitcode = cli.run(file_to_modify)

    assert exitcode == 1
    assert "No codemods selected. Exiting." in caplog.text


def test_invalid_codemod_selected_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod is selected.
    """
    with caplog.at_level("ERROR"):
        exitcode = cli.run("--select=invalid-codemod", file_to_modify)

    assert exitcode == 1
    assert "Invalid codemods selected: invalid-codemod" in caplog.text


def test_invalid_codemod_excluded_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod is excluded.
    """
    with caplog.at_level("ERROR"):
        exitcode = cli.run("--exclude=invalid-codemod", file_to_modify)

    assert exitcode == 1
    assert "Invalid codemods excluded: invalid-codemod" in caplog.text


def test_invalid_codemod_select_extend_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod is in select extend.
    """
    cli.with_config(select=["codemod-1"])

    with caplog.at_level("ERROR"):
        exitcode = cli.run("--select-extend=invalid-codemod", file_to_modify)

    assert exitcode == 1
    assert "Invalid codemods select extend: invalid-codemod" in caplog.text


def test_invalid_codemod_exclude_extend_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod is in exclude extend.
    """
    cli.with_config(exclude=["codemod-1"])

    with caplog.at_level("ERROR"):
        exitcode = cli.run("--exclude-extend=invalid-codemod", file_to_modify)

    assert exitcode == 1
    assert "Invalid codemods exclude extend: invalid-codemod" in caplog.text


def test_invalid_codemod_path_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod path is provided.
    """
    with caplog.at_level("ERROR"):
        exitcode = cli.run("--codemods-path=invalid-path", file_to_modify)

    assert exitcode == 1
    assert "Codemod path invalid-path is not a directory" in caplog.text


def test_invalid_codemod_path_extend_system_exit(cli, caplog, file_to_modify):
    """
    Test that CLI exits with status 1 when invalid codemod path extend is provided.
    """
    with caplog.at_level("ERROR"):
        exitcode = cli.run("--codemods-path-extend=invalid-path", file_to_modify)

    assert exitcode == 1
    assert "Codemod path invalid-path is not a directory" in caplog.text


def test_file_outside_repo_root_system_exit(cli, caplog, tmp_path):
    """
    Test that CLI exits with status 1 when file is outside repo root.
    """
    # Create a file outside the current working directory (repo root)
    external_file = tmp_path.parent / "external_file.py"
    external_file.write_text("print('external')")

    with caplog.at_level("ERROR"):
        exitcode = cli.run(str(external_file))

    assert exitcode == 1
    assert "is not inside the repo root" in caplog.text


# Tests for processor exception handling
@pytest.mark.parametrize(
    ("exception", "expected_code", "expected_message"),
    [
        (
            pytest.param(
                Exception("Invalid configuration"),
                1,
                "Invalid configuration",
                id="InvalidConfigError",
            )
        ),
        (pytest.param(SystemExit(42), 42, None, id="SystemExit-int")),
        (pytest.param(SystemExit(None), 1, None, id="SystemExit-None")),
        (pytest.param(SystemExit("error message"), 1, "error message", id="SystemExit-string")),
        (pytest.param(KeyboardInterrupt(), 1, None, id="KeyboardInterrupt")),
    ],
)
def test_processor_exceptions(cli, caplog, file_to_modify, exception, expected_code, expected_message):
    """
    Test that CLI handles various processor exceptions correctly.
    """
    # Convert the generic Exception to InvalidConfigError for the first test case
    if isinstance(exception, Exception) and not isinstance(exception, (SystemExit, KeyboardInterrupt)):
        exception = InvalidConfigError(str(exception))

    with patch("refine.cli.Processor") as mock_processor:
        if isinstance(exception, InvalidConfigError):
            # Exception during processor creation
            mock_processor.side_effect = exception
        else:
            # Exception during processing
            mock_processor_instance = mock_processor.return_value
            mock_processor_instance.process.side_effect = exception

        if expected_message and isinstance(exception, InvalidConfigError):
            with caplog.at_level("ERROR"):
                exitcode = cli.run(file_to_modify)
            assert expected_message in caplog.text
        else:
            exitcode = cli.run(file_to_modify)

        assert exitcode == expected_code


def test_processor_refine_system_exit(cli, file_to_modify):
    """
    Test that CLI handles RefineSystemExit correctly.
    """
    with patch("refine.cli.Processor") as mock_processor:
        mock_processor_instance = mock_processor.return_value
        mock_processor_instance.process.side_effect = RefineSystemExit(code=42, message="Custom exit message")

        exitcode = cli.run(file_to_modify)
        assert exitcode == 42


def test_processing_failures_system_exit(cli, file_to_modify):
    """
    Test that CLI exits with status 1 when processor reports failures.
    """
    with patch("refine.cli.Processor") as mock_processor:
        mock_processor_instance = mock_processor.return_value
        mock_processor_instance.process.return_value = ParallelTransformResult(
            successes=0, failures=1, warnings=0, skips=0, changed=0
        )

        exitcode = cli.run(file_to_modify)
        assert exitcode == 1


def test_successful_processing_system_exit(cli, file_to_modify):
    """
    Test that CLI exits with status 0 when processing is successful.
    """
    exitcode = cli.run(file_to_modify)
    assert exitcode == 0


# Tests for logging configuration
def test_quiet_flag_suppresses_info_logs(cli, caplog, file_to_modify):
    """
    Test that --quiet flag suppresses INFO level logs.
    """
    with caplog.at_level(logging.INFO):
        cli.run("--quiet", file_to_modify)

    # With quiet flag, INFO messages should not appear in logs
    info_messages = [record for record in caplog.records if record.levelno == logging.INFO]
    # The quiet flag should suppress most INFO logs, but some might still appear from setup
    # The key test is that normal processing INFO logs are suppressed
    assert len(info_messages) == 0 or all("Selected codemods:" not in msg.message for msg in info_messages)


def test_verbose_flag_shows_debug_logs(cli, caplog, file_to_modify):
    """
    Test that --verbose flag enables DEBUG level logs.
    """
    with caplog.at_level(logging.DEBUG):
        cli.run("--verbose", file_to_modify)

    # With verbose flag, DEBUG messages should appear
    debug_messages = [record for record in caplog.records if record.levelno == logging.DEBUG]
    # Should have debug messages about config loading
    assert any("Loading" in record.message for record in debug_messages)


def test_normal_flag_shows_info_logs(cli, caplog, file_to_modify):
    """
    Test that normal operation (no --quiet or --verbose) shows INFO logs.
    """
    with caplog.at_level(logging.INFO):
        cli.run(file_to_modify)

    # Normal operation should show INFO logs like "Selected codemods:"
    info_messages = [record for record in caplog.records if record.levelno == logging.INFO]
    assert any("Selected codemods:" in record.message for record in info_messages)

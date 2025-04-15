from __future__ import annotations

import os

import pytest

from refine import __version__


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

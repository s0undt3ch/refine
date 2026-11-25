from __future__ import annotations


def test_codemod_from_codemod_paths_is_listed(real_cli, write_codemod, caplog):
    write_codemod(real_cli.cwd / "mods", codemod_name="custom")
    real_cli.with_config(codemod_paths=["mods"])

    with caplog.at_level("INFO"):
        exitcode = real_cli.run("--list-codemods")

    assert exitcode == 0
    assert "- custom: Custom codemod custom." in caplog.text


def test_codemod_from_codemod_paths_transforms_a_file(real_cli, write_codemod):
    write_codemod(real_cli.cwd / "mods", codemod_name="custom")
    real_cli.with_config(codemod_paths=["mods"], process_pool_size=1, hide_progress=True, cache=False)
    target = real_cli.cwd / "target.py"
    target.write_text("x = 1\n")

    exitcode = real_cli.run("--select=custom", target)

    assert exitcode == 0
    assert target.read_text() == "x_refined = 1\n"

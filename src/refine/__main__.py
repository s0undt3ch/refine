"""
Utility to simplify rewriting python code.

It can be used for one-off rewrites, or, to maintain code styling rules.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys
from multiprocessing import freeze_support
from typing import NoReturn

import msgspec.structs
import py_walk

from refine import __version__
from refine.config import Config
from refine.exc import RefineSystemExit
from refine.processor import Processor
from refine.registry import Registry

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")

log = logging.getLogger(__name__)


def main() -> NoReturn:  # noqa: PLR0915,C901
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("files", metavar="FILE", nargs="*", type=pathlib.Path, help="One or more files to process.")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        help="Path to config file. Defaults to '%(default)s' on the current directory.",
        default=".refine.toml",
    )
    parser.add_argument(
        "--respect-gitignore",
        "--rgi",
        action="store_true",
        default=False,
        help="Respect .gitignore files when searching for files to process.",
    )
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Quiet down the tool output.",
    )
    verbosity_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose output.",
    )
    parser.add_argument(
        "--fail-fast",
        "--ff",
        action="store_true",
        default=False,
        help="Exit as soon as possible on the first processing error",
    )
    parser.add_argument(
        "--list-codemods",
        "--list",
        action="store_true",
        help="List all available codemods",
    )
    exclude_group = parser.add_mutually_exclusive_group()
    exclude_group.add_argument(
        "--exclude-codemod",
        "--exclude",
        default=[],
        action="append",
        help="Exclude codemods from available codemods. Ignores the config file.",
    )
    exclude_group.add_argument(
        "--exclude-codemod-extend",
        "--exclude-extend",
        default=[],
        action="append",
        help="Extend the existing exclude codemods from config file.",
    )
    select_group = parser.add_mutually_exclusive_group()
    select_group.add_argument(
        "--select-codemod",
        "--select",
        default=[],
        action="append",
        help="Explicitly select codemod names from available codemods. Ignores the config file.",
    )
    select_group.add_argument(
        "--select-codemod-extend",
        "--select-extend",
        default=[],
        action="append",
        help="Extend selected codemods from the configuration file.",
    )
    codemod_paths_group = parser.add_mutually_exclusive_group()
    codemod_paths_group.add_argument(
        "--codemods-path",
        type=pathlib.Path,
        action="append",
        default=[],
        dest="codemod_paths",
        help="Path to a codemods directory. Can be passed multiple times.",
    )
    codemod_paths_group.add_argument(
        "--codemods-path-extend",
        type=pathlib.Path,
        action="append",
        default=[],
        dest="codemod_paths_extend",
        help="Path to a codemods directory. Can be passed multiple times.",
    )
    args = parser.parse_args()
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if not args.config.is_absolute():
        config_file = pathlib.Path.cwd().joinpath(args.config).resolve()
    else:
        config_file = args.config
    if config_file.exists():
        if config_file.name == "pyproject.toml":
            config = Config.from_pyproject_file(config_file)
        else:
            config = Config.from_default_file(config_file)
    elif pathlib.Path.cwd().joinpath("pyproject.toml").exists():
        config = Config.from_pyproject_file(pathlib.Path.cwd().joinpath("pyproject.toml"))
    else:
        config = Config()

    if args.codemod_paths:
        config.codemod_paths.clear()
        for codemod_path in args.codemod_paths:
            if not codemod_path.is_dir():
                log.error("Codemod path %s is not a directory", codemod_path)
                parser.exit(status=1)
            config.codemod_paths.append(str(codemod_path))

    if args.codemod_paths_extend:
        # Add the additional CLI passed codemod paths
        for codemod_path in args.codemod_paths_extend:
            if not codemod_path.is_dir():
                log.error("Codemod path %s is not a directory", codemod_path)
                parser.exit(status=1)
            strpath = str(codemod_path)
            if strpath in config.codemod_paths:
                continue
            config.codemod_paths.append(strpath)

    registry = Registry()
    registry.load(config.codemod_paths)

    available_codemods = {codemod.NAME: codemod.get_short_description() for codemod in registry.codemods()}

    if args.select_codemod:
        # Add any additional CLI passed selections
        config.select[:] = list(args.select_codemod)
        bad_codemods = set(config.select) - set(available_codemods)
        if bad_codemods:
            log.error("Invalid codemods selected: %s", ", ".join(bad_codemods))
            parser.exit(status=1)

    if args.select_codemod_extend:
        # Add any additional CLI passed selections
        for name in args.select_codemod_extend:
            if name not in self.config.select:
                config.select.append(name)
        bad_codemods = set(config.select) - set(available_codemods)
        if bad_codemods:
            log.error("Invalid codemods selected: %s", ", ".join(bad_codemods))
            parser.exit(status=1)

    if args.exclude_codemod:
        # Add any additional CLI passed exclusions
        config.exclude[:] = list(args.exclude_codemod)
        bad_codemods = set(config.exclude) - set(available_codemods)
        if bad_codemods:
            log.error("Invalid codemods excluded: %s", ", ".join(bad_codemods))
            parser.exit(status=1)

    if args.exclude_codemod_extend:
        # Add any additional CLI passed exclusions
        for name in args.exclude_codemod_extend:
            if name not in self.config.exclude:
                config.exclude.append(name)
        bad_codemods = set(config.exclude) - set(available_codemods)
        if bad_codemods:
            log.error("Invalid codemods excluded: %s", ", ".join(bad_codemods))
            parser.exit(status=1)

    if args.fail_fast:
        config = msgspec.structs.replace(config, fail_fast=True)

    if args.list_codemods:
        log.info("Available codemods:")
        for name, description in sorted(available_codemods.items()):
            # In case the description is comming from the docstring, we just really want the first line.
            log.info(" - %s: %s", name, description.strip())
        parser.exit()

    repo_root: pathlib.Path = pathlib.Path(config.repo_root)
    paths: list[pathlib.Path] = args.files
    if not paths:
        paths.append(repo_root)

    ignore_patterns: list[str] = config.exclude_patterns
    gitignore_file = repo_root / ".gitignore"
    respect_gitignore: bool = args.respect_gitignore or config.respect_gitignore
    if respect_gitignore and gitignore_file.exists():
        ignore_patterns.extend(
            pattern for pattern in gitignore_file.read_text().splitlines() if pattern and not pattern.startswith("#")
        )

    files: list[pathlib.Path] = []
    for path in paths:
        if path.is_file():
            if _append_path(path, repo_root=repo_root, files=files) is False:
                parser.exit(status=1)
            continue
        for subpath in py_walk.walk(path, match=["*.py"], mode="only-files", ignore=ignore_patterns):
            if _append_path(subpath, repo_root=repo_root, files=files) is False:
                parser.exit(status=1)

    codemods = list(registry.codemods(select_codemods=config.select, exclude_codemods=config.exclude))
    if not codemods:
        log.error("No codemods selected. Exiting.")
        parser.exit(status=1)

    log.info("Selected codemods:")
    for codemod in codemods:
        log.info(" - %s: %s", codemod.NAME, codemod.get_short_description())

    processor = Processor(config=config, registry=registry, codemods=codemods)
    try:
        result = processor.process(files)
        if result.failures:
            parser.exit(status=1)
    except RefineSystemExit as exc:
        parser.exit(status=exc.code, message=exc.message)
    except SystemExit as exc:
        code: str | int | None = exc.code
        if code is None:
            parser.exit(status=1)
        if isinstance(code, int):
            parser.exit(status=code)
        parser.exit(status=1, message=code)
    except KeyboardInterrupt:
        parser.exit(status=1)
    parser.exit(status=0)


def _append_path(path: pathlib.Path, repo_root: pathlib.Path, files: list[pathlib.Path]) -> bool:
    """
    Append a path to the list of paths if it is not already present.
    """
    resolved_path: pathlib.Path = path.resolve()
    try:
        # Check if the file is inside the repo root
        resolved_path.relative_to(repo_root)
    except ValueError:
        log.error(  # noqa: TRY400
            "File %s is not inside the repo root %s",
            path,
            repo_root,
        )
        return False
    else:
        if resolved_path not in files:
            files.append(resolved_path)
        return True


if __name__ == "__main__":
    freeze_support()
    main()

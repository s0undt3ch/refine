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

from refine import __version__
from refine.config import Config
from refine.exc import ReCodeSystemExit
from refine.processor import Processor
from refine.registry import Registry

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")

log = logging.getLogger(__name__)


def main() -> NoReturn:  # noqa: PLR0915
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("files", metavar="FILE", nargs="*", type=pathlib.Path, help="One or more files to process.")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        help="Path to config file. Defaults to '.refine.ini' on the current directory.",
        default=".refine.toml",
    )
    parser.add_argument("--quiet", "-q", action="store_true", default=False, help="Quiet down the tool output.")
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
    parser.add_argument(
        "--exclude-codemod",
        "--exclude",
        default=[],
        action="append",
        help="Exclude codemods from available codemods.",
    )
    parser.add_argument(
        "--select-codemod",
        "--select",
        default=[],
        action="append",
        help="Explicitly select codemod names from available codemods.",
    )
    parser.add_argument(
        "--codemods-path",
        type=pathlib.Path,
        action="append",
        default=[],
        dest="codemods_paths",
        help="Path to a codemods directory. Can be passed multiple times.",
    )
    args = parser.parse_args()
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
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

    if args.list_codemods:
        # Add the additional CLI passed codemod paths
        config.codemod_paths[:] = list(set(config.codemod_paths) | set(args.codemods_paths))

    if args.select_codemod:
        # Add any additional CLI passed selections
        config.select[:] = list(set(config.select) | set(args.select_codemod))

    if args.exclude_codemod:
        # Add any additional CLI passed exclusions
        config.exclude[:] = list(set(config.exclude) | set(args.exclude_codemod))

    if args.fail_fast:
        config = config.model_copy(update={"fail_fast": True}, deep=True)

    registry = Registry()
    registry.load(config.codemod_paths)
    if args.list_codemods:
        log.info("Available codemods:")
        for codemod in registry.codemods():
            # In case the description is comming from the docstring, we just really want the first line.
            description = codemod.DESCRIPTION.strip().splitlines()[0]
            log.info(" - %s: %s", codemod.NAME, description.strip())
        parser.exit()

    paths = args.files
    if not paths:
        paths = config.repo_root.glob("**/*.py")

    files: list[pathlib.Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        for subpath in path.rglob("*.py"):
            files.append(subpath)

    codemods = list(registry.codemods(select_codemods=config.select, exclude_codemods=config.exclude))
    log.info("Selected codemods:")
    for codemod in codemods:
        log.info(" - %s: %s", codemod.NAME, codemod.DESCRIPTION)

    processor = Processor(config=config, registry=registry, codemods=codemods)
    try:
        result = processor.process(files)
        if result.failures:
            parser.exit(status=1)
    except ReCodeSystemExit as exc:
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


if __name__ == "__main__":
    freeze_support()
    main()

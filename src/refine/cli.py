"""
Utility to simplify rewriting python code.

It can be used for one-off rewrites, or, to maintain code styling rules.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import pprint
import sys
from multiprocessing import freeze_support
from typing import NoReturn

import msgspec.structs
import py_walk

from refine import __version__
from refine.config import Config
from refine.exc import InvalidConfigError
from refine.exc import RefineSystemExit
from refine.processor import ParallelTransformResult
from refine.processor import Processor
from refine.registry import Registry

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")

log = logging.getLogger(__name__)


class CLI:
    """
    Command Line Interface for the Refine tool.
    """

    parser: argparse.ArgumentParser
    config: Config
    registry: Registry
    processor: Processor

    def __init__(self) -> None:
        self.files: list[pathlib.Path] = []
        self.parser = self._setup_parser()

    def run(self, argv: list[str] | None = None) -> NoReturn:
        """
        Process the command line arguments and run the tool.
        """
        if argv is None:
            argv = sys.argv[1:]

        args = self.parser.parse_args(argv)
        if args.quiet:
            logging.getLogger().setLevel(logging.ERROR)
        elif args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger("py_walk").setLevel(logging.INFO)

        self.config = self._load_config(args.config)
        config_overrides = {}
        if args.fail_fast:
            config_overrides["fail_fast"] = True
        if args.hide_progress:
            config_overrides["hide_progress"] = True
        if args.respect_gitignore:
            config_overrides["respect_gitignore"] = True

        if args.codemod_paths:
            self.config.codemod_paths.clear()
            for codemod_path in args.codemod_paths:
                if not codemod_path.is_dir():
                    log.error("Codemod path %s is not a directory", codemod_path)
                    self.parser.exit(status=1)
                self.config.codemod_paths.append(str(codemod_path))

        if args.codemod_paths_extend:
            # Add the additional CLI passed codemod paths
            for codemod_path in args.codemod_paths_extend:
                if not codemod_path.is_dir():
                    log.error("Codemod path %s is not a directory", codemod_path)
                    self.parser.exit(status=1)
                strpath = str(codemod_path)
                if strpath in self.config.codemod_paths:
                    continue
                self.config.codemod_paths.append(strpath)

        self.registry = Registry()
        self.registry.load(self.config.codemod_paths)

        available_codemods = {codemod.NAME: codemod.get_short_description() for codemod in self.registry.codemods()}

        if args.select_codemod:
            # Add any additional CLI passed selections
            self.config.select[:] = list(args.select_codemod)
            bad_codemods = set(self.config.select) - set(available_codemods)
            if bad_codemods:
                log.error("Invalid codemods selected: %s", ", ".join(bad_codemods))
                self.parser.exit(status=1)

        if args.select_codemod_extend:
            # Add any additional CLI passed selections
            for name in args.select_codemod_extend:
                if name not in self.config.select:
                    self.config.select.append(name)
            bad_codemods = set(self.config.select) - set(available_codemods)
            if bad_codemods:
                log.error("Invalid codemods select extend: %s", ", ".join(bad_codemods))
                self.parser.exit(status=1)

        if args.exclude_codemod:
            # Add any additional CLI passed exclusions
            self.config.exclude[:] = list(args.exclude_codemod)
            bad_codemods = set(self.config.exclude) - set(available_codemods)
            if bad_codemods:
                log.error("Invalid codemods excluded: %s", ", ".join(bad_codemods))
                self.parser.exit(status=1)

        if args.exclude_codemod_extend:
            # Add any additional CLI passed exclusions
            for name in args.exclude_codemod_extend:
                if name not in self.config.exclude:
                    self.config.exclude.append(name)
            bad_codemods = set(self.config.exclude) - set(available_codemods)
            if bad_codemods:
                log.error("Invalid codemods exclude extend: %s", ", ".join(bad_codemods))
                self.parser.exit(status=1)

        if args.list_codemods:
            log.info("Available codemods:")
            for name, description in sorted(available_codemods.items()):
                # In case the description is comming from the docstring, we just really want the first line.
                log.info(" - %s: %s", name, description.strip())
            self.parser.exit()

        # Reconstruct the config with any overrides
        if config_overrides:
            log.debug("Applying config overrides: %s", config_overrides)
            # Use msgspec.structs.replace to create a new Config instance with the overrides
            # This ensures that we don't modify the original config instance directly.
            self.config = msgspec.structs.replace(self.config, **config_overrides)

        repo_root: pathlib.Path = pathlib.Path(self.config.repo_root)
        paths: list[pathlib.Path] = args.files
        if not paths:
            paths.append(repo_root)

        ignore_patterns: list[str] = [
            *self.config.exclude_patterns,
            "**/__pycache__/**",
        ]
        gitignore_file = repo_root / ".gitignore"
        if self.config.respect_gitignore and gitignore_file.exists():
            ignore_patterns.extend(
                pattern
                for pattern in gitignore_file.read_text().splitlines()
                if pattern and not pattern.startswith("#")
            )

        for path in paths:
            if path.is_file():
                if self._append_path(path, repo_root=repo_root, files=self.files) is False:
                    self.parser.exit(status=1)
                continue
            for subpath in py_walk.walk(path, match=["*.py"], mode="only-files", ignore=ignore_patterns):
                if self._append_path(subpath, repo_root=repo_root, files=self.files) is False:
                    self.parser.exit(status=1)

        self.codemods = list(
            self.registry.codemods(select_codemods=self.config.select, exclude_codemods=self.config.exclude)
        )
        if not self.codemods:
            log.error("No codemods selected. Exiting.")
            self.parser.exit(status=1)

        log.info("Selected codemods:")
        for codemod in self.codemods:
            log.info(" - %s: %s", codemod.NAME, codemod.get_short_description())

        try:
            self.processor = Processor(config=self.config, registry=self.registry, codemods=self.codemods)
        except InvalidConfigError as exc:
            log.error(str(exc))  # noqa: TRY400
            self.parser.exit(status=1)

        self._process_files()

    def _process_files(self) -> NoReturn:
        """
        Process the files with the selected codemods.
        """
        try:
            result: ParallelTransformResult = self.processor.process(self.files)
            if result.failures:
                self.parser.exit(status=1)
        except RefineSystemExit as exc:
            self.parser.exit(status=exc.code, message=exc.message)
        except SystemExit as exc:
            code: str | int | None = exc.code
            if code is None:
                self.parser.exit(status=1)
            if isinstance(code, int):
                self.parser.exit(status=code)
            self.parser.exit(status=1, message=code)
        except KeyboardInterrupt:
            self.parser.exit(status=1)
        self.parser.exit(status=0)

    def _setup_parser(self) -> argparse.ArgumentParser:
        """
        Setup the command line parser.
        """
        parser = argparse.ArgumentParser(description=__doc__, prog="refine")
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
        verbosity_group.add_argument(
            "--hide-progress",
            action="store_true",
            default=False,
            help="Hide the progress bar.",
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
        return parser

    def _append_path(self, path: pathlib.Path, repo_root: pathlib.Path, files: list[pathlib.Path]) -> bool:
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

    def _load_config(self, path: pathlib.Path) -> Config:
        """
        Load the configuration from a file.
        """
        if not path.is_absolute():
            config_file = pathlib.Path.cwd().joinpath(path).resolve()
        else:
            config_file = path

        if config_file.exists():
            try:
                relative_config_file_path = config_file.relative_to(pathlib.Path.cwd())
            except ValueError:
                relative_config_file_path = config_file
            log.debug("Loading config from passed: %s", relative_config_file_path)
            if config_file.name == "pyproject.toml":
                config = Config.from_pyproject_file(config_file)
            else:
                config = Config.from_default_file(config_file)
        else:
            pyproject_config_file = pathlib.Path.cwd().joinpath("pyproject.toml")
            if pyproject_config_file.exists():
                log.debug("Loading config from pyproject.toml")
                config = Config.from_pyproject_file(pyproject_config_file)
            else:
                log.debug("Loading default configuration")
                config = Config()

        log.debug("Loaded config:\n%s", pprint.pformat(config.as_dict()))
        return config


def main(argv: list[str] | None = None) -> NoReturn:
    cli = CLI()
    cli.run(argv)


if __name__ == "__main__":
    freeze_support()
    main(sys.argv[1:])

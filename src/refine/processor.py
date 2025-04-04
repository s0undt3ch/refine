"""
Refine processor.

A fair chunk of this module just piggybacks on what libCST does, we just adapt to our own way of processing the files.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import os.path
import shutil
import sys
import tempfile
import traceback
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod import SkipFile
from libcst.codemod._cli import ExecutionResult
from libcst.codemod._cli import Progress
from libcst.codemod._cli import print_execution_result
from libcst.codemod._dummy_pool import DummyPool
from libcst.codemod._runner import SkipReason
from libcst.codemod._runner import TransformExit
from libcst.codemod._runner import TransformFailure
from libcst.codemod._runner import TransformSkip
from libcst.codemod._runner import TransformSuccess
from libcst.helpers import calculate_module_and_package
from libcst.metadata import FullRepoManager

from refine.abc import BaseCodemod
from refine.abc import BaseConfig
from refine.exc import RefineSystemExit

if TYPE_CHECKING:
    from multiprocessing.pool import Pool

    from libcst.metadata.base_provider import ProviderT

    from refine.config import Config
    from refine.registry import Registry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParallelTransformResult:
    """
    This is a copy of :class:`~libcst.codemod._cli.ParallelTransformResult` with an extra ``changed`` field.
    """

    #: Number of files that we successfully transformed.
    successes: int
    #: Number of files that we failed to transform.
    failures: int
    #: Number of warnings generated when running transform across files.
    warnings: int
    #: Number of files skipped because they were blacklisted, generated
    #: or the codemod requested to skip.
    skips: int
    #: Number of files that were actually modified
    changed: int


class Processor:
    """
    Refine codemod processor.
    """

    def __init__(self, config: Config, registry: Registry, codemods: list[type[BaseCodemod]]) -> None:
        self.config = config
        self.registry = registry
        self.codemods = codemods
        codemod_configs = {}
        for codemod in codemods:
            config_dict = getattr(config, codemod.NAME, {})
            try:
                codemod_config = codemod.CONFIG_CLS(**config_dict)
            except AttributeError:
                codemod_config = BaseConfig()
            codemod_configs[codemod.NAME] = codemod_config
        self.codemod_configs = codemod_configs

    def process(self, files: list[Path]) -> ParallelTransformResult:
        """
        Process the passed in list of paths.
        """
        _files = sorted({str(fpath) for fpath in files})
        total = len(_files)
        progress = Progress(enabled=True, total=total)
        chunk_size = 4
        jobs = min(
            self.config.process_pool_size,
            (len(_files) + chunk_size - 1) // chunk_size,
        )
        if jobs < 1:
            error = "Must have at least one job to process!"
            raise RefineSystemExit(code=1, message=error)

        if total == 0:
            return ParallelTransformResult(successes=0, failures=0, skips=0, warnings=0, changed=0)

        pool_impl: partial[Pool] | type[DummyPool]
        if total == 1 or jobs == 1:
            # Simple case, we should not pay for process overhead.
            # Let's just use a dummy synchronous pool.
            jobs = 1
            pool_impl = DummyPool
        else:
            pool_impl = partial(multiprocessing.Pool, maxtasksperchild=chunk_size)
            # Warm the parser, pre-fork.
            cst.parse_module("")

        inherited_dependencies: set[ProviderT] = set()
        for codemod in self.codemods:
            for dependency in codemod.get_inherited_dependencies():
                inherited_dependencies.add(dependency)

        metadata_manager = FullRepoManager(
            self.config.repo_root,
            _files,
            list(inherited_dependencies),
        )
        metadata_manager.resolve_cache()

        successes: int = 0
        failures: int = 0
        warnings: int = 0
        skips: int = 0
        changed: int = 0

        with pool_impl(processes=jobs) as p:
            try:
                for result in p.imap_unordered(
                    partial(self._process_path, metadata_manager), _files, chunksize=chunk_size
                ):
                    # Print an execution result, keep track of failures
                    _print_parallel_result(
                        result,
                        progress,
                        repo_root=self.config.repo_root,
                        unified_diff=False,
                        show_changed=True,
                        show_successes=False,
                        hide_generated=True,
                        hide_blacklisted=True,
                    )
                    progress.print(successes + failures + skips)

                    if isinstance(result.transform_result, TransformFailure):
                        failures += 1
                    elif isinstance(result.transform_result, TransformSuccess):
                        successes += 1
                        if result.changed:
                            changed += 1
                    elif isinstance(result.transform_result, (TransformExit, TransformSkip)):
                        skips += 1

                    if isinstance(result.transform_result, TransformFailure) and self.config.fail_fast:
                        break

                    warnings += len(result.transform_result.warning_messages)
            finally:
                progress.clear()

        # Return whether there was one or more failure.
        return ParallelTransformResult(
            successes=successes, failures=failures, skips=skips, warnings=warnings, changed=changed
        )

    def _process_path(self, metadata_manager: FullRepoManager, filename: str) -> ExecutionResult:
        # determine the module and package name for this file
        try:
            module_name_and_package = calculate_module_and_package(self.config.repo_root or ".", filename)
            mod_name = module_name_and_package.name
            pkg_name = module_name_and_package.package
        except ValueError as exc:
            print(
                f"Failed to determine module name for {os.path.relpath(filename, self.config.repo_root)}: {exc}",
                file=sys.stderr,
            )
            mod_name = None
            pkg_name = None

        # Apart from metadata_manager, every field of context should be reset per file
        context = CodemodContext(
            filename=filename,
            full_module_name=mod_name,
            full_package_name=pkg_name,
            metadata_manager=metadata_manager,
        )

        try:
            with open(filename, encoding="utf-8") as rfh:
                old_code = rfh.read()

            # Run the transform, bail if we failed or if we aren't formatting code
            try:
                input_tree = cst.parse_module(old_code)
                output_tree = input_tree
                for codemod in self.codemods:
                    try:
                        # log.info(" - Applying %s", codemod.NAME)
                        mod = codemod(
                            context=context,
                            # Pass copies of the configuration
                            config=self.codemod_configs[codemod.NAME].model_copy(deep=True),
                        )
                        output_tree = mod.transform_module(output_tree)
                    except SkipFile as exc:
                        log.info(
                            " - Skipping %s on %s: %s",
                            codemod.NAME,
                            os.path.relpath(filename, self.config.repo_root),
                            exc,
                        )
                        continue

                new_code = output_tree.code
            except KeyboardInterrupt:
                return ExecutionResult(
                    filename=filename,
                    changed=False,
                    transform_result=TransformExit(),
                )
            except SkipFile as ex:
                return ExecutionResult(
                    filename=filename,
                    changed=False,
                    transform_result=TransformSkip(
                        skip_reason=SkipReason.OTHER,
                        skip_description=str(ex),
                        warning_messages=context.warnings,
                    ),
                )
            except Exception as ex:
                return ExecutionResult(
                    filename=filename,
                    changed=False,
                    transform_result=TransformFailure(
                        error=ex,
                        traceback_str=traceback.format_exc(),
                        warning_messages=context.warnings,
                    ),
                )
            if new_code != old_code:
                try:
                    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as wfh:
                        wfh.write(new_code)
                        # Ensure all data is written to disk
                        wfh.flush()
                        os.fsync(wfh.fileno())
                        # Since the writing was successful, copy the temporary file over the file
                        # we want to change
                        shutil.copyfile(wfh.name, filename)
                except Exception as exc:
                    return ExecutionResult(
                        filename=filename,
                        changed=False,
                        transform_result=TransformFailure(
                            error=exc,
                            traceback_str=traceback.format_exc(),
                            warning_messages=context.warnings,
                        ),
                    )
                return ExecutionResult(
                    filename=filename,
                    changed=True,
                    transform_result=TransformSuccess(
                        warning_messages=context.warnings,
                        code=new_code,
                    ),
                )
            return ExecutionResult(
                filename=filename,
                changed=False,
                transform_result=TransformSuccess(
                    warning_messages=context.warnings,
                    code=new_code,
                ),
            )
        except KeyboardInterrupt:
            return ExecutionResult(
                filename=filename,
                changed=False,
                transform_result=TransformExit(),
            )
        except Exception as ex:
            return ExecutionResult(
                filename=filename,
                changed=False,
                transform_result=TransformFailure(
                    error=ex,
                    traceback_str=traceback.format_exc(),
                    warning_messages=context.warnings,
                ),
            )


def _print_parallel_result(
    exec_result: ExecutionResult,
    progress: Progress,
    *,
    repo_root: Path,
    unified_diff: bool,
    show_successes: bool,
    show_changed: bool,
    hide_generated: bool,
    hide_blacklisted: bool,
) -> None:
    filename = os.path.relpath(exec_result.filename, repo_root)
    result = exec_result.transform_result

    if isinstance(result, TransformSkip):
        # Skipped file, print message and don't write back since not changed.
        if not (
            (result.skip_reason is SkipReason.BLACKLISTED and hide_blacklisted)
            or (result.skip_reason is SkipReason.GENERATED and hide_generated)
        ):
            progress.clear()
            print(f"Modifying {filename}", file=sys.stderr)
            print_execution_result(result)
            print(
                f"Skipped codemodding {filename}: {result.skip_description}\n",
                file=sys.stderr,
            )
    elif isinstance(result, TransformFailure):
        # Print any exception, don't write the file back.
        progress.clear()
        print(f"Modifying {filename}", file=sys.stderr)
        print_execution_result(result)
        print(f"Failed to codemod {filename}\n", file=sys.stderr)
    elif isinstance(result, TransformSuccess):
        if show_successes or (exec_result.changed and show_changed) or result.warning_messages:
            # Print any warnings, save the changes if there were any.
            progress.clear()
            if show_successes or result.warning_messages:
                print(f"Modifying {filename}", file=sys.stderr)
            print_execution_result(result)
            print(
                f"Successfully codemodded {filename}" + (" with warnings\n" if result.warning_messages else "\n"),
                file=sys.stderr,
            )

        # In unified diff mode, the code is a diff we must print.
        if unified_diff and result.code:
            print(result.code)

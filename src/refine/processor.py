"""
Refine processor.

A fair chunk of this module just piggybacks on what libCST does, we just adapt to our own way of processing the files.
"""

from __future__ import annotations

import itertools
import logging
import multiprocessing
import os
import os.path
import shutil
import sys
import tempfile
import traceback
from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst
import msgspec
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
from refine.exc import InvalidConfigError
from refine.exc import RefineSystemExit

if TYPE_CHECKING:
    from multiprocessing.pool import Pool

    from libcst.metadata.base_provider import ProviderT

    from refine.config import Config
    from refine.registry import Registry

log = logging.getLogger(__name__)

#: Number of processes any single refine invocation may use when running under
#: pre-commit. pre-commit can launch several refine processes concurrently
#: (require_serial: false in old hook configs), so each one must stay small.
PRE_COMMIT_MAX_JOBS = 2


def _get_pool_context() -> multiprocessing.context.BaseContext:
    if sys.platform == "win32":
        return multiprocessing.get_context("spawn")
    context = multiprocessing.get_context("forkserver")
    # Import the heavy modules once in the forkserver parent; every worker
    # forks from it instead of re-importing per process.
    context.set_forkserver_preload(["refine.processor"])
    return context


def _compute_jobs(*, configured_pool_size: int, total_files: int, chunk_size: int, env: Mapping[str, str]) -> int:
    jobs = min(configured_pool_size, (total_files + chunk_size - 1) // chunk_size)
    if "PRE_COMMIT" in env:
        jobs = min(jobs, PRE_COMMIT_MAX_JOBS)
    return jobs


class _Work(msgspec.Struct, frozen=True):
    filename: str
    source: str
    codemod_names: tuple[str, ...]


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
            config_dict = config.__remaining_config__.get(codemod.NAME, {})
            try:
                codemod_config_cls = codemod.CONFIG_CLS
            except AttributeError:
                codemod_config = BaseConfig()
            else:
                try:
                    codemod_config = msgspec.convert(config_dict, codemod_config_cls)
                except msgspec.ValidationError as exc:
                    error_msg = f"Invalid configuration for codemod {codemod.NAME}: {exc}"
                    raise InvalidConfigError(error_msg) from exc
            codemod_configs[codemod.NAME] = codemod_config
        self.codemod_configs = codemod_configs
        self.codemods_by_name = {codemod.NAME: codemod for codemod in codemods}

    def _build_work(self, files: list[str]) -> Iterator[_Work | ExecutionResult]:
        """
        Read each file once in the parent and decide which codemods apply.

        Yields ready-made clean ExecutionResults for files no codemod wants,
        and _Work items (carrying the already-read source) for the rest.
        """
        for filename in files:
            try:
                with open(filename, encoding="utf-8") as rfh:
                    source = rfh.read()
            except Exception as exc:
                yield ExecutionResult(
                    filename=filename,
                    changed=False,
                    transform_result=TransformFailure(
                        error=exc, traceback_str=traceback.format_exc(), warning_messages=[]
                    ),
                )
                continue
            applicable = []
            for codemod in self.codemods:
                try:
                    wanted = codemod.should_process(source, filename)
                except Exception:
                    # Gates must fail open: never silently skip work.
                    wanted = True
                if wanted:
                    applicable.append(codemod.NAME)
            if not applicable:
                yield ExecutionResult(
                    filename=filename,
                    changed=False,
                    transform_result=TransformSuccess(warning_messages=[], code=source),
                )
                continue
            yield _Work(filename=filename, source=source, codemod_names=tuple(applicable))

    def process(self, files: list[Path]) -> ParallelTransformResult:
        """
        Process the passed in list of paths.
        """
        _files = sorted({str(fpath) for fpath in files})
        total = len(_files)
        progress = Progress(enabled=self.config.hide_progress is False, total=total)
        chunk_size = 4

        if total == 0:
            # Zero input files: preserve the original "no jobs to run" error.
            jobs = _compute_jobs(
                configured_pool_size=self.config.process_pool_size,
                total_files=total,
                chunk_size=chunk_size,
                env=os.environ,
            )
            if jobs < 1:
                error = "Must have at least one job to process!"
                raise RefineSystemExit(code=1, message=error)
            return ParallelTransformResult(successes=0, failures=0, skips=0, warnings=0, changed=0)

        work_items: list[_Work] = []
        pre_results: list[ExecutionResult] = []
        for item in self._build_work(_files):
            if isinstance(item, _Work):
                work_items.append(item)
            else:
                pre_results.append(item)

        # Pool is sized after gating: files no codemod wants are never
        # dispatched, so they must not inflate the job count.
        jobs = _compute_jobs(
            configured_pool_size=self.config.process_pool_size,
            total_files=len(work_items),
            chunk_size=chunk_size,
            env=os.environ,
        )

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

        def _account(result: ExecutionResult) -> bool:
            """
            Update the running counters for one result.

            Returns True when processing should stop (fail_fast tripped).
            """
            nonlocal successes, failures, warnings, skips, changed
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
                return True

            warnings += len(result.transform_result.warning_messages)
            return False

        if not work_items:
            # Every file was gated out before parsing: nothing to dispatch,
            # so we skip pool construction entirely (jobs would be 0 here,
            # but that must not raise: the original file list wasn't empty).
            try:
                for result in pre_results:
                    if _account(result):
                        break
            finally:
                progress.clear()
        else:
            pool_impl: partial[Pool] | type[DummyPool]
            if len(work_items) == 1 or jobs == 1:
                # Simple case, we should not pay for process overhead.
                # Let's just use a dummy synchronous pool.
                jobs = 1
                pool_impl = DummyPool
            else:
                # No maxtasksperchild: workers live for the whole run instead of
                # being killed and re-spawned (and re-importing everything) every
                # few tasks.
                pool_impl = partial(_get_pool_context().Pool)

            with pool_impl(processes=jobs) as p:
                try:
                    for result in itertools.chain(
                        pre_results,
                        p.imap_unordered(
                            partial(self._process_path, metadata_manager), work_items, chunksize=chunk_size
                        ),
                    ):
                        if _account(result):
                            break
                finally:
                    progress.clear()

        # Return whether there was one or more failure.
        return ParallelTransformResult(
            successes=successes, failures=failures, skips=skips, warnings=warnings, changed=changed
        )

    def _process_path(self, metadata_manager: FullRepoManager, work: _Work) -> ExecutionResult:
        filename = work.filename
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
            old_code = work.source

            # Run the transform, bail if we failed or if we aren't formatting code
            try:
                input_tree = cst.parse_module(old_code)
                output_tree = input_tree
                for codemod_name in work.codemod_names:
                    codemod = self.codemods_by_name[codemod_name]
                    try:
                        # log.info(" - Applying %s", codemod.NAME)
                        mod = codemod(
                            context=context,
                            # Pass copies of the configuration
                            config=self.codemod_configs[codemod_name],
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
    repo_root: str,
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

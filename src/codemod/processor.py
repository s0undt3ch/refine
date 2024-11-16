"""
Codemod processor.
"""

import logging
import multiprocessing
from pathlib import Path

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod import SkipFile

from codemod.abc import BaseCodemod
from codemod.abc import BaseConfig
from codemod.config import Config
from codemod.registry import Registry

log = logging.getLogger(__name__)


class Processor:
    """
    Codemod processor.
    """

    def __init__(
        self, config: Config, registry: Registry, codemods: list[type[BaseCodemod]]
    ) -> None:
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

    def process(self, paths: list[Path]):
        """
        Process the passed in list of paths.
        """
        modified = 0
        failures = 0

        log.info("Processing %s files ...", len(paths))

        def _process_completed(path):
            nonlocal modified
            if path:
                log.info("Saved changes to %s", path)
                modified += 1

        def _process_failed(exception):
            nonlocal failures
            failures += 1

        with multiprocessing.Pool(self.config.process_pool_size) as pool:
            for path in paths:
                pool.apply_async(
                    self.process_file,
                    args=(path,),
                    callback=_process_completed,
                    error_callback=_process_failed,
                )

            # Wait for all tasks to complete before exiting the program
            pool.close()
            pool.join()

        log.info("Processed %d files. Modified: %s; Failures: %s", len(paths), modified, failures)

    def process_file(self, path: Path) -> Path | None:
        """
        Process a single file.

        This is what get's called from the process pool instance.
        """
        context = CodemodContext(filename=str(path))
        tree: cst.Module = cst.parse_module(path.read_text())
        modified_tree: cst.Module = tree
        for codemod in self.codemods:
            try:
                log.info(" - Applying %s", codemod.NAME)
                mod = codemod(context=context, config=self.codemod_configs[codemod.NAME])
                modified_tree = mod.transform_module(modified_tree)
            except SkipFile:
                continue
        if modified_tree.code != tree.code:
            log.info("Saving changes to %s", path)
            path.write_text(modified_tree.code)
            return path
        return None

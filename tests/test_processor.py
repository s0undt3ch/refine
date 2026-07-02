from __future__ import annotations

import logging
import pathlib
import shutil
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from refine.mods.cli.flags import CliDashes
from refine.processor import Processor
from refine.processor import _compute_jobs

log = logging.getLogger(__name__)

TESTS_DIR = pathlib.Path(__file__).parent.resolve()
TEST_FILE_PATH = TESTS_DIR / "mods/cli/files/flags/annotated-function.py"
TEST_FILE_UPDATED_PATH = TESTS_DIR / "mods/cli/files/flags/annotated-function.updated.py"


@pytest.mark.skip_on_windows
def test_write_file_exception(tmp_path, subtests):
    # Just make sure we are not copying an empty file
    assert TEST_FILE_PATH.exists()
    assert TEST_FILE_UPDATED_PATH.exists()
    assert TEST_FILE_PATH.read_text() != ""

    tmp_file_path = tmp_path / TEST_FILE_PATH.name
    shutil.copyfile(TEST_FILE_PATH, tmp_file_path)

    # Mock configuration and registry objects
    config = MagicMock()
    config.repo_root = tmp_path
    config.process_pool_size = 1
    config.__remaining_config__ = {}

    registry = MagicMock()
    codemods = [CliDashes]
    processor = Processor(config=config, registry=registry, codemods=codemods)

    with subtests.test("Failing behaviour"):
        # Patch the file-writing operation to raise an exception
        with patch("tempfile.NamedTemporaryFile") as mock_tempfile:
            mock_tempfile.return_value.__enter__.return_value.write.side_effect = Exception("Write error")
            # We are not interested in seeing the output
            with patch("refine.processor._print_parallel_result", MagicMock()):
                processor.process([tmp_file_path])

        # Ensure the file's content remains unchanged after the exception
        assert tmp_file_path.read_text() == TEST_FILE_PATH.read_text()

    # Just for the sake of completeness, what if we don't raise an exception?
    with subtests.test("Non-failing behaviour"):
        # We are not interested in seeing the output
        with patch("refine.processor._print_parallel_result", MagicMock()):
            processor.process([tmp_file_path])

        # Contents should no longer match
        assert tmp_file_path.read_text() != TEST_FILE_PATH.read_text()
        # They should however match the updated file contents
        assert tmp_file_path.read_text() == TEST_FILE_UPDATED_PATH.read_text()


def test_compute_jobs_caps_to_chunked_file_count():
    assert _compute_jobs(configured_pool_size=8, total_files=4, chunk_size=4, env={}) == 1
    assert _compute_jobs(configured_pool_size=8, total_files=17, chunk_size=4, env={}) == 5


def test_compute_jobs_caps_to_configured_pool_size():
    assert _compute_jobs(configured_pool_size=2, total_files=100, chunk_size=4, env={}) == 2


def test_compute_jobs_pre_commit_env_caps_pool():
    assert _compute_jobs(configured_pool_size=8, total_files=100, chunk_size=4, env={"PRE_COMMIT": "1"}) == 2


def test_compute_jobs_pre_commit_env_does_not_raise_floor():
    # A single chunk of work stays a single job even under pre-commit
    assert _compute_jobs(configured_pool_size=8, total_files=3, chunk_size=4, env={"PRE_COMMIT": "1"}) == 1


def test_compute_jobs_zero_files_returns_zero():
    assert _compute_jobs(configured_pool_size=8, total_files=0, chunk_size=4, env={}) == 0

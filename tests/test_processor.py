from __future__ import annotations

import logging
import pathlib
import shutil
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

import libcst
import pytest

from refine.config import Config
from refine.exc import RefineSystemExit
from refine.mods.cli.flags import CliDashes
from refine.processor import Processor
from refine.processor import _compute_jobs
from refine.processor import _get_pool_context
from refine.registry import Registry

log = logging.getLogger(__name__)

TESTS_DIR = pathlib.Path(__file__).parent.resolve()
TEST_FILE_PATH = TESTS_DIR / "mods/cli/files/flags/annotated-function.py"
TEST_FILE_UPDATED_PATH = TESTS_DIR / "mods/cli/files/flags/annotated-function.updated.py"
FIXTURES = TESTS_DIR / "mods" / "cli" / "files" / "flags"


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


def test_process_zero_files_raises():
    config = MagicMock()
    config.repo_root = "."
    config.process_pool_size = 1
    config.hide_progress = True
    config.__remaining_config__ = {}

    registry = MagicMock()
    codemods = [CliDashes]
    processor = Processor(config=config, registry=registry, codemods=codemods)
    with pytest.raises(RefineSystemExit):
        processor.process([])


def test_pool_context_platform_selection():
    ctx = _get_pool_context()
    if sys.platform == "win32":
        assert ctx.get_start_method() == "spawn"
    else:
        assert ctx.get_start_method() == "forkserver"


def _fixture_pairs():
    for path in sorted(FIXTURES.glob("*.py")):
        if path.stem.endswith(".updated"):
            continue
        updated = path.with_stem(f"{path.stem}.updated")
        if updated.exists():
            yield path, updated


def test_pooled_run_matches_dummy_pool_run(tmp_path):
    # Lay out >4 copies of fixture files so the real multiprocessing pool engages.
    registry = Registry()
    registry.load([])
    codemods = list(registry.codemods(select_codemods=["cli-dashes-over-underscores"]))
    assert codemods

    work_files = []
    expected = {}
    for i in range(3):  # 3 copies of each fixture -> well over one chunk
        for original, updated in _fixture_pairs():
            target = tmp_path / f"copy{i}" / original.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
            work_files.append(target)
            expected[target] = updated.read_text()

    config = Config.from_dict({"repo_root": str(tmp_path), "process_pool_size": 2, "hide_progress": True})
    processor = Processor(config=config, registry=registry, codemods=codemods)
    result = processor.process(work_files)

    assert result.failures == 0
    for target, expected_content in expected.items():
        assert target.read_text() == expected_content, f"mismatch for {target}"


def test_gated_out_files_are_never_parsed(tmp_path, monkeypatch):
    target = tmp_path / "plain.py"
    target.write_text("def add(a, b):\n    return a + b\n")

    registry = Registry()
    registry.load([])
    codemods = list(registry.codemods(select_codemods=["sqlfmt"]))

    parse_calls = []
    real_parse = libcst.parse_module

    def counting_parse(*args, **kwargs):
        parse_calls.append(args)
        return real_parse(*args, **kwargs)

    monkeypatch.setattr("refine.processor.cst.parse_module", counting_parse)

    config = Config.from_dict({"repo_root": str(tmp_path), "process_pool_size": 1, "hide_progress": True})
    processor = Processor(config=config, registry=registry, codemods=codemods)
    result = processor.process([target])

    assert result.failures == 0
    assert result.successes == 1  # gated-out counts as a clean success
    assert parse_calls == []


def test_config_excluded_file_is_never_parsed(tmp_path, monkeypatch):
    target = tmp_path / "flags.py"
    target.write_text('parser.add_argument("--dry_run")\n')

    registry = Registry()
    registry.load([])
    codemods = list(registry.codemods(select_codemods=["cli-dashes-over-underscores"]))

    parse_calls = []
    real_parse = libcst.parse_module

    def counting_parse(*args, **kwargs):
        parse_calls.append(args)
        return real_parse(*args, **kwargs)

    monkeypatch.setattr("refine.processor.cst.parse_module", counting_parse)

    config = Config.from_dict(
        {
            "repo_root": str(tmp_path),
            "process_pool_size": 1,
            "hide_progress": True,
            "cli-dashes-over-underscores": {"exclude": ["*flags.py"]},
        }
    )
    processor = Processor(config=config, registry=registry, codemods=codemods)
    result = processor.process([target])

    assert result.failures == 0
    assert parse_calls == []
    # File untouched
    assert target.read_text() == 'parser.add_argument("--dry_run")\n'

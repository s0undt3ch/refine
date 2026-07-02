from __future__ import annotations

from refine.cache import Cache
from refine.cache import compute_context_key
from refine.mods.cli.flags import CliDashes
from refine.mods.cli.flags import CliDashesConfig


def test_roundtrip(tmp_path):
    cache = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    assert not cache.is_clean("a.py", "print(1)\n")
    cache.mark_clean("a.py", "print(1)\n")
    assert cache.is_clean("a.py", "print(1)\n")
    cache.dump()

    reloaded = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    assert reloaded.is_clean("a.py", "print(1)\n")


def test_content_change_invalidates(tmp_path):
    cache = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    cache.mark_clean("a.py", "print(1)\n")
    assert not cache.is_clean("a.py", "print(2)\n")


def test_context_key_change_discards_everything(tmp_path):
    cache = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    cache.mark_clean("a.py", "print(1)\n")
    cache.dump()

    reloaded = Cache.load(tmp_path / ".refine_cache", "ctx-2")
    assert not reloaded.is_clean("a.py", "print(1)\n")


def test_corrupt_cache_file_is_treated_as_miss(tmp_path):
    cache_dir = tmp_path / ".refine_cache"
    cache_dir.mkdir()
    (cache_dir / "cache.msgpack").write_bytes(b"definitely not msgpack")
    cache = Cache.load(cache_dir, "ctx-1")
    assert not cache.is_clean("a.py", "print(1)\n")


def test_dump_writes_gitignore(tmp_path):
    cache = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    cache.dump()
    assert (tmp_path / ".refine_cache" / ".gitignore").read_text() == "*\n"


def test_dump_prunes_deleted_files(tmp_path):
    kept = tmp_path / "kept.py"
    kept.write_text("x = 1\n")
    cache = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    cache.mark_clean(str(kept), "x = 1\n")
    cache.mark_clean(str(tmp_path / "deleted.py"), "gone\n")
    cache.dump()

    reloaded = Cache.load(tmp_path / ".refine_cache", "ctx-1")
    assert reloaded.is_clean(str(kept), "x = 1\n")
    assert not reloaded.is_clean(str(tmp_path / "deleted.py"), "gone\n")


def test_context_key_changes_with_config():
    base = compute_context_key(
        refine_version="1.0",
        codemods=[CliDashes],
        codemod_configs={"cli-dashes-over-underscores": CliDashesConfig()},
    )
    changed_config = compute_context_key(
        refine_version="1.0",
        codemods=[CliDashes],
        codemod_configs={"cli-dashes-over-underscores": CliDashesConfig(exclude=["x/*"])},
    )
    changed_version = compute_context_key(
        refine_version="1.1",
        codemods=[CliDashes],
        codemod_configs={"cli-dashes-over-underscores": CliDashesConfig()},
    )
    assert base != changed_config
    assert base != changed_version
    assert base == compute_context_key(
        refine_version="1.0",
        codemods=[CliDashes],
        codemod_configs={"cli-dashes-over-underscores": CliDashesConfig()},
    )

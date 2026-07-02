"""
Persistent run cache.

Skips files whose content is unchanged since the last run under the same
"context" (refine version + selected codemods + their source + their config).
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec

if TYPE_CHECKING:
    from refine.abc import BaseCodemod
    from refine.abc import BaseConfig

log = logging.getLogger(__name__)

_CACHE_FILE_NAME = "cache.msgpack"


class _CachePayload(msgspec.Struct):
    context_key: str
    files: dict[str, str] = msgspec.field(default_factory=dict)


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_context_key(
    *,
    refine_version: str,
    codemods: list[type[BaseCodemod]],
    codemod_configs: dict[str, BaseConfig],
) -> str:
    hasher = hashlib.sha256()
    hasher.update(refine_version.encode())
    for codemod in sorted(codemods, key=lambda c: c.NAME):
        hasher.update(codemod.NAME.encode())
        source_file = inspect.getsourcefile(codemod)
        if source_file and Path(source_file).exists():
            hasher.update(Path(source_file).read_bytes())
        codemod_config = codemod_configs[codemod.NAME]
        hasher.update(msgspec.json.encode(codemod_config))
        for cache_key_path in codemod_config.cache_key_paths():
            path = Path(cache_key_path)
            try:
                hasher.update(path.read_bytes())
            except OSError:
                # Missing file: config validation already errors on this
                # elsewhere; fall back to hashing the path string so the key
                # is still deterministic.
                hasher.update(cache_key_path.encode())
    return hasher.hexdigest()


class Cache:
    """
    Content-hash cache over a single msgpack file.
    """

    def __init__(self, cache_dir: Path, context_key: str, files: dict[str, str]) -> None:
        self._cache_dir = cache_dir
        self._context_key = context_key
        self._files = files

    @classmethod
    def load(cls, cache_dir: Path, context_key: str) -> Cache:
        """Load cache from disk; return empty cache if missing or corrupted."""
        cache_file = cache_dir / _CACHE_FILE_NAME
        files: dict[str, str] = {}
        if cache_file.exists():
            try:
                payload = msgspec.msgpack.decode(cache_file.read_bytes(), type=_CachePayload)
            except (msgspec.DecodeError, msgspec.ValidationError, OSError) as exc:
                log.debug("Discarding unreadable cache file %s: %s", cache_file, exc)
            else:
                if payload.context_key == context_key:
                    files = payload.files
        return cls(cache_dir, context_key, files)

    def is_clean(self, filename: str, source: str) -> bool:
        """Check if file content hash matches cached entry."""
        return self._files.get(filename) == _hash(source.encode())

    def mark_clean(self, filename: str, source: str) -> None:
        """Record file content hash in cache."""
        self._files[filename] = _hash(source.encode())

    def dump(self) -> None:
        """Write cache to disk, pruning entries for deleted absolute paths."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        gitignore = self._cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")
        # Opportunistic pruning: drop entries for files that no longer exist.
        # Only prune absolute paths; keep relative paths as they may be valid in a different cwd.
        files = {
            filename: digest
            for filename, digest in self._files.items()
            if not os.path.isabs(filename) or os.path.exists(filename)
        }
        payload = _CachePayload(context_key=self._context_key, files=files)
        (self._cache_dir / _CACHE_FILE_NAME).write_bytes(msgspec.msgpack.encode(payload))

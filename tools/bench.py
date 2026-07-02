"""
Benchmark harness for refine.

Usage:
    uv run python tools/bench.py <corpus-dir> [--select CODEMOD]... [--runs N]

Copies the corpus into a temp dir (so files never get modified in place),
then times three scenarios:
  full        - one refine invocation over every file (fresh copy each run)
  rerun       - a second invocation over the SAME already-refined tree
  pre-commit  - PRE_COMMIT=1 invocation over a 10-file slice (fresh copy)
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _run_refine(cwd: Path, files: list[Path], *, extra_env: dict[str, str] | None = None) -> float:
    env = os.environ | (extra_env or {})
    start = time.perf_counter()
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "refine", "--hide-progress", *map(str, files)],
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
    )
    return time.perf_counter() - start


def _copy_corpus(corpus: Path, dest: Path) -> list[Path]:
    files = []
    for src in corpus.rglob("*.py"):
        rel = src.relative_to(corpus)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        files.append(target)
    for name in (".refine.toml", "pyproject.toml"):
        cfg = corpus / name
        if cfg.exists():
            shutil.copyfile(cfg, dest / name)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    results: dict[str, list[float]] = {"full": [], "rerun": [], "pre-commit": []}
    for _ in range(args.runs):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            files = _copy_corpus(args.corpus, dest)
            results["full"].append(_run_refine(dest, files))
            results["rerun"].append(_run_refine(dest, files))
            results["pre-commit"].append(_run_refine(dest, files[:10], extra_env={"PRE_COMMIT": "1"}))

    print(f"corpus: {args.corpus} ({len(files)} files), runs: {args.runs}")  # noqa: T201
    for scenario, timings in results.items():
        print(  # noqa: T201
            f"{scenario:>11}: median {statistics.median(timings):7.2f}s"
            f"  min {min(timings):7.2f}s  max {max(timings):7.2f}s"
        )


if __name__ == "__main__":
    main()

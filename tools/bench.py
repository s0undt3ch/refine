"""
Benchmark harness for refine.

Usage:
    uv run python tools/bench.py <corpus-dir> [--select CODEMOD]... [--runs N]

Copies the corpus into a temp dir (so files never get modified in place),
then times three scenarios:
  full        - one refine invocation over every file (fresh copy each run)
  rerun       - a second invocation over the SAME already-refined tree
  pre-commit  - PRE_COMMIT=1 invocation over a 10-file slice of its own fresh copy
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


def _run_refine(
    cwd: Path,
    files: list[Path],
    *,
    extra_env: dict[str, str] | None = None,
    select: list[str] | None = None,
) -> float:
    env = os.environ | (extra_env or {})
    argv = [sys.executable, "-m", "refine", "--hide-progress"]
    for codemod in select or []:
        argv.extend(["--select-codemod", codemod])
    argv.extend(map(str, files))
    start = time.perf_counter()
    proc = subprocess.run(  # noqa: S603
        argv,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        stderr_tail = "\n".join(proc.stderr.splitlines()[-5:])
        print(  # noqa: T201
            f"warning: refine invocation exited with code {proc.returncode} in {cwd}\n{stderr_tail}",
            file=sys.stderr,
        )
    return elapsed


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


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        msg = f"--runs must be >= 1, got {value!r}"
        raise argparse.ArgumentTypeError(msg)
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--runs", type=_positive_int, default=3)
    parser.add_argument(
        "--select",
        action="append",
        default=[],
        metavar="CODEMOD",
        help="Restrict the benchmark to specific codemods (repeatable).",
    )
    args = parser.parse_args()

    results: dict[str, list[float]] = {"full": [], "rerun": [], "pre-commit": []}
    file_count = 0
    for _ in range(args.runs):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            files = _copy_corpus(args.corpus, dest)
            file_count = len(files)
            results["full"].append(_run_refine(dest, files, select=args.select))
            results["rerun"].append(_run_refine(dest, files, select=args.select))

        with tempfile.TemporaryDirectory() as pc_tmp:
            pc_dest = Path(pc_tmp)
            pc_files = _copy_corpus(args.corpus, pc_dest)
            results["pre-commit"].append(
                _run_refine(pc_dest, pc_files[:10], extra_env={"PRE_COMMIT": "1"}, select=args.select)
            )

    print(f"corpus: {args.corpus} ({file_count} files), runs: {args.runs}")  # noqa: T201
    for scenario, timings in results.items():
        print(  # noqa: T201
            f"{scenario:>11}: median {statistics.median(timings):7.2f}s"
            f"  min {min(timings):7.2f}s  max {max(timings):7.2f}s"
        )


if __name__ == "__main__":
    main()

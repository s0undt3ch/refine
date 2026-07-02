"""
sqruff-backed SQL formatting.

sqruff's Python wheel only exposes a CLI entry point, so formatting shells out
to the binary. The subprocess cost is negligible next to sqlfluff's in-process
~270ms/query.

CLI contract (verified against sqruff 0.38.0 in the Step 1 spike; see
task-12-report.md for the full transcript):

* ``sqruff fix -`` reads the query from stdin and writes the (best-effort)
  fixed SQL to stdout; diagnostics go to stderr. This holds even when the
  input is unparsable -- sqruff still prints *something* to stdout.
* ``--parsing-errors`` makes sqruff report (and, combined with our reading of
  stderr, let us detect) truly unparsable input via a literal
  ``Unparsable section`` marker on stderr. Without this flag, unparsable
  sections are silently swallowed and the process still exits 0.
* The process exit code reflects whether *all* reported violations were
  fixed, not just whether the input parsed. A rule that sqruff cannot
  auto-fix (e.g. ``aliasing.length``/AL06) makes the process exit non-zero
  even for perfectly valid, successfully-reformatted SQL. Because of this we
  deliberately keep the bundled ``.sqruff`` config free of non-auto-fixable
  rules (see the comments in that file) so that "exit code != 0" reliably
  means "sqruff could not produce a clean fix" (usually: unparsable input).
* ``--config <path>`` accepts an arbitrary file path (no ``.sqruff`` naming
  or cwd requirement) and takes priority over any config file that would
  otherwise be discovered from the working directory.
* A config file may contain more than one ``[sqruff]`` section; when it
  does, keys from the later section win. We use this to layer the per-call
  ``dialect``/``max_line_length`` override on top of the bundled rule
  defaults without needing a full INI merge.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sysconfig
import tempfile
from functools import cache
from pathlib import Path

log = logging.getLogger(__name__)

#: Maximum time to wait for the sqruff subprocess before giving up on formatting.
SQRUFF_TIMEOUT_SECONDS = 30

BUNDLED_SQRUFF_CONFIG = Path(__file__).parent / ".sqruff"

_UNPARSABLE_MARKER = "Unparsable section"


@cache
def find_sqruff() -> str | None:
    # Prefer the console script installed with the `sqruff` wheel (same venv),
    # fall back to whatever is on PATH (e.g. mise/aqua installs).
    scripts_dir = Path(sysconfig.get_path("scripts"))
    candidate = scripts_dir / "sqruff"
    if candidate.exists():
        return str(candidate)
    return shutil.which("sqruff")


def _run_sqruff(binary: str, config_path: Path, query: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(  # noqa: S603 -- `binary` comes from find_sqruff(), not untrusted input
            [binary, "fix", "--parsing-errors", "--config", str(config_path), "-"],
            input=query,
            capture_output=True,
            text=True,
            check=False,
            timeout=SQRUFF_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log.debug("sqruff timed out after %s seconds; leaving query unformatted", SQRUFF_TIMEOUT_SECONDS)
        return None


def format_sql(
    query: str,
    *,
    dialect: str,
    max_line_length: int,
    config_dir: Path | None = None,
) -> str | None:
    binary = find_sqruff()
    if binary is None:
        log.warning("sqruff binary not found; leaving query unformatted")
        return None

    base_config_path = (config_dir / ".sqruff") if config_dir else BUNDLED_SQRUFF_CONFIG
    try:
        base = base_config_path.read_text()
    except OSError:
        log.warning("could not read sqruff config at %s; leaving query unformatted", base_config_path)
        return None

    # Layer the per-call dialect/max-line-length on top of the base config by
    # appending a second `[sqruff]` section -- sqruff accepts duplicate
    # sections and later keys win (verified in the Step 1 spike).
    override = f"\n[sqruff]\ndialect = {dialect}\nmax_line_length = {max_line_length}\n"
    config_text = base + override

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sqruff", prefix="refine-sqruff-", delete=False) as tmp_config:
        tmp_config.write(config_text)
        tmp_config_path = Path(tmp_config.name)

    try:
        proc = _run_sqruff(binary, tmp_config_path, query)
    finally:
        tmp_config_path.unlink(missing_ok=True)

    return _extract_output(proc)


def _extract_output(proc: subprocess.CompletedProcess[str] | None) -> str | None:
    if proc is None:
        return None
    if _UNPARSABLE_MARKER in proc.stderr:
        log.debug("sqruff could not parse query: %s", proc.stderr)
        return None
    if proc.returncode != 0:
        log.debug("sqruff could not fix query (rc=%s): %s", proc.returncode, proc.stderr)
        return None
    if not proc.stdout.strip():
        log.debug("sqruff produced no output for query")
        return None
    return proc.stdout.rstrip("\n")

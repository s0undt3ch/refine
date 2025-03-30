# type: ignore
from __future__ import annotations

import contextlib

try:
    from .version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.not-installed"
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version

    with contextlib.suppress(PackageNotFoundError):
        __version__ = version("re-code")

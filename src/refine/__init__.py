from __future__ import annotations

import contextlib

try:
    from refine._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.not-installed"
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version

    with contextlib.suppress(PackageNotFoundError):
        __version__ = version("re-code")

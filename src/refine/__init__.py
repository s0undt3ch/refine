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

__all__ = ["__version__"]

with contextlib.suppress(ImportError):  # pragma: no cover
    # Register pytest rewrite for better error messages in tests
    import pytest

    pytest.register_assert_rewrite("refine.testing")

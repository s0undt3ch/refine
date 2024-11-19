from __future__ import annotations

import pytest

# Make sure the assertion we do in codemod/testing.py gets rewritten by pytest for proper visualization
# of assertion failures
pytest.register_assert_rewrite("codemod.testing")

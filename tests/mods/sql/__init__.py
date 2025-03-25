from __future__ import annotations

import logging

# Quiet down sqlfluff logs during tests
logging.getLogger("sqlfluff").setLevel(logging.WARNING)

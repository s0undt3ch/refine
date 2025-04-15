"""
python -m refine entry-point.
"""

from __future__ import annotations

import sys
from multiprocessing import freeze_support

from refine.cli import main

if __name__ == "__main__":
    freeze_support()
    main(sys.argv[1:])

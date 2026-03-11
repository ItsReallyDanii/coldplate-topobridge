"""pytest configuration for coldplate-topobridge tests.

Experiment-directory isolation
-------------------------------
The test suite contains modules from two experiment directories
(analytical_2d_critic, multi_slice_3d_critic) that have identically named
files: run_demo.py, extract_descriptors.py.  When pytest collects all test
files in a single session, whichever directory's version is imported first
wins for all subsequent bare-name imports from the other directory, causing
order-dependent TypeError failures.

This conftest does NOT register any experiment directory on sys.path here.
Each test file is responsible for:
  1. Ensuring its experiment directory is at sys.path[0] before importing
     any experiment-local name.
  2. Clearing any stale sys.modules entries for bare experiment-local names
     (run_demo, extract_descriptors, generate_stack, generate_fields)
     before importing, so the correct version loads from the correct path.

The src/ directory IS registered here (once, at session scope) because the
topobridge package has no naming collision risk and is needed by all tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"

# Register src/ once so `from topobridge.X import Y` resolves for all tests.
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

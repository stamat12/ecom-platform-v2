from __future__ import annotations

import sys
from pathlib import Path

def add_legacy_to_syspath() -> Path:
    """
    Adds backend/legacy to sys.path so we can import legacy config and agents
    without rewriting them yet.
    """
    backend_dir = Path(__file__).resolve().parents[2]          # .../backend
    legacy_dir = backend_dir / "legacy"                        # .../backend/legacy
    if str(legacy_dir) not in sys.path:
        sys.path.insert(0, str(legacy_dir))
    return legacy_dir

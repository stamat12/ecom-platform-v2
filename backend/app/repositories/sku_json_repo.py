from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _sku_json_path(sku: str) -> Path:
    products_dir = Path(getattr(config, "PRODUCTS_FOLDER_PATH"))
    return products_dir / f"{sku}.json"


def read_sku_json(sku: str) -> Dict[str, Any]:
    path = _sku_json_path(sku)
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))

    # Your JSON files are structured like: { "JAL00022": {...fields...} }
    if isinstance(data, dict) and sku in data and isinstance(data[sku], dict):
        return data[sku]

    # fallback: if already flat dict
    if isinstance(data, dict):
        return data

    return {}

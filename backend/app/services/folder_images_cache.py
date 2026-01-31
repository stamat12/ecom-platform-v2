"""Folder Images cache management"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _get_cache_path() -> Path:
    """Get the path to the folder images cache file"""
    cache_dir = Path(getattr(config, "PRODUCTS_FOLDER_PATH")).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / "folder_images_cache.json"


def read_cache() -> Dict[str, Any]:
    """Read the folder images cache"""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return {"timestamp": None, "counts": {}}
    
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"timestamp": None, "counts": {}}


def write_cache(counts: Dict[str, int], timestamp: str | None = None) -> None:
    """Write the folder images cache"""
    cache_path = _get_cache_path()
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    data = {
        "timestamp": timestamp,
        "counts": counts
    }
    
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_folder_image_count(sku: str) -> int | None:
    """Get cached folder image count for a SKU"""
    cache = read_cache()
    return cache.get("counts", {}).get(sku)


def get_last_update_time() -> str | None:
    """Get the timestamp of the last cache update"""
    cache = read_cache()
    return cache.get("timestamp")

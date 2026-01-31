"""Folder Images computation service"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Iterator
from datetime import datetime

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore

from app.services.excel_inventory import excel_inventory
from app.services.folder_images_cache import write_cache


def compute_folder_images_for_all_skus() -> Iterator[Dict[str, any]]:
    """
    Compute folder images for all SKUs and yield progress updates.
    
    Yields progress updates in format:
    {
        "status": "progress" | "complete",
        "current": int,
        "total": int,
        "sku": str,
        "count": int,
        "timestamp": str (only for complete)
    }
    """
    df = excel_inventory.load()
    
    # Get SKU column
    sku_col = None
    if "SKU (Old)" in df.columns:
        sku_col = "SKU (Old)"
    elif "SKU" in df.columns:
        sku_col = "SKU"
    
    if sku_col is None:
        yield {"status": "error", "message": "No SKU column found"}
        return
    
    skus = df[sku_col].dropna().astype(str).unique().tolist()
    total = len(skus)
    
    counts = {}
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}
    
    trading_root = Path(getattr(config, "TRADING_ROOT"))
    roots = [
        trading_root / "Images",
        trading_root.parent / "HANDEL_SEGMENT" / "Images",
        trading_root.parent / "AUCTIONS_SEGMENT" / "Auktionen" / "_FOTOS",
        trading_root.parent / "BAGS_SEGMENT" / "Images",
    ]
    
    for idx, sku in enumerate(skus, 1):
        count = 0
        for root in roots:
            folder = root / sku
            if not folder.exists() or not folder.is_dir():
                continue
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in image_exts:
                    count += 1
        
        counts[sku] = count
        
        yield {
            "status": "progress",
            "current": idx,
            "total": total,
            "sku": sku,
            "count": count
        }
    
    # Write cache
    timestamp = datetime.now().isoformat()
    write_cache(counts, timestamp)
    
    yield {
        "status": "complete",
        "current": total,
        "total": total,
        "timestamp": timestamp
    }

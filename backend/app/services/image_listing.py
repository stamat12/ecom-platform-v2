from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.repositories.sku_json_repo import read_sku_json

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _image_base_dirs() -> List[Path]:
    # Prefer env override for portability
    env_dirs = os.getenv("IMAGE_BASE_DIRS")
    if env_dirs:
        return [Path(p.strip()) for p in env_dirs.split(";") if p.strip()]

    # fallback: legacy config
    bases = getattr(config, "IMAGE_FOLDER_PATHS", [])
    return [Path(p) for p in bases]


def _find_sku_dir(sku: str) -> Path | None:
    for base in _image_base_dirs():
        candidate = base / sku
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def list_images_for_sku(sku: str) -> Dict[str, Any]:
    from app.services.image_classification import get_image_classification
    from app.services.main_image import get_main_images
    
    sku_dir = _find_sku_dir(sku)
    files: List[str] = []

    if sku_dir:
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = sorted(
            [
                p.name
                for p in sku_dir.iterdir()
                if p.is_file() and p.suffix.lower() in exts
            ]
        )

    meta = read_sku_json(sku)

    # Your JSON samples store images like:
    # meta["Images"] = {"filename.jpg": {"image_classification": "...", ...}, ...}
    images_meta = meta.get("Images", {}) if isinstance(meta, dict) else {}
    main_images_list = get_main_images(sku)  # Get from Images.main_images structure
    ebay_images = meta.get("Ebay_Images", []) if isinstance(meta, dict) else []

    merged = []
    for fn in files:
        info = images_meta.get(fn, {}) if isinstance(images_meta, dict) else {}
        # Get classification from JSON structure (phone/stock/enhanced categories)
        classification = get_image_classification(sku, fn)
        merged.append(
            {
                "filename": fn,
                "classification": classification,
                "is_main": fn in main_images_list,
                "is_ebay": fn in ebay_images,
                "meta": info,
                "thumb_url": f"/api/images/{sku}/{fn}?variant=thumb_256",
                "preview_url": f"/api/images/{sku}/{fn}?variant=thumb_512",
                "original_url": f"/api/images/{sku}/{fn}?variant=original",
                "source": info.get("source"),
            }
        )

    return {
        "sku": sku,
        "folder_found": bool(sku_dir),
        "count": len(files),
        "main_images": main_images_list,
        "ebay_images": ebay_images,
        "images": merged,
    }

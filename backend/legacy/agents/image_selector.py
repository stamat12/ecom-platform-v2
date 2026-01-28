"""Select main images for products and update JSON metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import sys

# Resolve project root and import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402


def load_product_detail(sku: str) -> dict:
    """Lightweight product loader to avoid GUI dependency."""
    path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(sku, {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def select_main_images_core(image_paths: List[str]) -> Tuple[int, List[str], List[str]]:
    """
    Add selected images to 'main_images' array in SKU JSON.
    
    Args:
        image_paths: List of absolute image file paths
    
    Returns:
        (processed_count, updated_skus, errors)
    """
    if not image_paths:
        return 0, [], []

    # Group images by SKU
    sku_images: Dict[str, List[Path]] = {}
    for img_path_str in image_paths:
        img_path = Path(img_path_str)
        sku = img_path.parent.name
        sku_images.setdefault(sku, []).append(img_path)

    updated_skus: List[str] = []
    errors: List[str] = []
    processed = 0

    for sku, images in sku_images.items():
        try:
            product_detail = load_product_detail(sku) or {}
            images_section = product_detail.get("Images", {})
            if not isinstance(images_section, dict):
                images_section = {}

            # Get existing main_images or initialize
            main_images = list(images_section.get("main_images", []) or [])

            # Add new images (avoid duplicates)
            existing_filenames = {entry.get("filename") for entry in main_images if isinstance(entry, dict)}
            
            for img_path in images:
                filename = img_path.name
                if filename not in existing_filenames:
                    main_images.append({"filename": filename})
                    existing_filenames.add(filename)
                    processed += 1

            # Update Images section
            images_section["main_images"] = main_images
            
            # Update summary counts if schema_version exists
            if "schema_version" in images_section and "summary" in images_section:
                images_section["summary"]["has_main_images"] = bool(main_images)
                images_section["summary"]["count_main_images"] = len(main_images)

            product_detail["Images"] = images_section

            # Save JSON
            product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
            product_path.parent.mkdir(parents=True, exist_ok=True)
            with product_path.open("w", encoding="utf-8") as f:
                json.dump({sku: product_detail}, f, ensure_ascii=False, indent=2)

            updated_skus.append(sku)

        except Exception as ex:
            errors.append(f"{sku}: {ex}")

    return processed, updated_skus, errors

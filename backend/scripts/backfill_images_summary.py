#!/usr/bin/env python
"""Backfill Images schema_version/summary/main_images metadata in product JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _safe_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict) and item.get("filename"):
            out.append(item)
    return out


def _normalized_images_section(images: Any) -> Dict[str, Any]:
    section = images if isinstance(images, dict) else {}
    stock = _safe_list(section.get("stock"))
    phone = _safe_list(section.get("phone"))
    enhanced = _safe_list(section.get("enhanced"))
    main_images = _safe_list(section.get("main_images"))

    return {
        "schema_version": "1.0",
        "summary": {
            "has_stock": bool(stock),
            "has_phone": bool(phone),
            "has_enhanced": bool(enhanced),
            "count_stock": len(stock),
            "count_phone": len(phone),
            "count_enhanced": len(enhanced),
            "has_main_images": bool(main_images),
            "count_main_images": len(main_images),
        },
        "stock": stock,
        "phone": phone,
        "enhanced": enhanced,
        "main_images": main_images,
    }


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    products_dir = backend_dir / "legacy" / "products"

    files = sorted(products_dir.glob("*.json"))
    scanned = 0
    updated = 0
    skipped = 0
    errors = 0

    for file_path in files:
        scanned += 1
        try:
            with file_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)

            if not isinstance(payload, dict) or len(payload) != 1:
                skipped += 1
                continue

            sku = next(iter(payload.keys()))
            product = payload.get(sku)
            if not isinstance(product, dict):
                skipped += 1
                continue

            old_images = product.get("Images")
            if not isinstance(old_images, dict):
                skipped += 1
                continue

            new_images = _normalized_images_section(old_images)
            if old_images == new_images:
                skipped += 1
                continue

            product["Images"] = new_images

            tmp_path = file_path.with_suffix(".tmp.json")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp_path.replace(file_path)
            updated += 1
        except Exception as e:
            errors += 1
            print(f"[WARN] Failed {file_path.name}: {e}")

    print("=== Images Summary Backfill ===")
    print(f"Scanned: {scanned}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

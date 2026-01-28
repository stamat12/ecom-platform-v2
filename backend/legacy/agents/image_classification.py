"""Image classification helpers for Product Manager UI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import config
from data_manager import load_all_products


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

def build_images_summary(stock: List[dict], phone: List[dict], enhanced: Optional[List[dict]] = None) -> dict:
    if enhanced is None:
        enhanced = []
    return {
        "schema_version": "1.0",
        "summary": {
            "has_stock": bool(stock),
            "has_phone": bool(phone),
            "has_enhanced": bool(enhanced),
            "count_stock": len(stock),
            "count_phone": len(phone),
            "count_enhanced": len(enhanced),
        },
        "stock": stock,
        "phone": phone,
        "enhanced": enhanced,
    }


def get_image_classification(sku: str, image_filename: str) -> Optional[str]:
    """Return classification type for an image, if present."""
    try:
        product_detail = load_product_detail(sku)
        if not product_detail:
            return None
        images_section = product_detail.get("Images", {})
        if not isinstance(images_section, dict):
            return None
        for category in ["phone", "stock", "enhanced"]:
            images_list = images_section.get(category, []) or []
            for img_record in images_list:
                if img_record.get("filename") == image_filename or img_record.get("file") == image_filename:
                    return category
        return None
    except Exception:
        return None


def classify_images_core(image_paths: List[str], classification_type: str) -> Tuple[int, List[str], List[str]]:
    """Classify images; returns (processed_count, updated_skus, errors)."""
    if not image_paths:
        return 0, [], []

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

            stock = list(images_section.get("stock", []) or [])
            phone = list(images_section.get("phone", []) or [])
            enhanced = list(images_section.get("enhanced", []) or [])

            for img_path in images:
                record = {"filename": img_path.name}
                if classification_type == "phone":
                    phone.append(record)
                elif classification_type == "stock":
                    stock.append(record)
                elif classification_type == "enhanced":
                    enhanced.append(record)

            product_detail["Images"] = build_images_summary(stock, phone, enhanced)
            product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
            product_path.parent.mkdir(parents=True, exist_ok=True)
            with product_path.open("w", encoding="utf-8") as f:
                json.dump({sku: product_detail}, f, ensure_ascii=False, indent=2)

            updated_skus.append(sku)
            processed += len(images)
        except Exception as ex:
            errors.append(f"{sku}: {ex}")

    return processed, updated_skus, errors


def remove_image_refs_from_json(filenames: List[str]) -> Tuple[int, int, List[str]]:
    """Remove image references from all SKU JSONs. Returns (removed_count, updated_skus, errors)."""
    if not filenames:
        return 0, 0, []
    products = load_all_products()
    skus = [p.get("SKU") for p in products if p.get("SKU")]
    removed_total = 0
    updated_skus = 0
    errors: List[str] = []

    for sku in skus:
        try:
            product_detail = load_product_detail(sku)
            images_section = product_detail.get("Images", {}) or {}
            stock = list(images_section.get("stock", []) or [])
            phone = list(images_section.get("phone", []) or [])
            enhanced = list(images_section.get("enhanced", []) or [])

            before = len(stock) + len(phone) + len(enhanced)
            stock = [r for r in stock if r.get("filename") not in filenames and r.get("file") not in filenames]
            phone = [r for r in phone if r.get("filename") not in filenames and r.get("file") not in filenames]
            enhanced = [r for r in enhanced if r.get("filename") not in filenames and r.get("file") not in filenames]
            after = len(stock) + len(phone) + len(enhanced)

            if before != after:
                product_detail["Images"] = build_images_summary(stock, phone, enhanced)
                product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
                product_path.parent.mkdir(parents=True, exist_ok=True)
                with product_path.open("w", encoding="utf-8") as f:
                    json.dump({sku: product_detail}, f, ensure_ascii=False, indent=2)
                updated_skus += 1
                removed_total += before - after
        except Exception as ex:
            errors.append(f"{sku}: {ex}")

    return removed_total, updated_skus, errors


def _set_contains_ean_for_sku(
    sku: str, target_filenames: Set[str], value: bool
) -> Tuple[int, Optional[dict]]:
    """Internal: set/unset contains_ean flag for matching filenames in any category.

    Returns: (changed_count, updated_product_detail or None if no change)
    """
    product_detail = load_product_detail(sku) or {}
    images_section = product_detail.get("Images", {}) or {}

    stock = list(images_section.get("stock", []) or [])
    phone = list(images_section.get("phone", []) or [])
    enhanced = list(images_section.get("enhanced", []) or [])

    changed = 0

    def mutate_list(lst: List[dict]) -> List[dict]:
        nonlocal changed
        new_list: List[dict] = []
        for entry in lst:
            if isinstance(entry, dict):
                fname = entry.get("filename") or entry.get("file")
                if fname and fname in target_filenames:
                    if value:
                        # set true
                        if not entry.get("contains_ean", False):
                            entry["contains_ean"] = True
                            changed += 1
                    else:
                        # unset (remove key for cleanliness)
                        if entry.get("contains_ean", False):
                            entry.pop("contains_ean", None)
                            changed += 1
                new_list.append(entry)
            else:
                # legacy string entry
                try:
                    fname = Path(str(entry)).name
                except Exception:
                    fname = str(entry)
                if fname in target_filenames:
                    # upgrade to dict with contains_ean flag
                    new_list.append({"filename": fname, "contains_ean": bool(value)})
                    changed += 1
                else:
                    new_list.append(entry)
        return new_list

    stock = mutate_list(stock)
    phone = mutate_list(phone)
    enhanced = mutate_list(enhanced)

    if changed:
        product_detail["Images"] = build_images_summary(stock, phone, enhanced)
        return changed, product_detail
    return 0, None


def set_contains_ean_flag(
    image_paths: List[str], value: bool
) -> Tuple[int, List[str], List[str]]:
    """Public API: set/unset per-image "contains_ean" flag.

    Args:
        image_paths: list of absolute or relative image file paths
        value: True to mark, False to unmark

    Returns:
        (changed_count, updated_skus, errors)
    """
    if not image_paths:
        return 0, [], []

    # Group by SKU -> filenames
    sku_to_filenames: Dict[str, Set[str]] = {}
    for p in image_paths:
        try:
            path_obj = Path(p)
            sku = path_obj.parent.name
            fname = path_obj.name
            sku_to_filenames.setdefault(sku, set()).add(fname)
        except Exception:
            continue

    total_changed = 0
    updated_skus: List[str] = []
    errors: List[str] = []

    for sku, filenames in sku_to_filenames.items():
        try:
            changed, updated_detail = _set_contains_ean_for_sku(sku, filenames, value)
            if changed and updated_detail is not None:
                product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
                product_path.parent.mkdir(parents=True, exist_ok=True)
                with product_path.open("w", encoding="utf-8") as f:
                    json.dump({sku: updated_detail}, f, ensure_ascii=False, indent=2)
                total_changed += changed
                updated_skus.append(sku)
        except Exception as ex:
            errors.append(f"{sku}: {ex}")

    return total_changed, updated_skus, errors


def mark_contains_ean(image_paths: List[str]) -> Tuple[int, List[str], List[str]]:
    """Convenience: mark selected images as contains_ean=True."""
    return set_contains_ean_flag(image_paths, True)


def unmark_contains_ean(image_paths: List[str]) -> Tuple[int, List[str], List[str]]:
    """Convenience: unmark selected images (remove contains_ean)."""
    return set_contains_ean_flag(image_paths, False)

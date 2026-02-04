from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.folder_images_cache import get_folder_image_count
from app.services.excel_inventory import excel_inventory, _get_db_path
from app.services.inventory_json_importer import (
    _load_json_products,
    _normalize_for_compare,
    JSON_COLUMN,
    IMAGES_COLUMN,
    FOLDER_IMAGES_COLUMN,
    IMAGE_COUNT_SOURCES,
)

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
import sys
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _get_inventory_columns(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute("PRAGMA table_info(inventory)").fetchall()
    return [r[1] for r in rows]


def update_db_from_jsons(
    skus: Optional[List[str]] = None,
    append_missing: bool = False,
) -> Dict[str, Any]:
    products_dir = Path(getattr(config, "PRODUCTS_FOLDER_PATH"))
    if not products_dir.exists():
        return {"success": False, "message": f"Products directory not found: {products_dir}"}

    incoming = _load_json_products(products_dir, skus=skus)
    if not incoming:
        return {"success": False, "message": "No product JSON files found to import."}

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = _get_inventory_columns(conn)
        sku_col = getattr(config, "SKU_COLUMN")
        if sku_col not in columns:
            return {"success": False, "message": f"SKU column not found in DB: {sku_col}"}

        sample = next(iter(incoming.values()))
        update_cols = set(sample.keys())
        update_cols.update([JSON_COLUMN, IMAGES_COLUMN, FOLDER_IMAGES_COLUMN])
        for _, col_name in IMAGE_COUNT_SOURCES:
            update_cols.add(col_name)

        update_cols = [c for c in update_cols if c in columns and c != sku_col]

        processed = 0
        updated = 0
        appended = 0

        for sku, flat in incoming.items():
            updates: Dict[str, Any] = {c: flat.get(c, None) for c in update_cols if c in flat}
            if JSON_COLUMN in columns:
                updates[JSON_COLUMN] = "Yes"

            folder_count = get_folder_image_count(sku)
            if folder_count is not None:
                if FOLDER_IMAGES_COLUMN in columns:
                    updates[FOLDER_IMAGES_COLUMN] = int(folder_count)
                if IMAGES_COLUMN in columns:
                    updates[IMAGES_COLUMN] = int(folder_count)

            if not updates:
                continue

            row = conn.execute(
                f"SELECT * FROM inventory WHERE \"{sku_col}\" = ?",
                (sku,),
            ).fetchone()

            if row is None:
                if not append_missing:
                    continue
                insert_cols = [sku_col] + list(updates.keys())
                placeholders = ",".join(["?"] * len(insert_cols))
                col_list = ", ".join([f"\"{c}\"" for c in insert_cols])
                values = [sku] + [updates[c] for c in updates]
                conn.execute(
                    f"INSERT INTO inventory ({col_list}) VALUES ({placeholders})",
                    values,
                )
                appended += 1
                processed += 1
                continue

            changed: Dict[str, Any] = {}
            for col, val in updates.items():
                old = row[col] if col in row.keys() else None
                # Skip Status updates if current value in DB is already "OK"
                if col == "Status" and old == "OK":
                    continue
                if _normalize_for_compare(old) != _normalize_for_compare(val):
                    changed[col] = val

            if changed:
                set_clause = ", ".join([f"\"{col}\" = ?" for col in changed.keys()])
                conn.execute(
                    f"UPDATE inventory SET {set_clause} WHERE \"{sku_col}\" = ?",
                    list(changed.values()) + [sku],
                )
                updated += 1

            processed += 1

        conn.commit()
    finally:
        conn.close()

    if updated or appended:
        excel_inventory.invalidate()

    return {
        "success": True,
        "processed": processed,
        "updated": updated,
        "appended": appended,
        "message": f"Processed {processed} SKUs | Updated {updated} | Appended {appended}",
    }

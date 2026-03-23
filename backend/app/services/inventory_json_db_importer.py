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


def _coerce_to_float_2digits(value: Any) -> Optional[float]:
    """Convert any value to float with 2 decimal places.
    
    Handles:
    - None / NaN -> None
    - Strings with comma decimal separator (e.g., "12,34" -> 12.34)
    - Strings with dot decimal separator (e.g., "12.34" -> 12.34)
    - floats and ints
    
    Returns rounded to 2 decimal places or None if conversion fails.
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        # Replace comma with dot for parsing (handle European format)
        normalized = stripped.replace(",", ".")
        try:
            result = float(normalized)
            return round(result, 2)
        except (ValueError, TypeError):
            return None
    
    try:
        result = float(value)
        return round(result, 2)
    except (ValueError, TypeError):
        return None


def _calculate_total_cost_net(price_net: Any, shipping_net: Any, sku: str = None) -> Optional[float]:
    """Calculate Total Cost Net = Price Net + Shipping Net.
    
    Both values are coerced to float with 2 decimal places.
    If either is None, returns None and logs a warning.
    
    Args:
        price_net: Value from Price Net column
        shipping_net: Value from Shipping Net column
        sku: Optional SKU for logging
    
    Returns:
        Rounded to 2 decimal places or None if either input is None
    """
    price_net_float = _coerce_to_float_2digits(price_net)
    shipping_net_float = _coerce_to_float_2digits(shipping_net)
    
    if price_net_float is None or shipping_net_float is None:
        sku_str = f" [{sku}]" if sku else ""
        print(
            f"[WARNING] Cannot calculate Total Cost Net{sku_str}: "
            f"Price Net={price_net!r}, Shipping Net={shipping_net!r}"
        )
        return None
    
    total = price_net_float + shipping_net_float
    return round(total, 2)



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
            
            # Coerce financial columns to float with 2 decimal places
            price_net_col = getattr(config, "PRICE_NET_COLUMN", "Price Net")
            shipping_net_col = getattr(config, "SHIPPING_NET_COLUMN", "Shipping Net")
            total_cost_net_col = getattr(config, "TOTAL_COST_NET_COLUMN", "Total Cost Net")
            op_col = getattr(config, "OP_COLUMN", "OP")
            
            if price_net_col in updates:
                updates[price_net_col] = _coerce_to_float_2digits(updates[price_net_col])
            if shipping_net_col in updates:
                updates[shipping_net_col] = _coerce_to_float_2digits(updates[shipping_net_col])
            if op_col in updates:
                updates[op_col] = _coerce_to_float_2digits(updates[op_col])
            
            # Calculate Total Cost Net if Price Net & Shipping Net are available
            if total_cost_net_col in columns:
                price_net_val = updates.get(price_net_col)
                shipping_net_val = updates.get(shipping_net_col)
                
                if price_net_val is None or shipping_net_val is None:
                    # Try to get from existing row if not in updates
                    row_check = conn.execute(
                        f"SELECT \"{price_net_col}\", \"{shipping_net_col}\" FROM inventory WHERE \"{sku_col}\" = ?",
                        (sku,),
                    ).fetchone()
                    
                    if row_check:
                        if price_net_val is None:
                            price_net_val = row_check[price_net_col]
                        if shipping_net_val is None:
                            shipping_net_val = row_check[shipping_net_col]
                
                if price_net_val is not None and shipping_net_val is not None:
                    calculated_total = _calculate_total_cost_net(
                        price_net_val, shipping_net_val, sku=sku
                    )
                    if calculated_total is not None:
                        updates[total_cost_net_col] = calculated_total

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

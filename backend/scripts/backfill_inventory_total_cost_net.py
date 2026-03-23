#!/usr/bin/env python
"""Backfill Total Cost Net in inventory.db using Price Net + Shipping Net.

This script calculates Total Cost Net = Price Net + Shipping Net for all inventory records
where Price Net and Shipping Net are available. It handles both missing and existing Total Cost Net values.

Additionally, with --normalize-all flag, it ensures all 3 columns are rounded to 2 decimal places.

Usage:
  python backend/scripts/backfill_inventory_total_cost_net.py
  python backend/scripts/backfill_inventory_total_cost_net.py --dry-run
  python backend/scripts/backfill_inventory_total_cost_net.py --force  # recalculate all
  python backend/scripts/backfill_inventory_total_cost_net.py --normalize-all  # normalize all 3 columns to 2 decimals
  python backend/scripts/backfill_inventory_total_cost_net.py --normalize-all --dry-run  # preview normalization
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Optional

# Add backend directory to path so we can import app module
BACKEND = Path(__file__).resolve().parents[1]
LEGACY = BACKEND / "legacy"
import sys
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(LEGACY))

import config  # type: ignore
from app.services.excel_inventory import _get_db_path


def _coerce_to_float_2digits(value) -> Optional[float]:
    """Convert value to float with 2 decimal places."""
    if value is None:
        return None
    
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing DB")
    parser.add_argument("--force", action="store_true", help="Recalculate Total Cost Net even if already set")
    parser.add_argument("--normalize-all", action="store_true", help="Also normalize Price Net and Shipping Net to 2 decimal places")
    args = parser.parse_args()

    price_net_col = getattr(config, "PRICE_NET_COLUMN", "Price Net")
    shipping_net_col = getattr(config, "SHIPPING_NET_COLUMN", "Shipping Net")
    total_cost_net_col = getattr(config, "TOTAL_COST_NET_COLUMN", "Total Cost Net")
    sku_col = getattr(config, "SKU_COLUMN", "SKU (Old)")

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Verify columns exist
        columns = conn.execute("PRAGMA table_info(inventory)").fetchall()
        col_names = {r[1] for r in columns}
        
        if price_net_col not in col_names:
            print(f"ERROR: {price_net_col} column not found in inventory table")
            return 1
        if shipping_net_col not in col_names:
            print(f"ERROR: {shipping_net_col} column not found in inventory table")
            return 1
        if total_cost_net_col not in col_names:
            print(f"ERROR: {total_cost_net_col} column not found in inventory table")
            return 1
        
        # Query all rows for processing
        rows = conn.execute(
            f'SELECT "{sku_col}", "{price_net_col}", "{shipping_net_col}", "{total_cost_net_col}" FROM inventory'
        ).fetchall()

        if not rows:
            print(f"[INFO] No rows found in inventory")
            return 0

        print(f"[INFO] Found {len(rows)} rows to process")
        if args.normalize_all:
            print(f"[INFO] Will normalize all 3 columns to 2 decimal places")

        updated = 0
        skipped = 0
        updated_skus = []

        for row in rows:
            sku = row[sku_col]
            price_net = row[price_net_col]
            shipping_net = row[shipping_net_col]
            current_total = row[total_cost_net_col]

            # Coerce current values
            price_net_float = _coerce_to_float_2digits(price_net)
            shipping_net_float = _coerce_to_float_2digits(shipping_net)

            # Check if any value needs updating
            should_update = False
            updates = {}

            # Check if we need to recalculate/normalize Total Cost Net
            if price_net_float is not None and shipping_net_float is not None:
                calculated_total = round(price_net_float + shipping_net_float, 2)
                
                # Check if Total Cost Net needs update
                if current_total is None or args.force:
                    should_update = True
                    updates[total_cost_net_col] = calculated_total
                    print(f"UPDATE {sku}: {total_cost_net_col} = {price_net_float} + {shipping_net_float} = {calculated_total}")
                else:
                    current_total_float = _coerce_to_float_2digits(current_total)
                    if current_total_float != calculated_total:
                        should_update = True
                        updates[total_cost_net_col] = calculated_total
                        print(f"UPDATE {sku}: {total_cost_net_col} {current_total} -> {calculated_total}")
            
            # Normalize Price Net and Shipping Net if --normalize-all flag is set
            if args.normalize_all:
                if price_net is not None and price_net_float is not None:
                    # Check if value needs normalization (changed after rounding)
                    try:
                        if isinstance(price_net, str):
                            # String value - needs normalization if it has comma or wrong format
                            if "," in str(price_net) or float(price_net) != price_net_float:
                                should_update = True
                                updates[price_net_col] = price_net_float
                                print(f"  NORMALIZE {sku}: {price_net_col} {price_net!r} -> {price_net_float}")
                        elif isinstance(price_net, float):
                            # Float value - normalize if it has more than 2 decimal places
                            if round(price_net, 2) != price_net:
                                should_update = True
                                updates[price_net_col] = price_net_float
                                print(f"  NORMALIZE {sku}: {price_net_col} {price_net} -> {price_net_float}")
                    except (ValueError, TypeError):
                        pass
                
                if shipping_net is not None and shipping_net_float is not None:
                    # Check if value needs normalization (changed after rounding)
                    try:
                        if isinstance(shipping_net, str):
                            # String value - needs normalization if it has comma or wrong format
                            if "," in str(shipping_net) or float(shipping_net.replace(",", ".")) != shipping_net_float:
                                should_update = True
                                updates[shipping_net_col] = shipping_net_float
                                print(f"  NORMALIZE {sku}: {shipping_net_col} {shipping_net!r} -> {shipping_net_float}")
                        elif isinstance(shipping_net, float):
                            # Float value - normalize if it has more than 2 decimal places
                            if round(shipping_net, 2) != shipping_net:
                                should_update = True
                                updates[shipping_net_col] = shipping_net_float
                                print(f"  NORMALIZE {sku}: {shipping_net_col} {shipping_net} -> {shipping_net_float}")
                    except (ValueError, TypeError):
                        pass

            # Normalize Total Cost Net itself if --normalize-all flag is set
            if args.normalize_all and total_cost_net_col in updates:
                # Total Cost Net already normalized through calculation above
                pass
            elif args.normalize_all and current_total is not None:
                # Normalize existing Total Cost Net value even if not recalculating
                current_total_float = _coerce_to_float_2digits(current_total)
                if current_total_float is not None:
                    try:
                        if isinstance(current_total, str):
                            if "," in str(current_total) or float(current_total.replace(",", ".")) != current_total_float:
                                should_update = True
                                updates[total_cost_net_col] = current_total_float
                                print(f"  NORMALIZE {sku}: {total_cost_net_col} {current_total!r} -> {current_total_float}")
                        elif isinstance(current_total, float):
                            if round(current_total, 2) != current_total:
                                should_update = True
                                updates[total_cost_net_col] = current_total_float
                                print(f"  NORMALIZE {sku}: {total_cost_net_col} {current_total} -> {current_total_float}")
                    except (ValueError, TypeError):
                        pass

            if not should_update:
                skipped += 1
                continue

            updated_skus.append(sku)

            if not args.dry_run and updates:
                set_clause = ", ".join([f'"{col}" = ?' for col in updates.keys()])
                conn.execute(
                    f'UPDATE inventory SET {set_clause} WHERE "{sku_col}" = ?',
                    list(updates.values()) + [sku]
                )
            updated += 1

        if args.dry_run:
            print(f"\n[DRY-RUN] Would update {updated} rows, skip {skipped} rows")
        else:
            conn.commit()
            print(f"\n[SUCCESS] Updated {updated} rows, skipped {skipped} rows")

        return 0

    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    exit(main())

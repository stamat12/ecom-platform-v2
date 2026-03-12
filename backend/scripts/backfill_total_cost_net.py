#!/usr/bin/env python
"""Backfill null Total Cost Net in product JSON files using Price Net + Shipping Net.

Usage:
  python backend/scripts/backfill_total_cost_net.py
  python backend/scripts/backfill_total_cost_net.py --dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        value = stripped.replace(",", ".")
    try:
        number = float(value)
        if number != number:
            return None
        return number
    except Exception:
        return None


def _iter_product_entries(payload: Any):
    if not isinstance(payload, dict):
        return
    for sku, product_data in payload.items():
        if isinstance(product_data, dict):
            yield sku, product_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    products_dir = backend_dir / "legacy" / "products"

    if not products_dir.exists():
        print(f"Products directory not found: {products_dir}")
        return 1

    updated_files = 0
    updated_products = 0
    skipped_products = 0

    for product_file in sorted(products_dir.glob("*.json")):
        try:
            payload = json.loads(product_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"ERROR reading {product_file.name}: {exc}")
            skipped_products += 1
            continue

        file_changed = False

        for sku, product_data in _iter_product_entries(payload):
            price_data = product_data.get("Price Data")
            if not isinstance(price_data, dict):
                continue

            if price_data.get("Total Cost Net") is not None:
                continue

            price_net = _coerce_float(price_data.get("Price Net"))
            shipping_net = _coerce_float(price_data.get("Shipping Net"))

            if price_net is None or shipping_net is None:
                print(
                    f"SKIP {product_file.name} [{sku}]: cannot calculate Total Cost Net from "
                    f"Price Net={price_data.get('Price Net')!r}, Shipping Net={price_data.get('Shipping Net')!r}"
                )
                skipped_products += 1
                continue

            total_cost_net = round(price_net + shipping_net, 2)
            price_data["Total Cost Net"] = total_cost_net
            file_changed = True
            updated_products += 1
            print(f"FIX {product_file.name} [{sku}]: Total Cost Net -> {total_cost_net}")

        if file_changed:
            updated_files += 1
            if not args.dry_run:
                product_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

    mode = "DRY RUN" if args.dry_run else "DONE"
    print(
        f"{mode}: updated {updated_products} products across {updated_files} files; "
        f"skipped {skipped_products} products"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python
"""
One-time backfill: copy fees from schemas/category_mapping.json into cached schema files
(EbayCat_<category_id>_EBAY_DE.json) when metadata fees are missing/empty.

Usage:
  python backend/scripts/backfill_schema_fees_from_mapping.py
  python backend/scripts/backfill_schema_fees_from_mapping.py --overwrite
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        numeric = float(value)
        if numeric != numeric:  # NaN check
            return None
        return numeric
    except Exception:
        return None


def _normalize_mapping_fees(raw_fees: Dict[str, Any]) -> Dict[str, float]:
    fees = raw_fees if isinstance(raw_fees, dict) else {}
    payment_fee = _coerce_float(fees.get("payment_fee"))
    commission = _coerce_float(fees.get("sales_commission_up_to"))
    if commission is None:
        commission = _coerce_float(fees.get("sales_commission_percentage"))

    normalized: Dict[str, float] = {}
    if payment_fee is not None:
        normalized["payment_fee"] = payment_fee
    if commission is not None:
        normalized["sales_commission_percentage"] = commission
    return normalized


def _has_effective_fees(fees: Any) -> bool:
    if not isinstance(fees, dict):
        return False
    return (
        _coerce_float(fees.get("payment_fee")) is not None
        or _coerce_float(fees.get("sales_commission_percentage")) is not None
    )


def _merge_missing_fee_fields(current_fees: Any, mapping_fees: Dict[str, float]) -> Dict[str, Any]:
    current = current_fees if isinstance(current_fees, dict) else {}
    merged = dict(current)

    if _coerce_float(merged.get("payment_fee")) is None and _coerce_float(mapping_fees.get("payment_fee")) is not None:
        merged["payment_fee"] = float(mapping_fees["payment_fee"])

    if _coerce_float(merged.get("sales_commission_percentage")) is None and _coerce_float(mapping_fees.get("sales_commission_percentage")) is not None:
        merged["sales_commission_percentage"] = float(mapping_fees["sales_commission_percentage"])

    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Also overwrite non-empty schema fees")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    schemas_dir = backend_dir / "schemas"
    mapping_path = schemas_dir / "category_mapping.json"

    if not mapping_path.exists():
        print(f"[ERROR] Mapping file not found: {mapping_path}")
        return 1

    with mapping_path.open("r", encoding="utf-8") as f:
        mapping_data = json.load(f)

    mapping_lookup: Dict[str, Dict[str, float]] = {}
    for row in mapping_data.get("categoryMappings", []):
        category_id = str((row or {}).get("categoryId") or "").strip()
        if not category_id:
            continue
        normalized = _normalize_mapping_fees((row or {}).get("fees", {}))
        if normalized:
            mapping_lookup[category_id] = normalized

    schema_files = sorted(schemas_dir.glob("EbayCat_*_EBAY_DE.json"))

    scanned = 0
    updated = 0
    skipped_has_fees = 0
    skipped_no_mapping_fees = 0
    parse_errors = 0

    for schema_file in schema_files:
        scanned += 1
        parts = schema_file.stem.split("_")
        if len(parts) < 2:
            parse_errors += 1
            continue
        category_id = parts[1]

        mapping_fees = mapping_lookup.get(category_id)
        if not mapping_fees:
            skipped_no_mapping_fees += 1
            continue

        try:
            with schema_file.open("r", encoding="utf-8") as f:
                schema_data = json.load(f)

            metadata = schema_data.setdefault("_metadata", {})
            current_fees = metadata.get("fees", {})

            if args.overwrite:
                metadata["fees"] = mapping_fees
            else:
                merged_fees = _merge_missing_fee_fields(current_fees, mapping_fees)
                if merged_fees == (current_fees if isinstance(current_fees, dict) else {}):
                    skipped_has_fees += 1
                    continue
                metadata["fees"] = merged_fees

            tmp_path = schema_file.with_suffix(".tmp.json")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(schema_data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(schema_file)
            updated += 1
        except Exception as e:
            parse_errors += 1
            print(f"[WARN] Failed to process {schema_file.name}: {e}")

    print("=== Schema Fee Backfill Summary ===")
    print(f"Scanned: {scanned}")
    print(f"Updated: {updated}")
    print(f"Skipped (already has fees): {skipped_has_fees}")
    print(f"Skipped (no mapping fees): {skipped_no_mapping_fees}")
    print(f"Errors: {parse_errors}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

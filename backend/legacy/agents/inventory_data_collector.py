"""Export inventory rows to per-SKU JSON files."""

import json
import sys
from pathlib import Path

import pandas as pd


# Resolve project root and import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402


# Columns organized by category for JSON export
CATEGORY_COLUMNS = {
    "Invoice Data": [
        config.BUYING_ENTITY_COLUMN,
        config.SUPPLIER_COLUMN,
        config.INVOICE_COLUMN,
        config.INVOICE_DATE_COLUMN,
    ],
    "Supplier Data": [
        config.SUPPLIER_NUMBER_COLUMN,
        config.ISIN_COLUMN,
        config.TITLE_COLUMN,
    ],
    "Price Data": [
        config.PRICE_NET_COLUMN,
        config.SHIPPING_NET_COLUMN,
        config.TOTAL_COST_NET_COLUMN,
    ],
    "Ebay Category": [
        config.CATEGORY_COLUMN,
    ],
    "EAN": [
        config.EAN_COLUMN,
    ],
    "Product Condition": [
        config.CONDITION_COLUMN,
    ],
    "Intern Product Info": [
        config.GENDER_COLUMN,
        config.BRAND_COLUMN,
        config.COLOR_COLUMN,
        config.SIZE_COLUMN,
    ],
    "Intern Generated Info": [
        config.MORE_DETAILS_COLUMN,
        config.KEYWORDS_COLUMN,
        config.MATERIALS_COLUMN,
    ],
    "OP": [
        config.OP_COLUMN,
    ],
    "Status": [
        config.STATUS_COLUMN,
    ],
    "Warehouse": [
        config.LAGER_COLUMN,
    ],
}


def get_important_fields() -> list[str]:
    """Return important fields in a stable order sourced from config."""
    return [
        config.BUYING_ENTITY_COLUMN,
        config.SUPPLIER_COLUMN,
        config.INVOICE_COLUMN,
        config.INVOICE_DATE_COLUMN,
        config.PRICE_NET_COLUMN,
        config.SHIPPING_NET_COLUMN,
        config.TOTAL_COST_NET_COLUMN,
        config.OP_COLUMN,
        config.SUPPLIER_NUMBER_COLUMN,
        config.ISIN_COLUMN,
        config.TITLE_COLUMN,
        config.CATEGORY_COLUMN,
        config.EAN_COLUMN,
        config.CONDITION_COLUMN,
        config.GENDER_COLUMN,
        config.BRAND_COLUMN,
        config.COLOR_COLUMN,
        config.SIZE_COLUMN,
        config.LAGER_COLUMN,
        config.MORE_DETAILS_COLUMN,
        config.KEYWORDS_COLUMN,
        config.MATERIALS_COLUMN,
    ]


def load_inventory_data() -> pd.DataFrame | None:
    """Load the inventory sheet; returns DataFrame or None on failure."""
    try:
        return pd.read_excel(config.INVENTORY_FILE_PATH, sheet_name=config.INVENTORY_SHEET_NAME)
    except Exception:
        return None


def get_missing_skus(all_skus: list[str], inventory_df: pd.DataFrame | None) -> list[str]:
    """Return SKUs not present in the inventory DataFrame."""
    if inventory_df is None or inventory_df.empty:
        return []
    try:
        sku_series = inventory_df[config.SKU_COLUMN].fillna("").astype(str)
        inventory_skus = set(sku_series.tolist())
        return sorted([sku for sku in all_skus if sku not in inventory_skus])
    except Exception:
        return []


def read_skus(sku_path: Path | None = None) -> list[str]:
    """Load SKUs from the first column of ``sku.xlsx``."""

    path = Path(sku_path) if sku_path else config.SKU_FILE_PATH
    df = pd.read_excel(path)
    print(f"SKU file columns: {df.columns.tolist()}")
    return df.iloc[:, 0].dropna().astype(str).tolist()


def load_inventory() -> pd.DataFrame:
    """Load the configured inventory sheet from the inventory workbook."""

    df = pd.read_excel(config.INVENTORY_FILE_PATH, sheet_name=config.INVENTORY_SHEET_NAME)
    print(f"Inventory columns: {df.columns.tolist()}")
    return df


def extract_category_id(category_path: str) -> str:
    """Extract category ID from eBay category path."""
    if not category_path:
        return ""
    # The last part of the path is usually the category ID
    parts = category_path.rstrip('/').split('/')
    if parts:
        last_part = parts[-1]
        # Check if it's numeric (category ID)
        if last_part.isdigit():
            return last_part
    return ""


def load_category_id_map() -> dict[str, str]:
    """Load mapping of category path/title to eBay category ID from the categories sheet."""
    try:
        df = pd.read_excel(config.INVENTORY_FILE_PATH, sheet_name=config.CATEGORY_SHEET_NAME)
    except Exception as exc:  # pragma: no cover - defensive log
        print(f"Failed to load categories sheet: {exc}")
        return {}

    title_col = config.CATEGORY_TITLE_COLUMN
    id_col = config.CATEGORY_ID_COLUMN

    if title_col not in df.columns or id_col not in df.columns:
        print("Categories sheet missing required columns; expected 'Category' and 'ID'")
        return {}

    mapping: dict[str, str] = {}
    for _, row in df[[title_col, id_col]].dropna(subset=[title_col, id_col]).iterrows():
        title = str(row[title_col]).strip()
        cat_id = str(row[id_col]).strip()
        if title and cat_id:
            mapping[title] = cat_id

    print(f"Loaded {len(mapping)} category IDs from categories sheet")
    return mapping


def export_sku_records(skus: list[str], inventory_df: pd.DataFrame) -> None:
    """Write one JSON file per SKU under ``products/`` organized by category."""

    products_dir = ROOT / "products"
    products_dir.mkdir(exist_ok=True)

    category_id_map = load_category_id_map()

    sku_series = inventory_df[config.SKU_COLUMN].fillna("").astype(str)

    for sku in skus:
        rows = inventory_df[sku_series == sku]
        if rows.empty:
            print(f"SKU not found in inventory: {sku}")
            continue

        # Sanitize values for JSON (convert timestamps and other non-serializable types)
        sanitized = rows.fillna("").apply(
            lambda col: col.map(
                lambda v: v.isoformat() if hasattr(v, "isoformat") 
                else round(v, 2) if isinstance(v, float) 
                else v
            )
        )

        # Extract first row (assuming one SKU per row)
        row_data = sanitized.iloc[0].to_dict()

        # Ensure OP is treated as float with 2 decimals
        try:
            op_key = config.OP_COLUMN
            if op_key in row_data:
                val = row_data[op_key]
                if val is not None and val != "":
                    row_data[op_key] = round(float(val), 2)
        except Exception:
            pass

        # Organize into categories
        payload = {sku: {}}
        for category, columns in CATEGORY_COLUMNS.items():
            category_data = {}
            for col in columns:
                if col in row_data:
                    category_data[col] = row_data[col]
            if category_data:
                payload[sku][category] = category_data
        
        # Add eBay Category ID if category path exists
        if "Ebay Category" in payload[sku]:
            category_path = payload[sku]["Ebay Category"].get(config.CATEGORY_COLUMN, "")
            if category_path:
                cat_id = extract_category_id(category_path)
                if not cat_id:
                    cat_id = category_id_map.get(category_path.strip(), "")
                if cat_id:
                    payload[sku]["Ebay Category"]["eBay Category ID"] = cat_id

        output_path = products_dir / f"{sku}.json"

        # Merge with existing JSON to preserve other sections (e.g., Images)
        to_write = payload
        if output_path.exists():
            try:
                with output_path.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing_data = existing.get(sku, {}) if isinstance(existing, dict) else {}
                merged = existing_data.copy()
                for cat, cat_data in payload.get(sku, {}).items():
                    merged[cat] = cat_data

                # Reorder categories: first follow CATEGORY_COLUMNS order, then others (e.g., Images)
                ordered: dict[str, dict] = {}
                desired_order = list(CATEGORY_COLUMNS.keys())
                for cat in desired_order:
                    if cat in merged:
                        ordered[cat] = merged[cat]
                # Append remaining categories preserving their existing order
                for cat in merged.keys():
                    if cat not in ordered:
                        ordered[cat] = merged[cat]

                to_write = {sku: ordered}
            except Exception:
                to_write = payload

        # Skip write only if identical INCLUDING ordering (compare JSON strings)
        try:
            if output_path.exists():
                with output_path.open("r", encoding="utf-8") as f:
                    current_text = f.read()
                new_text = json.dumps(to_write, ensure_ascii=False, indent=2)
                if current_text.strip() == new_text.strip():
                    print(f"No changes for {output_path.name}; skipped")
                    continue
        except Exception:
            pass

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(to_write, f, ensure_ascii=False, indent=2)

        print(f"Saved {output_path.name}")


def main() -> None:
    skus = read_skus()
    inventory_df = load_inventory()
    export_sku_records(skus, inventory_df)


if __name__ == "__main__":
    main()
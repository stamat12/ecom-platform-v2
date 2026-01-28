"""Fetch and cache eBay category schemas for unique categories from product JSON files."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv


# Resolve project root and import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

# Load environment variables from .env in project root
load_dotenv(ROOT / ".env")

# Global cache for eBay schemas
EBAY_SCHEMA_CACHE: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}


def load_category_mapping() -> dict:
    """Load category name to ID mapping from the categories sheet."""

    df = pd.read_excel(
        config.INVENTORY_FILE_PATH,
        sheet_name=config.CATEGORY_SHEET_NAME
    )
    mapping = dict(zip(df[config.CATEGORY_TITLE_COLUMN], df[config.CATEGORY_ID_COLUMN]))
    return mapping


def extract_unique_categories() -> set:
    """Extract unique eBay category names from all product JSON files."""

    products_dir = config.PRODUCTS_FOLDER_PATH
    categories = set()

    if not products_dir.exists():
        print(f"Products folder not found: {products_dir}")
        return categories

    for json_file in products_dir.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            for sku, sku_data in data.items():
                if isinstance(sku_data, dict) and "Ebay Category" in sku_data:
                    ebay_cat = sku_data["Ebay Category"]
                    if isinstance(ebay_cat, dict):
                        cat_name = ebay_cat.get(config.CATEGORY_COLUMN)
                        if cat_name:
                            categories.add(cat_name)
        except Exception as e:
            print(f"Error reading {json_file.name}: {e}")

    return categories


def map_categories_to_ids(category_mapping: dict, unique_categories: set) -> dict:
    """Map category names to their IDs."""

    result = {}
    for category in sorted(unique_categories):
        cat_id = category_mapping.get(category)
        if cat_id is not None:
            result[category] = cat_id
        else:
            print(f"ERROR: Category '{category}' not found in category mapping")

    return result


def fetch_ebay_fees(category_id: str, category_mapping: dict, inventory_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fetch fees from the eBay Categories sheet in the inventory file.
    Returns payment fee and sales commission percentage.
    """

    try:
        # Load the eBay Categories sheet
        categories_df = pd.read_excel(
            config.INVENTORY_FILE_PATH,
            sheet_name=config.CATEGORY_SHEET_NAME
        )

        # Find the row with matching category ID
        cat_row = categories_df[categories_df[config.CATEGORY_ID_COLUMN] == int(category_id)]

        if cat_row.empty:
            return {}

        # Extract fees
        fees_data = {}
        
        payment_fee = cat_row[config.PAYMENT_FEE_COLUMN].iloc[0]
        if pd.notna(payment_fee):
            fees_data["payment_fee"] = float(payment_fee)
        else:
            print(f"  WARNING: {config.PAYMENT_FEE_COLUMN} is empty for category {category_id}")

        commission = cat_row[config.SALES_COMMISSION_UP_TO_COLUMN].iloc[0]
        if pd.notna(commission):
            fees_data["sales_commission_percentage"] = float(commission)
        else:
            print(f"  WARNING: {config.SALES_COMMISSION_UP_TO_COLUMN} is empty for category {category_id}")

        return fees_data

    except KeyError as e:
        print(f"  ERROR: Missing column {e} in eBay Categories sheet")
        return {}
    except Exception as e:
        print(f"  Error fetching fees: {e}")
        return {}


def fetch_ebay_aspects(category_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch Required and Optional Item Specifics (Aspects) from the eBay API
    for a specific Category ID.

    Returns:
        {
            "required": [{ "name": "Brand", "values": ["Nike", "Adidas"] }, ...],
            "optional": [{ "name": "Color", "values": [...] }, ...]
        }
    """

    # Check cache
    if category_id in EBAY_SCHEMA_CACHE:
        return EBAY_SCHEMA_CACHE[category_id]

    print(f"  Fetching eBay schema for Category ID: {category_id}")

    # Check authentication
    access_token = os.getenv("EBAY_ACCESS_TOKEN")
    if not access_token:
        print("  ERROR: EBAY_ACCESS_TOKEN not found in .env file")
        return {"required": [], "optional": []}

    try:
        base_url = "https://api.ebay.com/commerce/taxonomy/v1"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        # Step A: Get the categoryTreeId for the marketplace
        tree_id_url = f"{base_url}/get_default_category_tree_id"
        tree_id_params = {"marketplace_id": config.MARKETPLACE_DE_ID}

        resp_tree = requests.get(tree_id_url, headers=headers, params=tree_id_params, timeout=30)
        resp_tree.raise_for_status()
        tree_id = resp_tree.json().get("categoryTreeId")

        if not tree_id:
            print(f"  ERROR: Could not find categoryTreeId for marketplace {config.MARKETPLACE_DE_ID}")
            return {"required": [], "optional": []}

        # Step B: Get the aspects (specifics) for the category ID
        aspects_url = f"{base_url}/category_tree/{tree_id}/get_item_aspects_for_category"
        aspects_params = {"category_id": category_id}

        response = requests.get(aspects_url, headers=headers, params=aspects_params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Step C: Parse the Response
        required_fields: List[Dict[str, Any]] = []
        optional_fields: List[Dict[str, Any]] = []

        aspects_list = data.get("aspects", [])
        if not aspects_list:
            print(f"  INFO: No item aspects found for Category ID {category_id}")
            return {"required": [], "optional": []}

        for aspect in aspects_list:
            name = aspect.get("localizedAspectName", "N/A")
            constraint = aspect.get("aspectConstraint", {})
            is_required = constraint.get("aspectRequired", False)

            # Extract suggested values
            allowed_values = []
            values_list = aspect.get("aspectValues", [])
            for val in values_list:
                value_text = val.get("localizedValue", None)
                if value_text:
                    allowed_values.append(value_text)

            field_data = {
                "name": name,
                "values": sorted(allowed_values),
            }

            if is_required:
                required_fields.append(field_data)
            else:
                optional_fields.append(field_data)

        result = {"required": required_fields, "optional": optional_fields}

        # Cache the result
        EBAY_SCHEMA_CACHE[category_id] = result
        return result

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        msg = e.response.text
        print(f"  HTTP Error {status}: {msg}")
        return {"required": [], "optional": []}

    except Exception as e:
        print(f"  Unexpected error: {e}")
        return {"required": [], "optional": []}


def schema_file_exists(category_id: str) -> bool:
    """Check if schema file already exists in the schemas folder."""

    schema_filename = f"EbayCat_{category_id}_{config.MARKETPLACE_DE_ID}.json"
    schema_path = config.SCHEMAS_FOLDER_PATH / schema_filename
    return schema_path.exists()


def save_schema(category_id: str, schema_data: Dict[str, Any], category_name: str = "", fees_data: Dict[str, Any] = None) -> None:
    """Save schema to the schemas folder with metadata including fees."""

    config.SCHEMAS_FOLDER_PATH.mkdir(exist_ok=True)

    schema_filename = f"EbayCat_{category_id}_{config.MARKETPLACE_DE_ID}.json"
    schema_path = config.SCHEMAS_FOLDER_PATH / schema_filename

    # Add metadata at the top
    payload = {
        "_metadata": {
            "category_name": category_name,
            "category_id": category_id,
            "marketplace": config.MARKETPLACE_DE_ID,
            "fees": fees_data if fees_data else {},
        },
        "schema": schema_data,
    }

    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  Saved schema: {schema_filename}")


def main() -> None:
    category_mapping = load_category_mapping()
    unique_categories = extract_unique_categories()

    category_ids = map_categories_to_ids(category_mapping, unique_categories)

    print(f"\nProcessing {len(category_ids)} unique categories for eBay schemas:")
    for category, cat_id in sorted(category_ids.items()):
        print(f"\nCategory: {category} (ID: {cat_id})")

        if schema_file_exists(cat_id):
            print(f"  Schema already exists; skipped")
            continue

        schema = fetch_ebay_aspects(cat_id)
        fees = fetch_ebay_fees(str(cat_id), category_mapping, None)

        if schema["required"] or schema["optional"]:
            save_schema(cat_id, schema, category_name=category, fees_data=fees)
        else:
            print(f"  No schema data retrieved")


if __name__ == "__main__":
    main()


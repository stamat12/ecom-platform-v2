"""
eBay category schema management service
"""
import os
import logging
from typing import Dict, Any, List, Optional
import requests
from pathlib import Path

from app.config.ebay_config import (
    get_taxonomy_endpoint,
    MARKETPLACE_ID,
    EBAY_SITE_ID
)
from app.repositories import ebay_schema_repo
from app.repositories.sku_json_repo import read_sku_json
from app.services.excel_inventory import load_inventory_dataframe

logger = logging.getLogger(__name__)

# Cache for eBay API responses
_ebay_api_cache: Dict[str, Any] = {}


def get_ebay_token() -> str:
    """Get eBay access token from environment"""
    token = os.getenv("EBAY_ACCESS_TOKEN")
    if not token:
        raise ValueError("EBAY_ACCESS_TOKEN not found in environment variables")
    return token


def fetch_category_tree_id() -> str:
    """
    Fetch the category tree ID for the marketplace
    
    Returns:
        Category tree ID (cached after first call)
    """
    cache_key = f"tree_id_{MARKETPLACE_ID}"
    
    if cache_key in _ebay_api_cache:
        return _ebay_api_cache[cache_key]
    
    try:
        base_url = get_taxonomy_endpoint()
        headers = {
            "Authorization": f"Bearer {get_ebay_token()}",
            "Accept": "application/json",
        }
        
        url = f"{base_url}/get_default_category_tree_id"
        params = {"marketplace_id": MARKETPLACE_ID}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        tree_id = response.json().get("categoryTreeId")
        if not tree_id:
            raise ValueError(f"Could not find categoryTreeId for marketplace {MARKETPLACE_ID}")
        
        _ebay_api_cache[cache_key] = tree_id
        logger.info(f"Fetched category tree ID: {tree_id}")
        return tree_id
        
    except requests.HTTPError as e:
        logger.error(f"eBay API error fetching tree ID: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error fetching category tree ID: {e}")
        raise


def fetch_ebay_aspects_from_api(category_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch required/optional item specifics from eBay Taxonomy API
    
    Args:
        category_id: eBay category ID
    
    Returns:
        Dict with 'required' and 'optional' lists of field specs
    """
    logger.info(f"Fetching eBay aspects for category {category_id}")
    
    try:
        tree_id = fetch_category_tree_id()
        base_url = get_taxonomy_endpoint()
        headers = {
            "Authorization": f"Bearer {get_ebay_token()}",
            "Accept": "application/json",
        }
        
        url = f"{base_url}/category_tree/{tree_id}/get_item_aspects_for_category"
        params = {"category_id": category_id}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse aspects
        required_fields: List[Dict[str, Any]] = []
        optional_fields: List[Dict[str, Any]] = []
        
        aspects_list = data.get("aspects", [])
        if not aspects_list:
            logger.warning(f"No aspects found for category {category_id}")
            return {"required": [], "optional": []}
        
        for aspect in aspects_list:
            name = aspect.get("localizedAspectName", "N/A")
            constraint = aspect.get("aspectConstraint", {})
            is_required = constraint.get("aspectRequired", False)
            
            # Extract allowed values
            allowed_values = []
            values_list = aspect.get("aspectValues", [])
            for val in values_list:
                value_text = val.get("localizedValue")
                if value_text:
                    allowed_values.append(value_text)
            
            field_data = {
                "name": name,
                "values": sorted(allowed_values) if allowed_values else None,
            }
            
            if is_required:
                required_fields.append(field_data)
            else:
                optional_fields.append(field_data)
        
        logger.info(f"Fetched {len(required_fields)} required and {len(optional_fields)} optional fields for category {category_id}")
        return {"required": required_fields, "optional": optional_fields}
        
    except requests.HTTPError as e:
        logger.error(f"eBay API error: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error fetching aspects for category {category_id}: {e}")
        raise


def get_category_fees(category_id: str) -> Dict[str, float]:
    """
    Get fees for category from inventory Excel file
    
    Args:
        category_id: eBay category ID
    
    Returns:
        Dict with payment_fee and sales_commission_percentage
    """
    try:
        df = load_inventory_dataframe()
        
        # Look for category in eBay Category ID column
        category_row = df[df["eBay Category ID"] == int(category_id)]
        
        if category_row.empty:
            logger.warning(f"Category {category_id} not found in inventory")
            return {}
        
        fees = {}
        
        # Extract fees if columns exist
        if "Payment Fee €" in df.columns:
            payment_fee = category_row["Payment Fee €"].iloc[0]
            if pd.notna(payment_fee):
                fees["payment_fee"] = float(payment_fee)
        
        if "Sales Commission % up to 7500€" in df.columns:
            commission = category_row["Sales Commission % up to 7500€"].iloc[0]
            if pd.notna(commission):
                fees["sales_commission_percentage"] = float(commission)
        
        return fees
        
    except Exception as e:
        logger.error(f"Error fetching fees for category {category_id}: {e}")
        return {}


def fetch_and_cache_schema(category_id: str, category_name: str = "") -> Dict[str, Any]:
    """
    Fetch schema from eBay API and save to cache
    
    Args:
        category_id: eBay category ID
        category_name: Category name (optional)
    
    Returns:
        Complete schema with metadata
    """
    # Fetch schema from API
    schema_data = fetch_ebay_aspects_from_api(category_id)
    
    # Fetch fees
    fees = get_category_fees(category_id)
    
    # Prepare metadata
    metadata = {
        "category_name": category_name,
        "category_id": category_id,
        "marketplace": MARKETPLACE_ID,
        "fees": fees
    }
    
    # Save to cache
    success = ebay_schema_repo.save_schema(category_id, schema_data, metadata)
    
    if not success:
        logger.warning(f"Failed to cache schema for category {category_id}")
    
    return {
        "_metadata": metadata,
        "schema": schema_data
    }


def get_schema(category_id: str, use_cache: bool = True, category_name: str = "") -> Dict[str, Any]:
    """
    Get schema for category (from cache or API)
    
    Args:
        category_id: eBay category ID
        use_cache: If True, use cached schema if available
        category_name: Category name for fetching new schema
    
    Returns:
        Schema dict with _metadata and schema keys
    """
    # Try cache first
    if use_cache:
        cached = ebay_schema_repo.get_schema(category_id)
        if cached:
            logger.debug(f"Using cached schema for category {category_id}")
            return cached
    
    # Fetch from API
    logger.info(f"Fetching fresh schema for category {category_id}")
    return fetch_and_cache_schema(category_id, category_name)


def get_schema_for_sku(sku: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Get schema for SKU's category
    
    Args:
        sku: Product SKU
        use_cache: If True, use cached schema
    
    Returns:
        Schema dict or None if SKU has no category
    """
    product_json = read_sku_json(sku)
    
    if not product_json:
        logger.warning(f"No product JSON found for SKU {sku}")
        return None
    
    # Extract category info
    ebay_cat = product_json.get("Ebay Category", {})
    category_id = ebay_cat.get("eBay Category ID")
    category_name = ebay_cat.get("Category", "")
    
    if not category_id:
        logger.warning(f"No eBay category ID found for SKU {sku}")
        return None
    
    return get_schema(str(category_id), use_cache, category_name)


def list_all_schemas() -> List[Dict[str, Any]]:
    """
    List all cached schemas
    
    Returns:
        List of schema summaries
    """
    category_ids = ebay_schema_repo.list_cached_schemas()
    
    schemas = []
    for cat_id in category_ids:
        metadata = ebay_schema_repo.get_schema_metadata(cat_id)
        if metadata:
            schemas.append({
                "category_id": cat_id,
                "category_name": metadata.get("category_name", ""),
                "has_fees": bool(metadata.get("fees")),
                "marketplace": metadata.get("marketplace", "")
            })
    
    return schemas


def refresh_schemas(category_ids: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
    """
    Refresh schemas (re-fetch from eBay API)
    
    Args:
        category_ids: List of category IDs to refresh (None = all cached)
        force: If True, refresh even if cached
    
    Returns:
        Dict with refresh results
    """
    if category_ids is None:
        category_ids = ebay_schema_repo.list_cached_schemas()
    
    results = {
        "refreshed": [],
        "failed": []
    }
    
    for cat_id in category_ids:
        try:
            # Get category name from existing schema
            metadata = ebay_schema_repo.get_schema_metadata(cat_id)
            category_name = metadata.get("category_name", "") if metadata else ""
            
            # Fetch fresh schema
            schema = fetch_and_cache_schema(cat_id, category_name)
            
            results["refreshed"].append({
                "category_id": cat_id,
                "category_name": category_name,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Failed to refresh schema for category {cat_id}: {e}")
            results["failed"].append({
                "category_id": cat_id,
                "error": str(e)
            })
    
    return results


# Import pandas at module level to avoid issues
import pandas as pd

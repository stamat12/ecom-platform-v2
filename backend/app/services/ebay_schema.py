"""
eBay category schema management service
"""
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
from app.services.ebay_oauth import get_access_token

logger = logging.getLogger(__name__)

# Cache for eBay API responses
_ebay_api_cache: Dict[str, Any] = {}


def get_ebay_token() -> str:
    """Get eBay access token from environment"""
    return get_access_token()


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
    Get schema for SKU's category (synchronous version)
    
    Args:
        sku: Product SKU
        use_cache: If True, use cached schema
    
    Returns:
        Schema dict or None if SKU has no category
    """
    try:
        logger.info(f"Getting schema for SKU: {sku} (use_cache={use_cache})")
        product_json = read_sku_json(sku)
        
        if not product_json:
            logger.warning(f"No product JSON found for SKU {sku}")
            return None
    except Exception as e:
        logger.error(f"Error reading product JSON for {sku}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    # Try to get category from multiple possible locations (same logic as /api/ebay/fields endpoint)
    category = None
    category_id = None
    
    # Try top-level category field
    if "category" in product_json:
        category = product_json.get("category")
    
    # Try from Ebay Category section
    if "Ebay Category" in product_json:
        ebay_cat = product_json.get("Ebay Category", {})
        if isinstance(ebay_cat, dict):
            if not category:
                category = ebay_cat.get("Category")
            # Prefer explicit category ID if present
            category_id = (
                ebay_cat.get("eBay Category ID")
                or ebay_cat.get("Category ID")
                or ebay_cat.get("CategoryId")
                or ebay_cat.get("category_id")
            )
    
    # Try from AI Product Details
    if not category and "AI Product Details" in product_json:
        ai_details = product_json.get("AI Product Details", {})
        if isinstance(ai_details, dict):
            category = ai_details.get("category")
    
    if not category and not category_id:
        logger.warning(f"No category found for SKU {sku}")
        return None
    
    if category_id:
        logger.info(f"Using category ID {category_id} from SKU {sku}")
    else:
        logger.info(f"Found category for SKU {sku}: {category}")

        # Look up category ID from mapping
        try:
            category_data = _get_category_id_from_mapping(category)

            if not category_data:
                logger.warning(f"Could not find category ID for: {category}")
                return None

            category_id = category_data.get("categoryId")
            logger.info(f"Found category ID {category_id} for SKU {sku}")
        except Exception as e:
            logger.error(f"Error looking up category ID for {sku}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    # Load schema from cache or fetch from API if missing
    try:
        schema_data = get_schema(category_id, use_cache=use_cache, category_name=str(category))
        if not schema_data:
            logger.warning(f"No schema available for category {category_id}")
            return None
        return schema_data
    except Exception as e:
        logger.error(f"Error loading schema for SKU {sku}: {e}")
        return None


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


async def get_schema_by_category_name(category_name: str) -> dict:
    """
    Fetch eBay schema by category name or full path.
    1. Checks for cached schema files
    2. Looks up category ID in category_mapping.json
    3. Fetches schema from eBay API if needed
    4. Caches the schema for future use
    
    Args:
        category_name: Category name or full path (e.g., "/Kleidung & Accessoires/Damen/.../BHs & BH-Sets")
    
    Returns:
        Dictionary with schema data or error message
    """
    try:
        # Get all available schemas
        schemas_dir = ebay_schema_repo.SCHEMAS_DIR
        if not schemas_dir.exists():
            schemas_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract simple category name from path if it's a full path
        simple_category = category_name
        if "/" in category_name:
            simple_category = category_name.split("/")[-1].strip()
        
        logger.info(f"Looking for schema for category: {category_name} (simple: {simple_category})")
        
        # Step 1: Search for existing schema files
        schema_files = list(schemas_dir.glob("EbayCat_*.json"))
        
        for schema_file in schema_files:
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    import json
                    schema_data = json.load(f)
                    
                # Check if this schema matches the category
                # Handle both old format (_metadata.category_name) and new format
                metadata = schema_data.get("_metadata", {})
                schema_cat_name = metadata.get("category_name") or schema_data.get("categoryName") or schema_data.get("name") or ""
                
                if schema_cat_name == category_name or \
                   schema_cat_name.endswith(simple_category) or \
                   schema_cat_name == simple_category:
                    logger.info(f"Found existing schema file: {schema_file.name}")
                    return {
                        "categoryId": metadata.get("category_id") or schema_data.get("categoryId"),
                        "categoryName": simple_category,
                        "schema": schema_data
                    }
            except Exception as e:
                logger.debug(f"Error reading schema file {schema_file}: {e}")
                continue
        
        # Step 2: Look up category ID from mapping
        logger.info(f"Schema file not found, looking up category ID from mapping")
        category_data = _get_category_id_from_mapping(category_name)
        
        if not category_data:
            logger.warning(f"Could not find eBay category ID for: {category_name}")
            return {"error": f"No category mapping found for: {category_name}"}
        
        category_id = category_data.get("categoryId")
        fees_data = category_data.get("fees", {})
        logger.info(f"Found category ID {category_id} in mapping with fees: {fees_data}")
        
        # Step 3: Check if schema already exists for this category ID
        schema_file_pattern = f"EbayCat_{category_id}_*.json"
        existing_schema = list(schemas_dir.glob(schema_file_pattern))
        
        if existing_schema:
            logger.info(f"Found existing schema for category ID {category_id}")
            with open(existing_schema[0], 'r', encoding='utf-8') as f:
                import json
                schema_data = json.load(f)
                return {
                    "categoryId": category_id,
                    "categoryName": simple_category,
                    "schema": schema_data
                }
        
        # Step 4: Fetch schema from eBay API
        logger.info(f"Fetching eBay schema for category ID: {category_id}")
        try:
            aspects_result = fetch_ebay_aspects_from_api(category_id)
            
            # Get fees from mapping, with fallback to defaults
            payment_fee = fees_data.get("payment_fee", 0.35) if fees_data else 0.35
            sales_commission_percentage = fees_data.get("sales_commission_up_to", 0.12) if fees_data else 0.12
            
            # Build schema JSON in old format
            schema_to_save = {
                "_metadata": {
                    "category_name": category_name,
                    "category_id": category_id,
                    "marketplace": "EBAY_DE",
                    "fees": {
                        "payment_fee": payment_fee,
                        "sales_commission_percentage": sales_commission_percentage
                    }
                },
                "schema": {
                    "required": aspects_result.get("required", []),
                    "optional": aspects_result.get("optional", [])
                }
            }
            
            # Save to schemas folder with old naming convention
            schema_file_name = f"EbayCat_{category_id}_EBAY_DE.json"
            schema_file_path = schemas_dir / schema_file_name
            
            with open(schema_file_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(schema_to_save, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved new schema to {schema_file_path}")
            
            return {
                "categoryId": category_id,
                "categoryName": simple_category,
                "schema": schema_to_save
            }
            
        except Exception as e:
            logger.error(f"Error fetching schema from eBay API for category ID {category_id}: {e}")
            return {"error": f"Failed to fetch eBay schema for category ID {category_id}: {str(e)}"}
        
    except Exception as e:
        logger.error(f"Error getting schema by category name: {e}")
        return {"error": str(e)}


def _get_category_id_from_mapping(category_name: str) -> Optional[dict]:
    """
    Load category data from category_mapping.json file
    First tries exact full path match, then simple name match
    
    Args:
        category_name: Category name or full path to look up
    
    Returns:
        Dict with categoryId and fees if found in mapping, None otherwise
    """
    try:
        mapping_file = ebay_schema_repo.SCHEMAS_DIR / "category_mapping.json"
        
        if not mapping_file.exists():
            logger.debug(f"Category mapping file not found: {mapping_file}")
            return None
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            import json
            mapping_data = json.load(f)
        
        mappings = mapping_data.get("categoryMappings", [])
        logger.debug(f"Loaded {len(mappings)} category mappings from {mapping_file}")
        
        # Extract simple name from full path
        simple_name = category_name
        if "/" in category_name:
            simple_name = category_name.split("/")[-1].strip()
        
        # Strategy 1: Try exact full path match first
        for entry in mappings:
            full_path = entry.get("fullPath", "")
            if full_path == category_name:
                cat_id = entry.get("categoryId")
                fees = entry.get("fees", {})
                logger.info(f"Found category ID {cat_id} (full path match) for '{category_name}'")
                return {"categoryId": cat_id, "fees": fees}
        
        # Strategy 2: Try simple name exact match
        for entry in mappings:
            if entry.get("categoryName", "").lower() == simple_name.lower():
                cat_id = entry.get("categoryId")
                fees = entry.get("fees", {})
                logger.info(f"Found category ID {cat_id} (simple name match) for '{simple_name}'")
                return {"categoryId": cat_id, "fees": fees}
        
        logger.debug(f"No mapping found for category: {category_name}")
        return None
        
    except Exception as e:
        logger.error(f"Error loading category mapping: {e}")
        return None


async def _search_ebay_category_id(category_name: str) -> Optional[str]:
    """
    Search eBay API to find category ID by category name.
    Tries multiple search strategies.
    
    Args:
        category_name: Simple category name (e.g., "BHs & BH-Sets")
    
    Returns:
        Category ID if found, None otherwise
    """
    try:
        tree_id = fetch_category_tree_id()
        base_url = get_taxonomy_endpoint()
        headers = {
            "Authorization": f"Bearer {get_ebay_token()}",
            "Accept": "application/json",
        }
        
        # Strategy 1: Try exact search with category suggestions
        logger.info(f"Strategy 1: Searching for category '{category_name}' using suggestions API")
        try:
            url = f"{base_url}/category_tree/{tree_id}/get_category_suggestions"
            params = {"q": category_name}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            suggestions = data.get("categorySuggestions", [])
            logger.info(f"Got {len(suggestions)} suggestions for '{category_name}'")
            
            if suggestions:
                first_match = suggestions[0]
                cat_id = first_match.get("categoryId")
                cat_name = first_match.get("categoryName", "")
                logger.info(f"Found eBay category ID {cat_id} ({cat_name}) for '{category_name}'")
                return cat_id
        except Exception as e:
            logger.debug(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Try searching for just the main keyword (first word)
        logger.info(f"Strategy 2: Trying shorter search with first keyword")
        try:
            first_word = category_name.split()[0]
            url = f"{base_url}/category_tree/{tree_id}/get_category_suggestions"
            params = {"q": first_word}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            suggestions = data.get("categorySuggestions", [])
            logger.info(f"Got {len(suggestions)} suggestions for '{first_word}'")
            
            if suggestions:
                # Look for best match
                for suggestion in suggestions:
                    cat_name = suggestion.get("categoryName", "").lower()
                    if category_name.lower() in cat_name or "bh" in cat_name.lower():
                        cat_id = suggestion.get("categoryId")
                        logger.info(f"Found matching eBay category ID {cat_id} ({cat_name})")
                        return cat_id
        except Exception as e:
            logger.debug(f"Strategy 2 failed: {e}")
        
        # Strategy 3: Try without special characters
        logger.info(f"Strategy 3: Trying search without special characters")
        try:
            clean_name = category_name.replace("&", "and").replace(" - ", " ")
            url = f"{base_url}/category_tree/{tree_id}/get_category_suggestions"
            params = {"q": clean_name}
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            suggestions = data.get("categorySuggestions", [])
            if suggestions:
                first_match = suggestions[0]
                cat_id = first_match.get("categoryId")
                logger.info(f"Found eBay category ID {cat_id} for '{clean_name}'")
                return cat_id
        except Exception as e:
            logger.debug(f"Strategy 3 failed: {e}")
        
        logger.warning(f"No eBay category found for: {category_name} after all strategies")
        return None
        
    except requests.HTTPError as e:
        logger.error(f"eBay API error searching categories: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error searching eBay categories: {e}")
        return None


# Import pandas at module level to avoid issues
import pandas as pd

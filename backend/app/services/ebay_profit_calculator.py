"""eBay profit calculation service for listings cache."""
import logging
import json
import sys
import sqlite3
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Shipping costs (net) by marketplace
SHIPPING_COSTS_NET = {
    "Germany": 9.40,         # Germany (DE)
    "eBay.de": 9.40,
    "EBAY_DE": 9.40,
    "ebay_de": 9.40,
}
DEFAULT_SHIPPING_COST_NET = 11.50  # Rest of world

# VAT rates by country/marketplace
VAT_RATES = {
    "DE": 0.19,  # Germany
    "FR": 0.20,  # France
    "IT": 0.22,  # Italy
    "ES": 0.21,  # Spain
}
DEFAULT_VAT_RATE = 0.19  # Default to Germany VAT
NON_GERMANY_SURCHARGE = 4.99  # Extra charge for non-Germany customers

# Cache for schema fees
_SCHEMA_FEES_CACHE = {}

# Cache for Total Cost Net by SKU
_TOTAL_COST_NET_CACHE = None


def _load_schema_fees_cache() -> Dict[str, Dict[str, float]]:
    """Load fees from schema files into memory."""
    global _SCHEMA_FEES_CACHE
    
    if _SCHEMA_FEES_CACHE:
        return _SCHEMA_FEES_CACHE
    
    schemas_dir = Path(__file__).resolve().parents[2] / "schemas"
    
    try:
        # Load each schema file and extract fees
        for schema_file in schemas_dir.glob("EbayCat_*.json"):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                
                # Extract category ID from filename: EbayCat_{id}_EBAY_DE.json
                parts = schema_file.stem.split('_')
                if len(parts) >= 2:
                    cat_id = parts[1]
                    metadata = schema_data.get('_metadata', {})
                    fees = metadata.get('fees', {})
                    
                    if fees:
                        # Handle None values in fees
                        payment_fee = fees.get('payment_fee', 0.0)
                        commission = fees.get('sales_commission_percentage', 0.0)
                        
                        _SCHEMA_FEES_CACHE[str(cat_id)] = {
                            'payment_fee': float(payment_fee) if payment_fee is not None else 0.0,
                            'sales_commission_percentage': float(commission) if commission is not None else 0.0
                        }
            except Exception as e:
                logger.warning(f"[FEES] Error loading fees from {schema_file.name}: {e}")
        
        logger.info(f"[FEES] Loaded fees cache for {len(_SCHEMA_FEES_CACHE)} categories")
    except Exception as e:
        logger.warning(f"[FEES] Error loading schema fees cache: {e}")
    
    return _SCHEMA_FEES_CACHE


def _load_total_cost_net_cache() -> Dict[str, float]:
    """Load Total Cost Net by SKU from inventory database."""
    global _TOTAL_COST_NET_CACHE

    if _TOTAL_COST_NET_CACHE is not None:
        return _TOTAL_COST_NET_CACHE

    try:
        # Use the correct database location: legacy/cache/inventory.db
        legacy_dir = Path(__file__).resolve().parents[2] / "legacy"
        db_path = legacy_dir / "cache" / "inventory.db"
        
        # Column names in the database
        sku_col = "SKU (Old)"
        cost_col = "Total Cost Net"

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Verify columns exist in DB
            columns = [row[1] for row in conn.execute("PRAGMA table_info(inventory)").fetchall()]
            if sku_col not in columns or cost_col not in columns:
                raise RuntimeError(f"Missing columns in inventory DB: {sku_col}, {cost_col}")

            rows = conn.execute(
                f'SELECT "{sku_col}", "{cost_col}" FROM inventory'
            ).fetchall()
        finally:
            conn.close()

        cost_map: Dict[str, float] = {}
        for row in rows:
            sku = str(row[sku_col]).strip() if row[sku_col] is not None else ""
            if not sku or sku.lower() == "nan":
                continue

            value = row[cost_col]
            try:
                cost_value = float(value) if value is not None and str(value).lower() != "nan" else 0.0
            except (TypeError, ValueError):
                cost_value = 0.0

            cost_map[sku] = cost_value

        _TOTAL_COST_NET_CACHE = cost_map
        logger.info("[COST] Loaded Total Cost Net for %s SKUs from inventory.db", len(cost_map))
    except Exception as e:
        logger.warning("[COST] Error loading Total Cost Net from inventory.db: %s", e)
        _TOTAL_COST_NET_CACHE = {}

    return _TOTAL_COST_NET_CACHE


def get_total_cost_net_for_sku(sku: Optional[str]) -> float:
    """
    Get Total Cost Net for a SKU from inventory database.
    
    Handles multi-SKU listings:
    - Comma-separated (,) = individual separate SKUs
    - Dash-separated ( - ) = multiple SKUs forming an array
    - Dash-range (P0010036-P0010040) = range of SKUs
    - Hybrid = mix of both
    
    For multi-SKU, returns the average cost across all SKUs.
    """
    if not sku:
        return 0.0

    normalized_sku = str(sku).strip()
    
    # Check if this is a multi-SKU listing
    is_multi_sku = False
    
    if "," in normalized_sku or " - " in normalized_sku:
        # Comma-separated or space-dash-separated
        is_multi_sku = True
    elif "-" in normalized_sku:
        # Could be a range like "P0010036-P0010040" - check with regex
        import re
        if re.search(r'[A-Z]\d+-[A-Z]?\d+', normalized_sku):
            is_multi_sku = True
    
    if is_multi_sku:
        return _get_average_cost_for_multi_sku(normalized_sku)
    
    # Single SKU - use original logic
    cost_map = _load_total_cost_net_cache()
    if normalized_sku in cost_map:
        return float(cost_map.get(normalized_sku, 0.0))

    # Fallback: try to read from product JSON if available
    try:
        products_dir = Path(__file__).resolve().parents[2] / "legacy" / "products"
        json_path = products_dir / f"{normalized_sku}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            product = data.get(normalized_sku, data)
            price_data = product.get("Price Data", {})
            value = price_data.get("Total Cost Net", 0.0)
            return float(value) if value is not None else 0.0
    except Exception as e:
        logger.warning("[COST] Failed to read product JSON for SKU=%s: %s", normalized_sku, e)

    return 0.0


def _get_average_cost_for_multi_sku(sku_string: str) -> float:
    """
    Calculate average Total Cost Net for multi-SKU listings.
    
    Supports:
    - Comma-separated: "SKU1,SKU2,SKU3"
    - Dash-separated: "SKU1 - SKU2 - SKU3"
    - Range format: "P0010482-P0010490" (expands to P0010482...P0010490)
    - Hybrid: "SKU1,SKU2 - SKU3"
    """
    if not sku_string:
        return 0.0
    
    # Parse SKUs from different formats
    skus = []
    
    # First split by comma if it exists
    if "," in sku_string:
        parts = sku_string.split(",")
        for part in parts:
            part = part.strip()
            # Each part might contain dash-separated SKUs or ranges
            if " - " in part:
                # Space-dash-separated (explicit list)
                sub_skus = [s.strip() for s in part.split(" - ")]
                skus.extend(sub_skus)
            elif "-" in part:
                # Could be a range like "P0010482-P0010490"
                range_skus = _expand_sku_range(part)
                if range_skus:
                    skus.extend(range_skus)
                else:
                    skus.append(part)
            else:
                skus.append(part)
    else:
        # No comma - try dash separation
        if " - " in sku_string:
            # Space-dash-separated
            parts = sku_string.split(" - ")
            skus.extend([s.strip() for s in parts])
        elif "-" in sku_string:
            # Could be a range like "P0010482-P0010490"
            range_skus = _expand_sku_range(sku_string)
            if range_skus:
                skus.extend(range_skus)
            else:
                skus.append(sku_string)
        else:
            skus.append(sku_string)
    
    # Remove empty strings
    skus = [s for s in skus if s]
    
    if not skus:
        logger.warning("[COST] Could not parse multi-SKU string: %s", sku_string)
        return 0.0
    
    logger.info("[COST] Multi-SKU detected with %d SKUs: %s (from: %s)", len(skus), skus[:3] if len(skus) > 3 else skus, sku_string)
    
    # Get cost for each SKU
    costs = []
    cost_map = _load_total_cost_net_cache()
    found_count = 0
    
    for single_sku in skus:
        single_sku = single_sku.strip()
        cost = 0.0
        
        # Try cost map first
        if single_sku in cost_map:
            cost = float(cost_map.get(single_sku, 0.0))
            found_count += 1
            logger.debug("[COST] Found %s in cache: €%.2f", single_sku, cost)
        else:
            # Try product JSON
            try:
                products_dir = Path(__file__).resolve().parents[2] / "legacy" / "products"
                json_path = products_dir / f"{single_sku}.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    product = data.get(single_sku, data)
                    price_data = product.get("Price Data", {})
                    cost_value = price_data.get("Total Cost Net", 0.0)
                    cost = float(cost_value) if cost_value is not None else 0.0
                    if cost > 0:
                        found_count += 1
                        logger.debug("[COST] Found %s in JSON: €%.2f", single_sku, cost)
            except Exception as e:
                logger.debug("[COST] Failed to read product JSON for SKU=%s: %s", single_sku, e)
        
        if cost > 0:
            costs.append(cost)
    
    # Calculate average
    if not costs:
        logger.warning("[COST] No costs found for any SKU in: %s (checked %d SKUs, found %d)", 
                      sku_string, len(skus), found_count)
        return 0.0
    
    average_cost = sum(costs) / len(costs)
    logger.info("[COST] Multi-SKU (%s) average cost: €%.2f (found costs for %d of %d SKUs)", 
                sku_string, average_cost, len(costs), len(skus))
    
    return average_cost


def _expand_sku_range(sku_range: str) -> list:
    """
    Expand a SKU range like 'P0010482-P0010490' into individual SKUs.
    
    Returns empty list if not a valid range format.
    """
    sku_range = sku_range.strip()
    
    if "-" not in sku_range:
        return []
    
    # Split by dash
    parts = sku_range.split("-")
    
    if len(parts) != 2:
        # More than one dash, not a simple range
        return []
    
    start_sku = parts[0].strip()
    end_sku = parts[1].strip()
    
    # Extract prefix and numeric parts
    # E.g., "P0010482" -> prefix="P", number=10482
    import re
    start_match = re.match(r"^([A-Za-z]*)(\d+)$", start_sku)
    end_match = re.match(r"^([A-Za-z]*)(\d+)$", end_sku)
    
    if not start_match or not end_match:
        # Not a valid range format
        return []
    
    start_prefix, start_num = start_match.groups()
    end_prefix, end_num = end_match.groups()
    
    # Prefixes must match
    if start_prefix != end_prefix:
        return []
    
    start_num = int(start_num)
    end_num = int(end_num)
    
    # Validate range
    if start_num >= end_num or (end_num - start_num) > 1000:
        # Invalid range or suspiciously large
        logger.warning("[COST] Invalid SKU range: %s (span=%d)", sku_range, end_num - start_num)
        return []
    
    # Generate range
    num_digits = len(parts[0].split(start_prefix)[1]) if start_prefix else len(str(start_num))
    skus = []
    for i in range(start_num, end_num + 1):
        sku = f"{start_prefix}{str(i).zfill(num_digits)}"
        skus.append(sku)
    
    logger.debug("[COST] Expanded range %s into %d SKUs", sku_range, len(skus))
    return skus


def _is_germany_marketplace(marketplace: str) -> bool:
    """Check if marketplace is Germany."""
    if not marketplace:
        return False
    
    marketplace_lower = str(marketplace).lower()
    
    # Check for Germany variations
    for key in SHIPPING_COSTS_NET.keys():
        if key.lower() in marketplace_lower or marketplace_lower in key.lower():
            return True
    
    return False


def _get_vat_rate_for_marketplace(marketplace: str) -> float:
    """Get VAT rate for marketplace."""
    if not marketplace:
        return DEFAULT_VAT_RATE

    marketplace_upper = str(marketplace).upper().strip()

    # Normalize common formats to country codes
    normalized_map = {
        "EBAY_DE": "DE",
        "EBAY_FR": "FR",
        "EBAY_IT": "IT",
        "EBAY_ES": "ES",
        "GERMANY": "DE",
        "FRANCE": "FR",
        "ITALY": "IT",
        "SPAIN": "ES",
        "DE": "DE",
        "FR": "FR",
        "IT": "IT",
        "ES": "ES",
    }

    country_code = normalized_map.get(marketplace_upper, marketplace_upper)
    return VAT_RATES.get(country_code, DEFAULT_VAT_RATE)


def _get_marketplace_shipping_cost(marketplace: str) -> float:
    """Get shipping cost for marketplace. Default to 11.50 for non-Germany."""
    if not marketplace:
        return DEFAULT_SHIPPING_COST_NET
    
    marketplace_lower = str(marketplace).lower()
    
    # Check for Germany variations
    for key, cost in SHIPPING_COSTS_NET.items():
        if key.lower() in marketplace_lower or marketplace_lower in key.lower():
            return cost
    
    return DEFAULT_SHIPPING_COST_NET


def get_category_fees(category_id: Optional[str]) -> Optional[Dict[str, float]]:
    """
    Get fees for a category from the schema files.
    
    Args:
        category_id: eBay category ID
    
    Returns:
        Dict with payment_fee and sales_commission_percentage, or None if not found
    """
    if not category_id:
        return None
    
    # Load cache if not already loaded
    fees_cache = _load_schema_fees_cache()
    
    # Look up by category ID
    cat_id = str(category_id)
    if cat_id in fees_cache:
        return fees_cache[cat_id]
    
    logger.debug(f"[FEES] No fees found for category {category_id}")
    return None


def calculate_listing_profit(
    listing: Dict[str, Any],
    category_fees: Optional[Dict[str, float]] = None,
    total_cost_net: Optional[float] = None,
    lookup_by_category_id: bool = True,
    lookup_total_cost_net: bool = True,
) -> Dict[str, float]:
    """
    Calculate profit metrics for an eBay listing.
    
    Includes:
    - €4.99 surcharge for non-Germany customers
    - Marketplace-specific VAT rates
    - Commission calculated on customer's FULL PAYMENT (brutto)
    
    Formula:
    - Apply €4.99 surcharge if marketplace is not Germany
    - selling_price_netto = selling_price_brutto / (1 + vat_rate)
    - sales_commission = selling_price_brutto * commission% (ON BRUTTO!)
    - Net Profit = selling_price_netto - sales_commission - payment_fee - shipping_costs_net - total_cost_net
    
    Args:
        listing: Listing dict with price, marketplace, category_id, etc.
        category_fees: Dict with 'payment_fee' and 'sales_commission_percentage' (override)
        total_cost_net: Net cost of the product from database
        lookup_by_category_id: Whether to look up fees from schema files by category_id
        lookup_total_cost_net: Whether to look up Total Cost Net by SKU
    
    Returns:
        Dict with profit calculation results:
        {
            'selling_price_brutto': float,
            'selling_price_netto': float,
            'payment_fee': float,
            'sales_commission': float,
            'sales_commission_percentage': float,
            'shipping_costs_net': float,
            'total_cost_net': float,
            'net_profit': float,
            'net_profit_margin_percent': float
        }
    """
    # Extract price (use price field or fallback to None)
    selling_price_brutto = listing.get("price")
    if selling_price_brutto is None or selling_price_brutto <= 0:
        return {
            'selling_price_brutto': 0.0,
            'selling_price_netto': 0.0,
            'payment_fee': 0.0,
            'sales_commission': 0.0,
            'sales_commission_percentage': 0.0,
            'shipping_costs_net': 0.0,
            'total_cost_net': total_cost_net,
            'net_profit': 0.0,
            'net_profit_margin_percent': 0.0
        }
    
    # Parse as float
    try:
        selling_price_brutto = float(selling_price_brutto)
    except (TypeError, ValueError):
        selling_price_brutto = 0.0
    
    # Get marketplace information
    marketplace = listing.get("site") or listing.get("marketplace", "")
    is_germany = _is_germany_marketplace(marketplace)
    
    # Add €4.99 surcharge for non-Germany customers
    if not is_germany:
        selling_price_brutto += NON_GERMANY_SURCHARGE
    
    # Get VAT rate for this marketplace
    vat_rate = _get_vat_rate_for_marketplace(marketplace)
    
    # Calculate netto price: brutto / (1 + vat_rate)
    # This removes the VAT to get what we actually receive
    selling_price_netto = selling_price_brutto / (1 + vat_rate)
    
    # Get fees
    payment_fee = 0.0
    sales_commission_percentage = 0.0
    
    # Try to look up from schema files first if category_id is available
    if lookup_by_category_id:
        category_id = listing.get("category_id")
        if category_id:
            schema_fees = get_category_fees(category_id)
            if schema_fees:
                payment_fee = float(schema_fees.get("payment_fee") or 0.0)
                sales_commission_percentage = float(schema_fees.get("sales_commission_percentage") or 0.0)
                logger.debug(f"[PROFIT] Using schema fees for category {category_id}: fee=€{payment_fee}, commission={sales_commission_percentage*100:.2f}%")
    
    # Override with explicit category_fees if provided
    if category_fees:
        payment_fee = float(category_fees.get("payment_fee") or 0.0)
        sales_commission_percentage = float(category_fees.get("sales_commission_percentage") or 0.0)
    
    # IMPORTANT: Commission is on the customer's FULL PAYMENT (brutto), not netto
    # This is how eBay calculates it - on the total amount paid by customer
    sales_commission = selling_price_brutto * sales_commission_percentage
    
    # Get shipping cost for marketplace
    shipping_costs_net = _get_marketplace_shipping_cost(marketplace)
    
    # Ensure total_cost_net is valid, optionally load from inventory
    if lookup_total_cost_net and (total_cost_net is None or total_cost_net == 0.0):
        total_cost_net = get_total_cost_net_for_sku(listing.get("sku"))

    try:
        total_cost_net = float(total_cost_net) if total_cost_net else 0.0
    except (TypeError, ValueError):
        total_cost_net = 0.0
    
    # Calculate net profit
    # Net Profit = selling_price_netto - sales_commission - payment_fee - shipping_net - total_cost_net
    # Where:
    # - selling_price_netto = what we receive after VAT (brutto / (1 + vat_rate))
    # - sales_commission = on customer's full payment (brutto)
    # - total_cost_net = product cost from database
    net_profit = selling_price_netto - sales_commission - payment_fee - shipping_costs_net - total_cost_net
    
    # Calculate profit margin (as percentage of total cost)
    net_profit_margin_percent = 0.0
    if total_cost_net > 0:
        net_profit_margin_percent = (net_profit / total_cost_net) * 100
    
    return {
        'selling_price_brutto': round(selling_price_brutto, 2),
        'selling_price_netto': round(selling_price_netto, 2),
        'payment_fee': round(payment_fee, 2),
        'sales_commission': round(sales_commission, 2),
        'sales_commission_percentage': round(sales_commission_percentage, 4),
        'shipping_costs_net': round(shipping_costs_net, 2),
        'total_cost_net': round(total_cost_net, 2),
        'net_profit': round(net_profit, 2),
        'net_profit_margin_percent': round(net_profit_margin_percent, 2)
    }


def enrich_listings_with_profit(
    listings: list,
    category_mapping: Optional[Dict] = None,
    product_jsons: Optional[Dict[str, Dict]] = None,
) -> list:
    """
    Enrich all listings with profit calculations.
    
    Looks up category fees and total cost net from product JSONs.
    
    Args:
        listings: List of listing dicts
        category_mapping: Dict mapping category_id to fees
        product_jsons: Dict mapping item_id to product JSON
    
    Returns:
        List of listings with profit_analysis added
    """
    if category_mapping is None:
        category_mapping = {}
    if product_jsons is None:
        product_jsons = {}
    
    for listing in listings:
        category_id = listing.get("category_id")
        item_id = listing.get("item_id")
        sku = listing.get("sku")
        
        # Get category fees
        category_fees = None
        if category_id and category_mapping:
            cat_data = category_mapping.get(str(category_id), {})
            category_fees = cat_data.get("fees", {}) if isinstance(cat_data, dict) else None
        
        # Get total cost net from product JSON
        total_cost_net = 0.0
        if item_id and product_jsons:
            product = product_jsons.get(item_id, {})
            price_data = product.get("Price Data", {})
            total_cost_net = float(price_data.get("Total Cost Net", 0.0))

        if total_cost_net == 0.0 and sku:
            total_cost_net = get_total_cost_net_for_sku(sku)
        
        # Calculate profit
        profit_analysis = calculate_listing_profit(
            listing,
            category_fees=category_fees,
            total_cost_net=total_cost_net,
            lookup_total_cost_net=True
        )
        
        # Add to listing
        listing['profit_analysis'] = profit_analysis
    
    return listings

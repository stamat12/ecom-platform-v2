"""eBay listings cache management service."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import config  # type: ignore

CACHE_FILE = config.PRODUCTS_FOLDER_PATH / "cache" / "ebay_listings_cache.json"


def _extract_lookup_sku(raw_sku: str) -> str:
    """Extract primary SKU token for matching variant SKU formats."""
    if not raw_sku:
        return ""

    sku_value = str(raw_sku).strip()
    if not sku_value:
        return ""

    if "," in sku_value:
        sku_value = sku_value.split(",", 1)[0].strip()

    if " - " in sku_value:
        sku_value = sku_value.split(" - ", 1)[0].strip()
    elif "-" in sku_value:
        parts = [part.strip() for part in sku_value.split("-") if part.strip()]
        if len(parts) == 2:
            sku_value = parts[0]

    return sku_value


def read_cache() -> Optional[Dict]:
    """
    Read the eBay listings cache file.
    
    Returns:
        Dict with 'timestamp' and 'listings' keys, or None if cache doesn't exist/invalid.
    """
    if not CACHE_FILE.exists():
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        if 'timestamp' not in cache or 'listings' not in cache:
            return None
        
        return cache
    except Exception as e:
        print(f"Error reading eBay listings cache: {e}")
        return None


def write_cache(listings: list) -> None:
    """
    Write eBay listings to cache file.
    
    Args:
        listings: List of eBay listing dicts with 'item_id', 'sku', 'title', etc.
    """
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    cache = {
        'timestamp': datetime.now().isoformat(),
        'listings': listings
    }
    
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_sku_has_listing(sku: str) -> Optional[bool]:
    """
    Check if a SKU has an active eBay listing (from cache).
    
    Args:
        sku: The SKU to check
    
    Returns:
        True if SKU has listing, False if no listing, None if no cache data
    """
    cache = read_cache()
    if cache is None:
        return None
    
    listings = cache.get('listings', [])
    
    # Normalize and check SKU
    normalized_sku = sku.strip()
    
    for listing in listings:
        listing_sku = listing.get('sku', '').strip()
        
        if not listing_sku:
            continue
        
        # Handle comma-separated combined SKUs
        individual_skus = [s.strip() for s in listing_sku.split(',')]
        
        for individual_sku in individual_skus:
            if not individual_sku:
                continue
            
            # Check for exact match
            if individual_sku == normalized_sku:
                return True
            
            # Check for range (e.g., JAL00246-JAL00248)
            if '-' in individual_sku:
                parts = individual_sku.split('-')
                if len(parts) == 2:
                    start_sku, end_sku = parts[0].strip(), parts[1].strip()
                    
                    # Extract prefix and numeric parts
                    start_prefix = ''.join([c for c in start_sku if not c.isdigit()])
                    end_prefix = ''.join([c for c in end_sku if not c.isdigit()])
                    
                    # Must have same prefix
                    if start_prefix == end_prefix:
                        start_num_str = start_sku[len(start_prefix):]
                        end_num_str = end_sku[len(end_prefix):]
                        
                        try:
                            start_num = int(start_num_str)
                            end_num = int(end_num_str)
                            
                            # Check if our SKU is in this range
                            check_prefix = ''.join([c for c in normalized_sku if not c.isdigit()])
                            check_num_str = normalized_sku[len(check_prefix):]
                            
                            if check_prefix == start_prefix:
                                try:
                                    check_num = int(check_num_str)
                                    if start_num <= check_num <= end_num:
                                        return True
                                except ValueError:
                                    pass
                        except ValueError:
                            pass
    
    return False


def _sku_matches_listing_sku(normalized_sku: str, listing_sku: str) -> bool:
    if not listing_sku:
        return False

    individual_skus = [s.strip() for s in listing_sku.split(',')]
    for individual_sku in individual_skus:
        if not individual_sku:
            continue

        if individual_sku == normalized_sku:
            return True

        if '-' in individual_sku:
            parts = individual_sku.split('-')
            if len(parts) == 2:
                start_sku, end_sku = parts[0].strip(), parts[1].strip()
                start_prefix = ''.join([c for c in start_sku if not c.isdigit()])
                end_prefix = ''.join([c for c in end_sku if not c.isdigit()])
                if start_prefix == end_prefix:
                    start_num_str = start_sku[len(start_prefix):]
                    end_num_str = end_sku[len(end_prefix):]
                    try:
                        start_num = int(start_num_str)
                        end_num = int(end_num_str)
                        check_prefix = ''.join([c for c in normalized_sku if not c.isdigit()])
                        check_num_str = normalized_sku[len(check_prefix):]
                        if check_prefix == start_prefix:
                            try:
                                check_num = int(check_num_str)
                                if start_num <= check_num <= end_num:
                                    return True
                            except ValueError:
                                pass
                    except ValueError:
                        pass

    return False


def get_de_listing_title_for_sku(sku: str) -> Optional[str]:
    """Return DE marketplace listing title for SKU from cache, if available."""
    cache = read_cache()
    if cache is None:
        return None

    listings = cache.get('listings', []) or []
    normalized_sku = (sku or "").strip()

    for listing in listings:
        listing_sku = (listing.get('sku') or '').strip()
        if not _sku_matches_listing_sku(normalized_sku, listing_sku):
            continue

        marketplace = str(listing.get('marketplace') or '').strip().upper()
        site = str(listing.get('site') or '').strip().lower()
        if marketplace == 'DE' or site == 'germany':
            title = listing.get('title')
            if title is not None:
                title_text = str(title).strip()
                if title_text:
                    return title_text

    return None


def get_last_update_time() -> Optional[str]:
    """
    Get the timestamp of the last cache update.
    
    Returns:
        ISO format timestamp string, or None if no cache
    """
    cache = read_cache()
    if cache is None:
        return None
    
    return cache.get('timestamp')


def update_listing_price_in_cache(sku: str, new_price: float) -> bool:
    """
    Update the price field of a listing in the cache file by SKU (DE marketplace).

    Returns True if the listing was found and updated, False otherwise.
    """
    cache = read_cache()
    if not cache:
        return False

    target = str(sku or "").strip()
    if not target:
        return False

    listings = cache.get("listings", [])
    updated = False
    for listing in listings:
        if str(listing.get("sku") or "").strip() != target:
            continue
        listing["price"] = round(float(new_price), 2)
        # Also reset cached profit analysis so it gets recomputed on next fetch
        listing.pop("profit_analysis", None)
        updated = True
        break

    if updated:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return updated


def update_listing_to_auction_in_cache(
    sku: str,
    start_price: float,
    duration_days: int = 7,
    new_item_id: Optional[str] = None,
    old_item_id: Optional[str] = None,
) -> bool:
    """Patch cache entries after converting a live fixed listing to auction."""
    cache = read_cache()
    if not cache:
        return False

    target = str(sku or "").strip()
    if not target:
        return False

    target_lookup = _extract_lookup_sku(target)

    target_old_item_id = str(old_item_id or "").strip()

    listings = cache.get("listings", [])
    updated = False
    converted = False

    # FIRST PASS: Convert the old item ID to auction (if provided)
    if target_old_item_id:
        for listing in listings:
            listing_sku = str(listing.get("sku") or "").strip()
            listing_lookup = _extract_lookup_sku(listing_sku)
            if not listing_sku:
                continue
            if listing_lookup != target_lookup and listing_sku != target:
                continue

            marketplace = str(listing.get("marketplace") or "").strip().upper()
            site = str(listing.get("site") or "").strip().lower()
            if marketplace != "DE" and site != "germany":
                continue

            listing_item_id = str(listing.get("item_id") or "").strip()
            if listing_item_id == target_old_item_id:
                listing["price"] = round(float(start_price), 2)
                listing["listing_type"] = "Chinese"
                listing["listing_duration"] = f"Days_{int(duration_days)}"
                listing["listing_status"] = "Active"
                if new_item_id:
                    listing["item_id"] = str(new_item_id)
                listing.pop("profit_analysis", None)
                converted = True
                updated = True
                break

    # SECOND PASS: Mark all remaining active fixed-price listings as Ended
    for listing in listings:
        listing_sku = str(listing.get("sku") or "").strip()
        listing_lookup = _extract_lookup_sku(listing_sku)
        if not listing_sku:
            continue
        if listing_lookup != target_lookup and listing_sku != target:
            continue

        marketplace = str(listing.get("marketplace") or "").strip().upper()
        site = str(listing.get("site") or "").strip().lower()
        if marketplace != "DE" and site != "germany":
            continue

        listing_type = str(listing.get("listing_type") or "").strip().lower()
        listing_status = str(listing.get("listing_status") or "").strip().lower()
        listing_item_id = str(listing.get("item_id") or "").strip()

        # Mark active fixed listings as ended (skip the one we just converted)
        if "fixed" in listing_type and listing_status == "active":
            if listing_item_id != (new_item_id or ""):
                listing["listing_status"] = "Ended"
                listing.pop("profit_analysis", None)
                updated = True

    # FALLBACK: If old_item_id wasn't matched, update first related DE listing
    if not converted:
        for listing in listings:
            listing_sku = str(listing.get("sku") or "").strip()
            listing_lookup = _extract_lookup_sku(listing_sku)
            if not listing_sku:
                continue
            if listing_lookup != target_lookup and listing_sku != target:
                continue

            marketplace = str(listing.get("marketplace") or "").strip().upper()
            site = str(listing.get("site") or "").strip().lower()
            if marketplace != "DE" and site != "germany":
                continue

            listing["price"] = round(float(start_price), 2)
            listing["listing_type"] = "Chinese"
            listing["listing_duration"] = f"Days_{int(duration_days)}"
            listing["listing_status"] = "Active"
            if new_item_id:
                listing["item_id"] = str(new_item_id)
            listing.pop("profit_analysis", None)
            updated = True
            break

    if updated:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return updated


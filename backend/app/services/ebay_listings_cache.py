"""eBay listings cache management service."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import config  # type: ignore

CACHE_FILE = config.PRODUCTS_FOLDER_PATH / "cache" / "ebay_listings_cache.json"


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

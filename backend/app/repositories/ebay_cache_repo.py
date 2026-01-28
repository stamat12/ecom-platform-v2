"""
Repository for eBay caches (listings, manufacturers, etc.)
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Cache directory (relative to backend folder)
CACHE_DIR = Path(__file__).parent.parent.parent / "legacy" / "cache"

def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(cache_name: str) -> Path:
    """Get path to cache file"""
    return CACHE_DIR / f"{cache_name}.json"

def _is_cache_valid(cache_path: Path, max_age_hours: float) -> bool:
    """Check if cache file is still valid based on modification time"""
    if not cache_path.exists():
        return False
    
    try:
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mod_time
        return age < timedelta(hours=max_age_hours)
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False

# ===== Listings Cache =====

def get_cached_listings(max_age_hours: float = 6) -> Optional[List[Dict[str, Any]]]:
    """
    Load cached active listings
    
    Args:
        max_age_hours: Maximum age of cache in hours
    
    Returns:
        List of listing dicts or None if cache invalid/missing
    """
    cache_path = _get_cache_path("ebay_listings_cache")
    
    if not _is_cache_valid(cache_path, max_age_hours):
        logger.debug("Listings cache invalid or expired")
        return None
    
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        listings = data.get("listings", [])
        logger.debug(f"Loaded {len(listings)} listings from cache")
        return listings
        
    except Exception as e:
        logger.error(f"Error loading listings cache: {e}")
        return None

def save_listings_cache(listings: List[Dict[str, Any]]) -> bool:
    """
    Save listings cache
    
    Args:
        listings: List of listing dicts
    
    Returns:
        True if saved successfully
    """
    ensure_cache_dir()
    cache_path = _get_cache_path("ebay_listings_cache")
    
    payload = {
        "cached_at": datetime.now().isoformat(),
        "count": len(listings),
        "listings": listings
    }
    
    try:
        # Atomic write
        temp_path = cache_path.with_suffix(".tmp.json")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        temp_path.replace(cache_path)
        logger.info(f"Saved {len(listings)} listings to cache")
        return True
        
    except Exception as e:
        logger.error(f"Error saving listings cache: {e}")
        return False

def clear_listings_cache() -> bool:
    """Delete listings cache"""
    cache_path = _get_cache_path("ebay_listings_cache")
    
    if not cache_path.exists():
        return True
    
    try:
        cache_path.unlink()
        logger.info("Cleared listings cache")
        return True
    except Exception as e:
        logger.error(f"Error clearing listings cache: {e}")
        return False

# ===== Manufacturer Cache =====

def get_manufacturer_info(brand: str) -> Optional[Dict[str, Any]]:
    """
    Load cached manufacturer info
    
    Args:
        brand: Brand name
    
    Returns:
        Manufacturer info dict or None if not cached
    """
    cache_path = _get_cache_path("ebay_manufacturers")
    
    if not cache_path.exists():
        return None
    
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            manufacturers = json.load(f)
        
        # Normalize brand name for lookup
        brand_key = brand.strip().lower()
        info = manufacturers.get(brand_key)
        
        if info:
            logger.debug(f"Found cached manufacturer info for {brand}")
        
        return info
        
    except Exception as e:
        logger.error(f"Error loading manufacturer cache: {e}")
        return None

def save_manufacturer_info(brand: str, info: Dict[str, Any]) -> bool:
    """
    Cache manufacturer info
    
    Args:
        brand: Brand name
        info: Manufacturer info dict
    
    Returns:
        True if saved successfully
    """
    ensure_cache_dir()
    cache_path = _get_cache_path("ebay_manufacturers")
    
    # Load existing cache
    manufacturers = {}
    if cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                manufacturers = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading existing manufacturers cache: {e}")
    
    # Add/update brand
    brand_key = brand.strip().lower()
    manufacturers[brand_key] = {
        **info,
        "cached_at": datetime.now().isoformat(),
        "original_brand": brand
    }
    
    try:
        # Atomic write
        temp_path = cache_path.with_suffix(".tmp.json")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(manufacturers, f, ensure_ascii=False, indent=2)
        
        temp_path.replace(cache_path)
        logger.info(f"Cached manufacturer info for {brand}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving manufacturer cache: {e}")
        return False

def list_cached_manufacturers() -> List[str]:
    """
    Get list of all cached manufacturer brands
    
    Returns:
        List of brand names
    """
    cache_path = _get_cache_path("ebay_manufacturers")
    
    if not cache_path.exists():
        return []
    
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            manufacturers = json.load(f)
        
        return [v.get("original_brand", k) for k, v in manufacturers.items()]
        
    except Exception as e:
        logger.error(f"Error listing manufacturers: {e}")
        return []

def clear_manufacturer_cache() -> bool:
    """Delete manufacturer cache"""
    cache_path = _get_cache_path("ebay_manufacturers")
    
    if not cache_path.exists():
        return True
    
    try:
        cache_path.unlink()
        logger.info("Cleared manufacturer cache")
        return True
    except Exception as e:
        logger.error(f"Error clearing manufacturer cache: {e}")
        return False

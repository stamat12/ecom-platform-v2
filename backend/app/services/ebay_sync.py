"""
eBay listing synchronization service
"""
import logging
import os
import re
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config.ebay_config import (
    get_api_endpoint,
    EBAY_COMPATIBILITY_LEVEL,
    EBAY_SITE_ID,
    LISTINGS_CACHE_DURATION_HOURS
)
from app.repositories import ebay_cache_repo
from app.services import ebay_listings_cache

logger = logging.getLogger(__name__)

NS = {"e": "urn:ebay:apis:eBLBaseComponents"}


def get_ebay_token() -> str:
    """Get eBay access token from environment"""
    token = os.getenv("EBAY_ACCESS_TOKEN")
    if not token:
        raise ValueError("EBAY_ACCESS_TOKEN not found in environment variables")
    return token


def _build_headers(call_name: str, token: str) -> Dict[str, str]:
    """Build headers for eBay Trading API"""
    return {
        "Content-Type": "text/xml",
        "X-EBAY-API-CALL-NAME": call_name,
        "X-EBAY-API-SITEID": EBAY_SITE_ID,
        "X-EBAY-API-COMPATIBILITY-LEVEL": EBAY_COMPATIBILITY_LEVEL,
        "X-EBAY-API-IAF-TOKEN": token,
    }


def _ensure_success(root: ET.Element, call_name: str) -> None:
    """Check if eBay API call was successful"""
    ack = root.findtext("e:Ack", default="", namespaces=NS)
    if ack not in ("Success", "Warning"):
        short_msg = root.findtext(".//e:Errors/e:ShortMessage", default="", namespaces=NS)
        long_msg = root.findtext(".//e:Errors/e:LongMessage", default="", namespaces=NS)
        code = root.findtext(".//e:Errors/e:ErrorCode", default="", namespaces=NS)
        raise RuntimeError(
            f"{call_name} failed (Ack={ack}, ErrorCode={code}).\n"
            f"ShortMessage: {short_msg}\nLongMessage: {long_msg}"
        )


def fetch_active_listings_from_ebay(entries_per_page: int = 200) -> List[Dict[str, str]]:
    """
    Fetch all active eBay listings from API
    
    Returns:
        List of listing dicts
    """
    logger.info("Fetching active listings from eBay API...")
    
    token = get_ebay_token()
    endpoint = get_api_endpoint()
    results: List[Dict[str, str]] = []
    page = 1
    
    while True:
        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{token}</eBayAuthToken>
  </RequesterCredentials>
  <ActiveList>
    <Include>true</Include>
    <Pagination>
      <EntriesPerPage>{entries_per_page}</EntriesPerPage>
      <PageNumber>{page}</PageNumber>
    </Pagination>
  </ActiveList>
  <DetailLevel>ReturnAll</DetailLevel>
</GetMyeBaySellingRequest>
"""
        
        headers = _build_headers("GetMyeBaySelling", token)
        response = requests.post(endpoint, headers=headers, data=xml_body.encode("utf-8"), timeout=60)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        _ensure_success(root, "GetMyeBaySelling")
        
        # Parse items
        items = root.findall(".//e:ActiveList/e:ItemArray/e:Item", namespaces=NS)
        
        for item in items:
            item_id = (item.findtext("e:ItemID", default="", namespaces=NS) or "").strip()
            sku = (item.findtext("e:SKU", default="", namespaces=NS) or "").strip()
            title = (item.findtext("e:Title", default="", namespaces=NS) or "").strip()
            marketplace = (item.findtext("e:Site", default="", namespaces=NS) or "").strip()
            view_url = (item.findtext("e:ListingDetails/e:ViewItemURL", default="", namespaces=NS) or "").strip()
            
            results.append({
                "item_id": item_id,
                "sku": sku,
                "title": title,
                "marketplace": marketplace,
                "view_url": view_url,
            })
        
        # Check pagination
        total_pages_text = root.findtext(
            ".//e:ActiveList/e:PaginationResult/e:TotalNumberOfPages",
            default="1",
            namespaces=NS,
        )
        try:
            total_pages = int(total_pages_text)
        except ValueError:
            total_pages = 1
        
        logger.debug(f"Fetched page {page} of {total_pages} ({len(items)} items)")
        
        if page >= total_pages:
            break
        page += 1
    
    logger.info(f"Fetched {len(results)} active listings from eBay")
    return results


def get_active_listings(use_cache: bool = True, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Get active eBay listings (from cache or API)
    
    Args:
        use_cache: Use cached data if available
        force_refresh: Force refresh even if cache valid
    
    Returns:
        Dict with listings and metadata
    """
    cached = False
    
    # Try cache first
    if use_cache and not force_refresh:
        cached_listings = ebay_cache_repo.get_cached_listings(LISTINGS_CACHE_DURATION_HOURS)
        legacy_cache = ebay_listings_cache.read_cache()
        legacy_listings = legacy_cache.get("listings", []) if legacy_cache else []

        if cached_listings or legacy_listings:
            # Merge listings from both caches (dedupe by item_id + sku)
            merged = []
            seen = set()
            for listing in (cached_listings or []) + (legacy_listings or []):
                item_id = (listing.get("item_id") or "").strip()
                sku = (listing.get("sku") or "").strip()
                key = f"{item_id}::{sku}"
                if key in seen:
                    continue
                seen.add(key)
                merged.append(listing)

            logger.info(
                "Using cached eBay listings (repo=%s, legacy=%s, merged=%s)",
                len(cached_listings or []),
                len(legacy_listings or []),
                len(merged),
            )
            return {
                "success": True,
                "total_listings": len(merged),
                "cached": True,
                "listings": merged,
                "message": f"Loaded {len(merged)} listings from cache"
            }
    
    # Fetch from API
    listings = fetch_active_listings_from_ebay()
    
    # Save to cache
    ebay_cache_repo.save_listings_cache(listings)
    
    return {
        "success": True,
        "total_listings": len(listings),
        "cached": False,
        "listings": listings,
        "message": f"Fetched {len(listings)} listings from eBay API"
    }


def get_sku_listing_counts(use_cache: bool = True) -> Dict[str, Any]:
    """
    Get count of active listings per SKU
    
    Args:
        use_cache: Use cached data if available
    
    Returns:
        Dict with SKU counts and metadata
    """
    # Get listings
    result = get_active_listings(use_cache=use_cache)
    listings = result.get("listings", [])
    cached = result.get("cached", False)
    
    # Count by SKU
    sku_counts: Dict[str, int] = {}
    
    for listing in listings:
        sku = listing.get("sku", "").strip()
        if sku:
            # Handle combined SKUs (separated by comma)
            individual_skus = [s.strip() for s in sku.split(',')]
            for individual_sku in individual_skus:
                if individual_sku:
                    sku_counts[individual_sku] = sku_counts.get(individual_sku, 0) + 1
    
    logger.info(f"Counted listings for {len(sku_counts)} SKUs")
    
    return {
        "success": True,
        "total_skus": len(sku_counts),
        "total_listings": len(listings),
        "sku_counts": sku_counts,
        "cached": cached,
        "message": f"Counted {len(listings)} listings across {len(sku_counts)} SKUs"
    }


def sync_listing_status_for_sku(sku: str) -> Dict[str, Any]:
    """
    Sync listing status for specific SKU
    
    Updates product JSON with listing count
    
    Returns:
        Dict with sync results
    """
    logger.info(f"Syncing listing status for SKU {sku}")
    
    # Get counts
    counts_result = get_sku_listing_counts(use_cache=True)
    sku_counts = counts_result.get("sku_counts", {})
    
    listing_count = sku_counts.get(sku, 0)
    
    # Could update product JSON here with listing count/status
    # For now, just return the count
    
    return {
        "success": True,
        "sku": sku,
        "listing_count": listing_count,
        "updated": False,  # Not updating JSON yet
        "message": f"SKU {sku} has {listing_count} active listing(s)"
    }


def clear_listings_cache() -> Dict[str, Any]:
    """Clear listings cache"""
    success = ebay_cache_repo.clear_listings_cache()
    
    return {
        "success": success,
        "message": "Listings cache cleared" if success else "Failed to clear cache"
    }

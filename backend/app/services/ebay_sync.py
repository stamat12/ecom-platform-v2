"""
eBay listing synchronization service
"""
import logging
import re
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from app.config.ebay_config import (
    get_api_endpoint,
    EBAY_COMPATIBILITY_LEVEL,
    EBAY_SITE_ID,
    LISTINGS_CACHE_DURATION_HOURS
)
from app.repositories import ebay_cache_repo
from app.services import ebay_listings_cache
from app.services.ebay_oauth import get_access_token

logger = logging.getLogger(__name__)

NS = {"e": "urn:ebay:apis:eBLBaseComponents"}


def _clean_text(value: str) -> str:
    return (value or "").strip()


def _parse_int(value: str) -> Optional[int]:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return None


def _parse_float(value: str) -> Optional[float]:
    try:
        return float((value or "").strip())
    except (TypeError, ValueError):
        return None


def _parse_bool(value: str) -> Optional[bool]:
    val = (value or "").strip().lower()
    if val in {"true", "1", "yes"}:
        return True
    if val in {"false", "0", "no"}:
        return False
    return None


def _marketplace_from_url(view_url: str) -> str:
    if not view_url:
        return ""
    host = urlparse(view_url).netloc.lower()
    if "ebay." in host:
        return host.split("ebay.")[-1].upper()
    return ""


def _extract_listing_from_item(item: ET.Element) -> Dict[str, Any]:
    item_id = _clean_text(item.findtext("e:ItemID", default="", namespaces=NS))
    sku = _clean_text(item.findtext("e:SKU", default="", namespaces=NS))
    title = _clean_text(item.findtext("e:Title", default="", namespaces=NS))
    site = _clean_text(item.findtext("e:Site", default="", namespaces=NS))
    view_url = _clean_text(item.findtext("e:ListingDetails/e:ViewItemURL", default="", namespaces=NS))

    current_price_node = item.find("e:SellingStatus/e:CurrentPrice", namespaces=NS)
    current_price_value = _clean_text(current_price_node.text if current_price_node is not None else "")
    current_price_currency = _clean_text(current_price_node.attrib.get("currencyID", "") if current_price_node is not None else "")

    picture_urls = [
        _clean_text(node.text or "")
        for node in item.findall("e:PictureDetails/e:PictureURL", namespaces=NS)
        if _clean_text(node.text or "")
    ]
    primary_image_url = _clean_text(item.findtext("e:PictureDetails/e:GalleryURL", default="", namespaces=NS))
    if not primary_image_url and picture_urls:
        primary_image_url = picture_urls[0]

    marketplace = site or _marketplace_from_url(view_url)

    return {
        "item_id": item_id,
        "sku": sku,
        "title": title,
        "marketplace": marketplace,
        "site": site,
        "view_url": view_url,
        "price": _parse_float(current_price_value),
        "currency": current_price_currency or None,
        "quantity_total": _parse_int(item.findtext("e:Quantity", default="", namespaces=NS)),
        "quantity_available": _parse_int(item.findtext("e:SellingStatus/e:QuantityAvailable", default="", namespaces=NS)),
        "quantity_sold": _parse_int(item.findtext("e:SellingStatus/e:QuantitySold", default="", namespaces=NS)),
        "listing_status": _clean_text(item.findtext("e:SellingStatus/e:ListingStatus", default="", namespaces=NS)) or None,
        "listing_type": _clean_text(item.findtext("e:ListingType", default="", namespaces=NS)) or None,
        "start_time": _clean_text(item.findtext("e:ListingDetails/e:StartTime", default="", namespaces=NS)) or None,
        "end_time": _clean_text(item.findtext("e:ListingDetails/e:EndTime", default="", namespaces=NS)) or None,
        "condition_id": _parse_int(item.findtext("e:ConditionID", default="", namespaces=NS)),
        "condition_name": _clean_text(item.findtext("e:ConditionDisplayName", default="", namespaces=NS)) or None,
        "category_id": _clean_text(item.findtext("e:PrimaryCategory/e:CategoryID", default="", namespaces=NS)) or None,
        "category_name": _clean_text(item.findtext("e:PrimaryCategory/e:CategoryName", default="", namespaces=NS)) or None,
        "best_offer_enabled": _parse_bool(item.findtext("e:BestOfferDetails/e:BestOfferEnabled", default="", namespaces=NS)),
        "primary_image_url": primary_image_url or None,
        "image_urls": picture_urls,
    }


def get_ebay_token() -> str:
    """Get eBay access token from environment"""
    return get_access_token()


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


def fetch_active_listings_from_ebay(entries_per_page: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch all active eBay listings from API
    
    Returns:
        List of listing dicts
    """
    logger.info("Fetching active listings from eBay API...")
    
    token = get_ebay_token()
    endpoint = get_api_endpoint()
    results: List[Dict[str, Any]] = []
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
            results.append(_extract_listing_from_item(item))
        
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

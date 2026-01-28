"""
eBay Trading API - Fetch active listings with caching support.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}

# Cache settings
CACHE_FILE = Path(__file__).parent.parent / "cache" / "ebay_listings_cache.json"
CACHE_DURATION_HOURS = 6


def post_trading(
    call_name: str,
    oauth_token: str,
    xml_body: str,
    site_id: int = 77,
    compatibility_level: int = 1231,
) -> str:
    """Post request to eBay Trading API."""
    headers = {
        "Content-Type": "text/xml",
        "X-EBAY-API-CALL-NAME": call_name,
        "X-EBAY-API-SITEID": str(site_id),
        "X-EBAY-API-COMPATIBILITY-LEVEL": str(compatibility_level),
        "X-EBAY-API-IAF-TOKEN": oauth_token,
    }
    r = requests.post(TRADING_ENDPOINT, data=xml_body.encode("utf-8"), headers=headers, timeout=60)
    r.raise_for_status()
    return r.text


def ensure_success(root: ET.Element, call_name: str, raw_xml: str) -> None:
    """Check if eBay API call was successful."""
    ack = root.findtext("e:Ack", default="", namespaces=NS)
    if ack not in ("Success", "Warning"):
        short_msg = root.findtext(".//e:Errors/e:ShortMessage", default="", namespaces=NS)
        long_msg = root.findtext(".//e:Errors/e:LongMessage", default="", namespaces=NS)
        code = root.findtext(".//e:Errors/e:ErrorCode", default="", namespaces=NS)
        raise RuntimeError(
            f"{call_name} failed (Ack={ack}, ErrorCode={code}).\n"
            f"ShortMessage: {short_msg}\nLongMessage: {long_msg}"
        )


def get_active_listings(
    oauth_token: str,
    site_id: int = 77,
    entries_per_page: int = 200,
) -> List[Dict[str, str]]:
    """Fetch all active eBay listings."""
    results: List[Dict[str, str]] = []
    page = 1

    while True:
        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{oauth_token}</eBayAuthToken>
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
        raw = post_trading("GetMyeBaySelling", oauth_token, xml_body, site_id=site_id)
        root = ET.fromstring(raw)
        ensure_success(root, "GetMyeBaySelling", raw)

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

        total_pages_text = root.findtext(
            ".//e:ActiveList/e:PaginationResult/e:TotalNumberOfPages",
            default="1",
            namespaces=NS,
        )
        try:
            total_pages = int(total_pages_text)
        except ValueError:
            total_pages = 1

        if page >= total_pages:
            break
        page += 1

    return results


def load_cached_listings() -> Optional[List[Dict[str, str]]]:
    """Load cached eBay listings if fresh."""
    if not CACHE_FILE.exists():
        return None
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        cached_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
        if datetime.now() - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
            return cache.get('data')
    except Exception as e:
        print(f"Cache load error: {e}")
    
    return None


def save_listings_cache(listings: List[Dict[str, str]]):
    """Save listings to cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    cache = {
        'timestamp': datetime.now().isoformat(),
        'data': listings
    }
    
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_sku_listing_counts(oauth_token: Optional[str] = None, use_cache: bool = True) -> Dict[str, int]:
    """
    Get count of eBay listings per SKU.
    
    Args:
        oauth_token: eBay OAuth token. If None, reads from EBAY_TOKEN or EBAY_ACCESS_TOKEN env var.
        use_cache: Whether to use cached data (default: True)
    
    Returns:
        Dict mapping SKU -> count of active listings
    """
    # Get token from env if not provided
    if not oauth_token:
        oauth_token = os.getenv('EBAY_TOKEN') or os.getenv('EBAY_ACCESS_TOKEN')
    
    if not oauth_token:
        raise ValueError("EBAY_TOKEN or EBAY_ACCESS_TOKEN not found in environment variables or provided as argument")
    
    # Try cache first
    if use_cache:
        cached = load_cached_listings()
        if cached is not None:
            print(f"✓ Using cached eBay data ({len(cached)} listings)")
            listings = cached
        else:
            print("⏳ Fetching fresh eBay data...")
            listings = get_active_listings(oauth_token)
            save_listings_cache(listings)
            print(f"✓ Fetched {len(listings)} listings from eBay")
    else:
        print("⏳ Fetching fresh eBay data (cache bypassed)...")
        listings = get_active_listings(oauth_token)
        save_listings_cache(listings)
        print(f"✓ Fetched {len(listings)} listings from eBay")
    
    # Count SKUs (handle combined SKUs separated by ", ")
    sku_counts: Dict[str, int] = {}
    for listing in listings:
        sku = listing.get('sku', '').strip()
        if sku:  # Only count if SKU exists
            # Split by ", " to handle combined SKUs
            individual_skus = [s.strip() for s in sku.split(',')]
            for individual_sku in individual_skus:
                if individual_sku:  # Only count non-empty SKUs
                    sku_counts[individual_sku] = sku_counts.get(individual_sku, 0) + 1
    
    return sku_counts


def clear_cache():
    """Clear the eBay listings cache."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("✓ eBay cache cleared")


if __name__ == "__main__":
    """Test the eBay listings fetcher."""
    try:
        counts = get_sku_listing_counts(use_cache=False)
        print(f"\n{'='*60}")
        print(f"SKU Listing Counts (Total: {len(counts)} SKUs)")
        print(f"{'='*60}")
        
        # Sort by count descending
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        for sku, count in sorted_counts[:20]:  # Show top 20
            print(f"{sku:30s} : {count:3d} listing(s)")
        
        if len(sorted_counts) > 20:
            print(f"\n... and {len(sorted_counts) - 20} more SKUs")
        
        print(f"\n{'='*60}")
        print(f"Total listings: {sum(counts.values())}")
        print(f"Unique SKUs: {len(counts)}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

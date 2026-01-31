"""eBay listings computation service with progress tracking."""
import os
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Generator

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}


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


def ensure_success(root: ET.Element, call_name: str) -> None:
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


def fetch_ebay_listings(oauth_token: str) -> Generator[Dict, None, None]:
    """
    Fetch all active eBay listings with progress updates.
    
    Yields:
        Progress dicts with keys: status, page, total_pages, count, listings (on complete)
    """
    site_id = 77  # Germany
    entries_per_page = 200
    page = 1
    all_listings = []
    
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
        ensure_success(root, "GetMyeBaySelling")
        
        items = root.findall(".//e:ActiveList/e:ItemArray/e:Item", namespaces=NS)
        
        for item in items:
            item_id = (item.findtext("e:ItemID", default="", namespaces=NS) or "").strip()
            sku = (item.findtext("e:SKU", default="", namespaces=NS) or "").strip()
            title = (item.findtext("e:Title", default="", namespaces=NS) or "").strip()
            marketplace = (item.findtext("e:Site", default="", namespaces=NS) or "").strip()
            view_url = (item.findtext("e:ListingDetails/e:ViewItemURL", default="", namespaces=NS) or "").strip()
            
            all_listings.append({
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
        
        # Yield progress
        yield {
            "status": "progress",
            "page": page,
            "total_pages": total_pages,
            "count": len(all_listings)
        }
        
        if page >= total_pages:
            break
        page += 1
    
    # Yield completion
    yield {
        "status": "complete",
        "total_pages": page,
        "count": len(all_listings),
        "listings": all_listings
    }


def compute_ebay_listings() -> Generator[Dict, None, None]:
    """
    Compute eBay listings and yield progress updates.
    
    Yields:
        Progress dicts with SSE-compatible format
    """
    from datetime import datetime
    from . import ebay_listings_cache
    
    # Get OAuth token from environment
    oauth_token = os.getenv('EBAY_ACCESS_TOKEN')
    if not oauth_token:
        yield {
            "status": "error",
            "message": "EBAY_ACCESS_TOKEN not found in environment variables",
            "timestamp": datetime.now().isoformat()
        }
        return
    
    try:
        for progress in fetch_ebay_listings(oauth_token):
            if progress['status'] == 'progress':
                # Yield progress update
                yield {
                    "status": "progress",
                    "page": progress['page'],
                    "total_pages": progress['total_pages'],
                    "count": progress['count'],
                    "timestamp": datetime.now().isoformat()
                }
            elif progress['status'] == 'complete':
                # Save to cache
                listings = progress['listings']
                ebay_listings_cache.write_cache(listings)
                
                # Yield completion
                yield {
                    "status": "complete",
                    "total_pages": progress['total_pages'],
                    "count": progress['count'],
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        yield {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

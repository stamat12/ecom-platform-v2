"""eBay listings computation service with progress tracking."""
import logging
import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Generator, Any, List
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.ebay_profit_calculator import calculate_listing_profit, _get_marketplace_shipping_cost

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}
logger = logging.getLogger(__name__)
MAX_PARALLEL_DETAIL_LOOKUPS = 10  # Process 10 items in parallel


def _setup_file_logging() -> None:
    """Configure file logging for fetch eBay listings flow."""
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ebay_listings_fetch.log"

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", "") == str(log_path):
            return

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)


_setup_file_logging()


def _clean_text(value: str) -> str:
    return (value or "").strip()


def _parse_int(value: str) -> int | None:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return None


def _parse_float(value: str) -> float | None:
    try:
        return float((value or "").strip())
    except (TypeError, ValueError):
        return None


def _parse_bool(value: str) -> bool | None:
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


def _extract_item_payload(item: ET.Element) -> Dict[str, Any]:
    item_id = _clean_text(item.findtext("e:ItemID", default="", namespaces=NS))
    sku = _clean_text(item.findtext("e:SKU", default="", namespaces=NS))
    title = _clean_text(item.findtext("e:Title", default="", namespaces=NS))
    site = _clean_text(item.findtext("e:Site", default="", namespaces=NS))
    view_url = _clean_text(item.findtext("e:ListingDetails/e:ViewItemURL", default="", namespaces=NS))

    current_price_value = _clean_text(item.findtext("e:SellingStatus/e:CurrentPrice", default="", namespaces=NS))
    current_price_currency = _clean_text(
        item.find("e:SellingStatus/e:CurrentPrice", namespaces=NS).attrib.get("currencyID", "")
        if item.find("e:SellingStatus/e:CurrentPrice", namespaces=NS) is not None
        else ""
    )

    picture_urls: List[str] = [
        _clean_text(node.text or "")
        for node in item.findall("e:PictureDetails/e:PictureURL", namespaces=NS)
        if _clean_text(node.text or "")
    ]
    primary_image_url = _clean_text(item.findtext("e:PictureDetails/e:GalleryURL", default="", namespaces=NS))
    if not primary_image_url and picture_urls:
        primary_image_url = picture_urls[0]
    if primary_image_url and not picture_urls:
        picture_urls = [primary_image_url]

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


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _needs_detail_lookup(payload: Dict[str, Any]) -> bool:
    fields_to_check = [
        "image_urls",
        "listing_status",
        "category_id",
        "condition_id",
        "quantity_available",
        "quantity_sold",
    ]
    return any(_is_missing(payload.get(field)) for field in fields_to_check)


def _fetch_item_details(oauth_token: str, item_id: str, site_id: int = 77) -> Dict[str, Any]:
    """Fetch full item details using GetItem and return normalized payload."""
    logger.debug("[DETAIL] Building GetItem request for item_id=%s", item_id)
    xml_body = f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<GetItemRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">
  <RequesterCredentials>
    <eBayAuthToken>{oauth_token}</eBayAuthToken>
  </RequesterCredentials>
  <ItemID>{item_id}</ItemID>
  <IncludeItemSpecifics>true</IncludeItemSpecifics>
  <DetailLevel>ReturnAll</DetailLevel>
</GetItemRequest>
"""
    logger.debug("[DETAIL] Calling post_trading GetItem for item_id=%s...", item_id)
    raw = post_trading("GetItem", oauth_token, xml_body, site_id=site_id)
    logger.debug("[DETAIL] GetItem response received for item_id=%s, parsing...", item_id)
    root = ET.fromstring(raw)
    ensure_success(root, "GetItem")
    item_node = root.find(".//e:Item", namespaces=NS)
    if item_node is None:
        return {}
    return _extract_item_payload(item_node)


def _merge_missing_fields(base: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, detail_value in details.items():
        if _is_missing(merged.get(key)) and not _is_missing(detail_value):
            merged[key] = detail_value
    if merged.get("primary_image_url") and _is_missing(merged.get("image_urls")):
        merged["image_urls"] = [merged["primary_image_url"]]
    return merged


def _listing_cache_key(payload: Dict[str, Any]) -> str:
    item_id = str(payload.get("item_id") or "").strip()
    if item_id:
        return f"item:{item_id}"
    sku = str(payload.get("sku") or "").strip()
    marketplace = str(payload.get("marketplace") or "").strip().upper()
    return f"sku:{sku}|m:{marketplace}"


def _merge_preserve_existing_when_missing(new_payload: Dict[str, Any], existing_payload: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(new_payload)

    for key, existing_value in (existing_payload or {}).items():
        new_value = merged.get(key)

        if isinstance(new_value, dict) and isinstance(existing_value, dict):
            nested = dict(new_value)
            for nested_key, nested_existing in existing_value.items():
                if _is_missing(nested.get(nested_key)) and not _is_missing(nested_existing):
                    nested[nested_key] = nested_existing
            merged[key] = nested
            continue

        if _is_missing(new_value) and not _is_missing(existing_value):
            merged[key] = existing_value

    return merged


def _merge_fast_with_existing_cache(fast_listings: List[Dict[str, Any]], existing_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    existing_index: Dict[str, Dict[str, Any]] = {}
    for existing in (existing_listings or []):
        key = _listing_cache_key(existing)
        if key:
            existing_index[key] = existing

    merged_listings: List[Dict[str, Any]] = []
    for listing in (fast_listings or []):
        existing = existing_index.get(_listing_cache_key(listing))
        if existing:
            merged_listings.append(_merge_preserve_existing_when_missing(listing, existing))
        else:
            merged_listings.append(listing)

    return merged_listings


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
    logger.debug("[API] %s request starting (site_id=%s, timeout=30s)...", call_name, site_id)
    try:
        r = requests.post(TRADING_ENDPOINT, data=xml_body.encode("utf-8"), headers=headers, timeout=30)
        logger.debug("[API] %s response received (status=%s, length=%s)", call_name, r.status_code, len(r.text))
        r.raise_for_status()
        return r.text
    except requests.Timeout:
        logger.error("[API] %s timed out after 30s", call_name)
        raise
    except requests.RequestException as e:
        logger.error("[API] %s request failed: %s", call_name, e)
        raise


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


def fetch_ebay_listings_fast(oauth_token: str) -> Generator[Dict, None, None]:
    """
    Fast fetch - only GetMyeBaySelling data, no detail lookups.
    
    Yields:
        Progress dicts with keys: status, page, total_pages, count, listings (on complete)
    """
    site_id = 77  # Germany
    entries_per_page = 200
    page = 1
    all_listings = []
    logger.info(
        "[FAST-FETCH] Start GetMyeBaySelling: site_id=%s, entries_per_page=%s",
        site_id,
        entries_per_page,
    )
    
    while True:
        logger.info("[FETCH] Preparing GetMyeBaySelling request: page=%s", page)
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
        logger.info("[FETCH] Calling post_trading for page %s...", page)
        try:
            raw = post_trading("GetMyeBaySelling", oauth_token, xml_body, site_id=site_id)
            logger.info("[FETCH] Received response for page %s, parsing XML...", page)
        except Exception as api_err:
            logger.error("[FETCH] post_trading failed for page %s: %s", page, api_err, exc_info=True)
            raise
        
        root = ET.fromstring(raw)
        ensure_success(root, "GetMyeBaySelling")
        
        items = root.findall(".//e:ActiveList/e:ItemArray/e:Item", namespaces=NS)
        
        logger.info("[FAST-FETCH] Processing %s items from page %s (no detail lookups)...", len(items), page)
        for item in items:
            payload = _extract_item_payload(item)
            all_listings.append(payload)
        
        total_pages_text = root.findtext(
            ".//e:ActiveList/e:PaginationResult/e:TotalNumberOfPages",
            default="1",
            namespaces=NS,
        )
        try:
            total_pages = int(total_pages_text)
        except ValueError:
            total_pages = 1

        logger.info(
            "[FAST-FETCH] Page %s/%s processed, page_items=%s, accumulated=%s",
            page,
            total_pages,
            len(items),
            len(all_listings),
        )
        
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
    logger.info(
        "[FAST-FETCH] Completed: total_pages=%s, total_listings=%s",
        page,
        len(all_listings),
    )
    yield {
        "status": "complete",
        "total_pages": page,
        "count": len(all_listings),
        "listings": all_listings
    }


def fetch_ebay_listings_detailed(oauth_token: str) -> Generator[Dict, None, None]:
    """
    Detailed fetch - GetMyeBaySelling + parallel GetItem detail lookups for missing fields.
    
    Yields:
        Progress dicts with keys: status, page, total_pages, count, detail_lookups, listings (on complete)
    """
    site_id = 77  # Germany
    entries_per_page = 200
    page = 1
    all_listings = []
    total_detail_lookups = 0
    logger.info(
        "[DETAILED-FETCH] Start GetMyeBaySelling with parallel detail lookups: site_id=%s, entries_per_page=%s, parallel=%s",
        site_id,
        entries_per_page,
        MAX_PARALLEL_DETAIL_LOOKUPS,
    )
    
    while True:
        logger.info("[DETAILED-FETCH] Preparing GetMyeBaySelling request: page=%s", page)
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
        logger.info("[DETAILED-FETCH] Calling post_trading for page %s...", page)
        try:
            raw = post_trading("GetMyeBaySelling", oauth_token, xml_body, site_id=site_id)
            logger.info("[DETAILED-FETCH] Received response for page %s, parsing XML...", page)
        except Exception as api_err:
            logger.error("[DETAILED-FETCH] post_trading failed for page %s: %s", page, api_err, exc_info=True)
            raise
        
        root = ET.fromstring(raw)
        ensure_success(root, "GetMyeBaySelling")
        
        items = root.findall(".//e:ActiveList/e:ItemArray/e:Item", namespaces=NS)
        
        # Extract base payloads
        logger.info("[DETAILED-FETCH] Processing %s items from page %s...", len(items), page)
        page_payloads = []
        items_needing_details = []
        
        for item in items:
            payload = _extract_item_payload(item)
            item_id = payload.get("item_id", "")
            
            if item_id and _needs_detail_lookup(payload):
                items_needing_details.append((item_id, payload))
            
            page_payloads.append(payload)
        
        # Parallel detail lookups for this page
        if items_needing_details:
            logger.info(
                "[DETAILED-FETCH] Starting parallel detail lookups for %s items (page %s)...",
                len(items_needing_details),
                page,
            )
            
            def fetch_detail(item_data):
                item_id, payload = item_data
                try:
                    details = _fetch_item_details(oauth_token, item_id, site_id=site_id)
                    return (item_id, _merge_missing_fields(payload, details), None)
                except Exception as e:
                    return (item_id, payload, str(e))
            
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DETAIL_LOOKUPS) as executor:
                futures = {executor.submit(fetch_detail, item_data): item_data[0] for item_data in items_needing_details}
                
                for future in as_completed(futures):
                    item_id, enriched_payload, error = future.result()
                    if error:
                        logger.warning("[DETAILED-FETCH] Detail lookup failed for %s: %s", item_id, error)
                    else:
                        total_detail_lookups += 1
                        # Update the payload in page_payloads
                        for i, p in enumerate(page_payloads):
                            if p.get("item_id") == item_id:
                                page_payloads[i] = enriched_payload
                                break
            
            logger.info(
                "[DETAILED-FETCH] Completed %s detail lookups for page %s",
                len(items_needing_details),
                page,
            )
        
        all_listings.extend(page_payloads)
        
        total_pages_text = root.findtext(
            ".//e:ActiveList/e:PaginationResult/e:TotalNumberOfPages",
            default="1",
            namespaces=NS,
        )
        try:
            total_pages = int(total_pages_text)
        except ValueError:
            total_pages = 1

        logger.info(
            "[DETAILED-FETCH] Page %s/%s processed, page_items=%s, accumulated=%s, total_detail_lookups=%s",
            page,
            total_pages,
            len(items),
            len(all_listings),
            total_detail_lookups,
        )
        
        # Yield progress
        yield {
            "status": "progress",
            "page": page,
            "total_pages": total_pages,
            "count": len(all_listings),
            "detail_lookups": total_detail_lookups
        }
        
        if page >= total_pages:
            break
        page += 1
    
    # Yield completion
    logger.info(
        "[DETAILED-FETCH] Completed: total_pages=%s, total_listings=%s, total_detail_lookups=%s",
        page,
        len(all_listings),
        total_detail_lookups,
    )
    yield {
        "status": "complete",
        "total_pages": page,
        "count": len(all_listings),
        "detail_lookups": total_detail_lookups,
        "listings": all_listings
    }


def _enrich_listings_with_profit(listings: list) -> list:
    """
    Enrich listings with profit calculations.
    
    For each listing, calculates:
    - selling_price_netto
    - payment_fee
    - sales_commission
    - shipping_costs_net
    - net_profit
    - net_profit_margin_percent
    
    Note: Profit calculations use inventory Total Cost Net when SKU exists.
    """
    for listing in listings:
        try:
            # Calculate profit with minimal data from eBay API
            profit_analysis = calculate_listing_profit(
                listing,
                category_fees=None,  # Would need to look up from category_id
                total_cost_net=None,
                lookup_total_cost_net=True
            )
            listing['profit_analysis'] = profit_analysis
            logger.debug("[PROFIT] Calculated for item_id=%s: profit=€%s, margin=%s%%",
                        listing.get('item_id'),
                        profit_analysis['net_profit'],
                        profit_analysis['net_profit_margin_percent'])
        except Exception as e:
            logger.warning("[PROFIT] Failed to calculate profit for item_id=%s: %s",
                          listing.get('item_id'), e)
            # Add empty profit data
            listing['profit_analysis'] = {
                'selling_price_brutto': listing.get('price', 0.0),
                'selling_price_netto': 0.0,
                'payment_fee': 0.0,
                'sales_commission': 0.0,
                'sales_commission_percentage': 0.0,
                'shipping_costs_net': 0.0,
                'total_cost_net': 0.0,
                'net_profit': 0.0,
                'net_profit_margin_percent': 0.0
            }
    
    return listings


def compute_ebay_listings_fast() -> Generator[Dict, None, None]:
    """
    Fast compute - eBay listings without detail lookups.
    
    Yields:
        Progress dicts with SSE-compatible format
    """
    from datetime import datetime
    from . import ebay_listings_cache
    
    # Get OAuth token (auto-refresh)
    try:
        from app.services.ebay_oauth import get_access_token
        oauth_token = get_access_token()
        logger.info("[SSE-FAST] Fast Fetch eBay Listings button triggered - OAuth token acquired")
    except Exception as e:
        logger.exception("[SSE-FAST] Failed to acquire OAuth token for eBay listings fetch")
        yield {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return
    
    try:
        for progress in fetch_ebay_listings_fast(oauth_token):
            if progress['status'] == 'progress':
                logger.info(
                    "[SSE-FAST] Progress page=%s/%s count=%s",
                    progress['page'],
                    progress['total_pages'],
                    progress['count'],
                )
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
                existing_cache = ebay_listings_cache.read_cache() or {}
                existing_listings = existing_cache.get("listings", []) or []
                listings = _merge_fast_with_existing_cache(listings, existing_listings)
                # Enrich with profit calculations
                listings = _enrich_listings_with_profit(listings)
                ebay_listings_cache.write_cache(listings)
                logger.info("[SSE-FAST] Cache updated successfully: listings=%s with profit analysis", len(listings))
                
                # Yield completion
                yield {
                    "status": "complete",
                    "total_pages": progress['total_pages'],
                    "count": progress['count'],
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        logger.exception("[SSE-FAST] Fast Fetch eBay Listings failed")
        yield {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


def compute_ebay_listings_detailed() -> Generator[Dict, None, None]:
    """
    Detailed compute - eBay listings with parallel detail lookups.
    
    Yields:
        Progress dicts with SSE-compatible format
    """
    from datetime import datetime
    from . import ebay_listings_cache
    
    # Get OAuth token (auto-refresh)
    try:
        from app.services.ebay_oauth import get_access_token
        oauth_token = get_access_token()
        logger.info("[SSE-DETAILED] Detailed Fetch eBay Listings button triggered - OAuth token acquired")
    except Exception as e:
        logger.exception("[SSE-DETAILED] Failed to acquire OAuth token for eBay listings fetch")
        yield {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return
    
    try:
        for progress in fetch_ebay_listings_detailed(oauth_token):
            if progress['status'] == 'progress':
                logger.info(
                    "[SSE-DETAILED] Progress page=%s/%s count=%s detail_lookups=%s",
                    progress['page'],
                    progress['total_pages'],
                    progress['count'],
                    progress.get('detail_lookups', 0),
                )
                # Yield progress update
                yield {
                    "status": "progress",
                    "page": progress['page'],
                    "total_pages": progress['total_pages'],
                    "count": progress['count'],
                    "detail_lookups": progress.get('detail_lookups', 0),
                    "timestamp": datetime.now().isoformat()
                }
            elif progress['status'] == 'complete':
                # Save to cache
                listings = progress['listings']
                # Enrich with profit calculations
                listings = _enrich_listings_with_profit(listings)
                ebay_listings_cache.write_cache(listings)
                logger.info(
                    "[SSE-DETAILED] Cache updated successfully: listings=%s with profit analysis, detail_lookups=%s",
                    len(listings),
                    progress.get('detail_lookups', 0),
                )
                
                # Yield completion
                yield {
                    "status": "complete",
                    "total_pages": progress['total_pages'],
                    "count": progress['count'],
                    "detail_lookups": progress.get('detail_lookups', 0),
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        logger.exception("[SSE-DETAILED] Detailed Fetch eBay Listings failed")
        yield {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

#!/usr/bin/env python
"""
One-time fix script:
  1. Renames listing_type "Chinese" → "Auction" in the eBay listings cache.
  2. Adds profit_analysis to any Auction listings that are missing it,
     using the same calculation logic as the rest of the cache.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "legacy"))

from app.services.ebay_profit_calculator import calculate_listing_profit  # noqa: E402

CACHE_FILE = backend_dir / "legacy" / "products" / "cache" / "ebay_listings_cache.json"


def main():
    print("=" * 60)
    print("Fix Auction listings in eBay cache")
    print("=" * 60)

    if not CACHE_FILE.exists():
        print(f"❌  Cache file not found: {CACHE_FILE}")
        return

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

    listings = cache.get("listings", [])
    print(f"\n📖  Total listings in cache: {len(listings)}")

    renamed = 0
    enriched = 0
    errors = 0

    for listing in listings:
        # ── Step 1: rename Chinese → Auction ────────────────────────────
        if listing.get("listing_type") == "Chinese":
            listing["listing_type"] = "Auction"
            renamed += 1

        # ── Step 2: compute missing profit_analysis for Auction listings ─
        if listing.get("listing_type") == "Auction" and not listing.get("profit_analysis"):
            try:
                pa = calculate_listing_profit(
                    listing,
                    category_fees=None,
                    total_cost_net=None,
                    lookup_total_cost_net=True,
                )
                listing["profit_analysis"] = pa
                enriched += 1
            except Exception as exc:
                errors += 1
                print(
                    f"  ⚠️  Profit calc failed for item_id={listing.get('item_id')} "
                    f"sku={listing.get('sku')}: {exc}"
                )

    print(f"\n✅  Renamed Chinese → Auction: {renamed}")
    print(f"✅  Profit analysis added:     {enriched}")
    if errors:
        print(f"⚠️   Errors:                    {errors}")

    cache["listings"] = listings
    cache["timestamp"] = datetime.now().isoformat()

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"\n💾  Cache saved → {CACHE_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Enriches existing eBay listings cache with profit calculations.

Run this to add profit analysis to all listings in the cache file.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent / "legacy"))

from app.services.ebay_profit_calculator import calculate_listing_profit

# Direct path to cache file
CACHE_FILE = backend_dir / "legacy" / "products" / "cache" / "ebay_listings_cache.json"


def read_cache():
    """Read cache file."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading cache: {e}")
        return None


def write_cache(cache_data):
    """Write cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing cache: {e}")
        return False


def main():
    print("=" * 60)
    print("eBay Listings Profit Enrichment")
    print("=" * 60)
    
    # Read existing cache
    print("\n📖 Reading existing cache...")
    cache = read_cache()
    
    if cache is None:
        print(f"   ❌ Cache file not found: {CACHE_FILE}")
        return
    
    listings = cache.get('listings', [])
    total = len(listings)
    print(f"   Found {total} listings in cache")
    
    if total == 0:
        print("   ❌ Cache is empty, nothing to enrich")
        return
    
    # Enrich with profit calculations
    print("\n💰 Calculating profit for each listing...")
    enriched_count = 0
    error_count = 0
    
    for idx, listing in enumerate(listings, 1):
        try:
            profit_analysis = calculate_listing_profit(
                listing,
                category_fees=None,
                total_cost_net=None,
                lookup_total_cost_net=True
            )
            listing['profit_analysis'] = profit_analysis
            enriched_count += 1
            
            if idx % 100 == 0:
                print(f"   Processed {idx}/{total} listings...")
        except Exception as e:
            error_count += 1
            listing['profit_analysis'] = {
                'error': str(e)
            }
            print(f"   ⚠️  Warning: Failed for item_id={listing.get('item_id')}: {e}")
    
    print(f"   ✅ Profit calculated for {enriched_count}/{total} listings")
    if error_count > 0:
        print(f"   ⚠️  Errors: {error_count} listings")
    
    # Save enriched cache
    print("\n💾 Saving enriched cache...")
    cache['listings'] = listings
    cache['timestamp'] = datetime.now().isoformat()
    
    if write_cache(cache):
        print(f"   ✅ Cache saved with profit analysis")
    else:
        print("   ❌ Failed to save cache")
        return
    
    # Show sample
    if listings:
        sample = listings[0]
        print("\n📊 Sample listing with profit data:")
        print(f"   Item ID: {sample.get('item_id')}")
        print(f"   SKU: {sample.get('sku')}")
        print(f"   Price: €{sample.get('price')}")
        if 'profit_analysis' in sample:
            pa = sample['profit_analysis']
            if 'error' not in pa:
                print(f"   Profit Analysis:")
                print(f"     - Price (netto): €{pa.get('selling_price_netto', 0.0):.2f}")
                print(f"     - Commission: €{pa.get('sales_commission', 0.0):.2f} ({pa.get('sales_commission_percentage', 0.0)*100:.1f}%)")
                print(f"     - Payment Fee: €{pa.get('payment_fee', 0.0):.2f}")
                print(f"     - Shipping (net): €{pa.get('shipping_costs_net', 0.0):.2f}")
                print(f"     - Net Profit: €{pa.get('net_profit', 0.0):.2f}")
                print(f"     - Margin: {pa.get('net_profit_margin_percent', 0.0):.2f}%")
    
    print("\n" + "=" * 60)
    print("✅ Done! Cache enriched with profit calculations")
    print("=" * 60)


if __name__ == "__main__":
    main()

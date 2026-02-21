#!/usr/bin/env python
"""Export eBay listings cache JSON to an Excel file in the same folder."""
import json
from pathlib import Path

import pandas as pd


def _load_cache(cache_path: Path) -> dict:
    with cache_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _flatten_listings(cache_data: dict) -> pd.DataFrame:
    listings = cache_data.get("listings", [])
    # Flatten nested fields like profit_analysis into columns.
    return pd.json_normalize(listings, sep=".")


def main() -> None:
    cache_path = Path(__file__).resolve().parents[1] / "legacy" / "products" / "cache" / "ebay_listings_cache.json"
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache file not found: {cache_path}")

    cache_data = _load_cache(cache_path)
    df = _flatten_listings(cache_data)

    output_path = cache_path.with_suffix("")
    output_path = output_path.parent / "ebay_listings_cache.xlsx"

    df.to_excel(output_path, index=False)
    print(f"Exported {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()

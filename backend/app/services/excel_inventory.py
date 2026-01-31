from __future__ import annotations
import os
import time
from typing import Optional
import json

import pandas as pd
from dotenv import load_dotenv

# Load backend/.env
load_dotenv()

import sys
from pathlib import Path
LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore

from app.repositories.sku_json_repo import _sku_json_path


def _get_inventory_path() -> str:
    # Env override wins (recommended)
    p = os.getenv("INVENTORY_FILE_PATH")
    if p:
        return p
    # Fallback to legacy config (may be wrong depending on PROJECT_ROOT assumptions)
    return str(getattr(config, "INVENTORY_FILE_PATH"))


def _get_inventory_sheet() -> str | int:
    return os.getenv("INVENTORY_SHEET_NAME") or getattr(config, "INVENTORY_SHEET_NAME", 0)


class ExcelInventoryCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl_seconds = ttl_seconds
        self._df: Optional[pd.DataFrame] = None
        self._loaded_at: float = 0.0

    def load(self) -> pd.DataFrame:
        now = time.time()
        if self._df is not None and (now - self._loaded_at) < self.ttl_seconds:
            return self._df

        df = pd.read_excel(
            _get_inventory_path(),
            sheet_name=_get_inventory_sheet(),
        )

        # Add computed "Json" column that checks if JSON file exists for each SKU
        def has_json(sku):
            if pd.isna(sku) or str(sku).strip() == "":
                return False
            try:
                return _sku_json_path(str(sku)).exists()
            except:
                return False
        
        # Add computed image count columns from JSON files
        def get_image_counts(sku):
            if pd.isna(sku) or str(sku).strip() == "":
                return None, None, None
            try:
                path = _sku_json_path(str(sku))
                if not path.exists():
                    return None, None, None
                
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract SKU data (JSON structure is {SKU: {...}})
                sku_str = str(sku)
                sku_data = data.get(sku_str, {})
                
                # Get image summary
                images = sku_data.get("Images", {})
                summary = images.get("summary", {})
                
                return (
                    summary.get("count_stock", 0),
                    summary.get("count_phone", 0),
                    summary.get("count_enhanced", 0)
                )
            except:
                return None, None, None
        
        # Use "SKU (Old)" column for the SKU value
        if "SKU (Old)" in df.columns:
            df["Json"] = df["SKU (Old)"].apply(has_json)
            # Add image count columns
            image_counts = df["SKU (Old)"].apply(get_image_counts)
            df["Json Stock Images"] = image_counts.apply(lambda x: x[0] if x and x[0] is not None else None)
            df["Json Phone Images"] = image_counts.apply(lambda x: x[1] if x and x[1] is not None else None)
            df["Json Enhanced Images"] = image_counts.apply(lambda x: x[2] if x and x[2] is not None else None)
        elif "SKU" in df.columns:
            df["Json"] = df["SKU"].apply(has_json)
            # Add image count columns
            image_counts = df["SKU"].apply(get_image_counts)
            df["Json Stock Images"] = image_counts.apply(lambda x: x[0] if x and x[0] is not None else None)
            df["Json Phone Images"] = image_counts.apply(lambda x: x[1] if x and x[1] is not None else None)
            df["Json Enhanced Images"] = image_counts.apply(lambda x: x[2] if x and x[2] is not None else None)

        self._df = df
        self._loaded_at = now
        return df

    def invalidate(self) -> None:
        self._df = None


excel_inventory = ExcelInventoryCache()


def load_inventory_dataframe() -> pd.DataFrame:
    """Load inventory dataframe (with caching)"""
    return excel_inventory.load()

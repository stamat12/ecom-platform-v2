from __future__ import annotations
import os
import time
from typing import Optional

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
        
        # Use "SKU (Old)" column for the SKU value
        if "SKU (Old)" in df.columns:
            df["Json"] = df["SKU (Old)"].apply(has_json)
        elif "SKU" in df.columns:
            df["Json"] = df["SKU"].apply(has_json)

        self._df = df
        self._loaded_at = now
        return df

    def invalidate(self) -> None:
        self._df = None


excel_inventory = ExcelInventoryCache()


def load_inventory_dataframe() -> pd.DataFrame:
    """Load inventory dataframe (with caching)"""
    return excel_inventory.load()

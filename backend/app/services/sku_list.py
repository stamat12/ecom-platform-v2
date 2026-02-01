from __future__ import annotations
from typing import Dict, Any, List
import os
from pathlib import Path

from app.services.excel_inventory import excel_inventory
from app.services.folder_images_cache import get_folder_image_count
from app.services.ebay_listings_cache import get_sku_has_listing
import config  # type: ignore
import pandas as pd

# Operators by type
STRING_OPS = ["contains", "equals", "starts_with", "ends_with"]
NUM_DATE_OPS = ["equals", "lt", "lte", "gt", "gte", "between"]
BOOL_OPS = ["is_true", "is_false"]
ENUM_OPS = ["equals", "in", "not_in"]


def get_available_columns() -> List[str]:
    """Get all available columns from the inventory, excluding internal/metadata columns"""
    df = excel_inventory.load()
    cols = list(df.columns)
    # Remove internal/metadata columns that shouldn't be displayed
    excluded = [
        "BGN Price",
        "BG Marketplace",
        "ÖVG",
        "JSON",
        "Images JSON Phone",
        "Images JSON Stock",
        "Images JSON Enhanced",
        "Reference",
        "Sold"
    ]
    available = [col for col in cols if col not in excluded]
    if "Folder Images" not in available:
        available.append("Folder Images")
    if "Ebay Listing" not in available:
        available.append("Ebay Listing")
    return available


def get_default_columns() -> List[str]:
    """Get the default columns to display"""
    # These are the most important columns
    return [
        "SKU (Old)",
        "Json",
        "Brand",
        "Category",
        "Color",
        "Size",
        "Condition",
        "Status",
        "Price Net",
    ]


def _infer_column_type(series: pd.Series) -> str:
    dt = series.dtype
    if pd.api.types.is_bool_dtype(dt):
        return "boolean"
    if pd.api.types.is_numeric_dtype(dt):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(dt):
        return "date"
    # enum heuristic: small unique set on object-like
    unique_count = series.dropna().astype(str).nunique()
    if unique_count > 0 and unique_count <= 30:
        return "enum"
    return "string"


def get_columns_meta() -> List[Dict[str, Any]]:
    df = excel_inventory.load()
    meta: List[Dict[str, Any]] = []
    for col in df.columns:
        s = df[col]
        ctype = _infer_column_type(s)
        
        operators = STRING_OPS
        enum_values = None
        if ctype == "number" or ctype == "date":
            operators = NUM_DATE_OPS
        elif ctype == "boolean":
            operators = BOOL_OPS
        elif ctype == "enum":
            operators = ENUM_OPS
            # capture up to 50 unique values as option suggestions
            enum_values = (
                s.dropna()
                .astype(str)
                .unique()
                .tolist()
            )[:50]
        meta.append({
            "name": col,
            "type": ctype,
            "operators": operators,
            "enum_values": enum_values,
        })
    
    # Add virtual column metadata
    meta.append({
        "name": "Folder Images",
        "type": "number",
        "operators": NUM_DATE_OPS,
        "enum_values": None,
    })
    
    meta.append({
        "name": "Ebay Listing",
        "type": "boolean",
        "operators": BOOL_OPS,
        "enum_values": None,
    })
    
    return meta


def get_distinct_values(column: str, limit: int = 200, q: str | None = None) -> Dict[str, Any]:
    """Return distinct non-empty string values for a column with optional substring filter and limit."""
    df = excel_inventory.load()
    if column not in df.columns:
        return {"column": column, "values": [], "total_unique": 0, "limited": False}
    s = df[column].dropna().astype(str)
    # Remove empty strings
    s = s[s.str.len() > 0]
    if q:
        q_lower = str(q).lower()
        s = s[s.str.lower().str.contains(q_lower, na=False)]
    counts = s.value_counts()
    values = counts.index.tolist()
    total_unique = len(values)
    limited = total_unique > limit
    if limited:
        values = values[:limit]
    return {
        "column": column,
        "values": values,
        "total_unique": total_unique,
        "limited": limited,
    }


def list_skus(
    page: int,
    page_size: int,
    filters: List[Dict[str, Any]] | None = None,
    columns: List[str] | None = None,
) -> Dict[str, Any]:
    """
    List SKUs with column-level filtering support.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        filters: List of filter dicts with keys: column, value, operator
                 operator can be: contains, equals, starts_with, ends_with
        columns: List of columns to return (if None, returns all columns)
    """
    df = excel_inventory.load().copy()

    # Separate Folder Images and Ebay Listing filters for later (virtual columns)
    folder_images_filter = None
    ebay_listing_filter = None
    if filters:
        filters = [f for f in filters]  # copy
        folder_images_filter = next((f for f in filters if f.get("column") == "Folder Images"), None)
        ebay_listing_filter = next((f for f in filters if f.get("column") == "Ebay Listing"), None)
        if folder_images_filter:
            filters = [f for f in filters if f.get("column") != "Folder Images"]
        if ebay_listing_filter:
            filters = [f for f in filters if f.get("column") != "Ebay Listing"]

    # Apply filters
    if filters:
        for filter_item in filters:
            col = filter_item.get("column")
            if not col or col not in df.columns:
                continue

            ftype = filter_item.get("type")
            operator = filter_item.get("operator", "contains")

            # Typed filters
            if ftype in ("number", "date", "boolean", "enum"):
                series = df[col]
                try:
                    if ftype == "number":
                        s = pd.to_numeric(series, errors="coerce")
                        val = filter_item.get("value")
                        val2 = filter_item.get("value2")
                        if operator == "equals" and val is not None:
                            df = df[s == float(val)]
                        elif operator == "lt" and val is not None:
                            df = df[s < float(val)]
                        elif operator == "lte" and val is not None:
                            df = df[s <= float(val)]
                        elif operator == "gt" and val is not None:
                            df = df[s > float(val)]
                        elif operator == "gte" and val is not None:
                            df = df[s >= float(val)]
                        elif operator == "between" and val is not None and val2 is not None:
                            df = df[(s >= float(val)) & (s <= float(val2))]
                    elif ftype == "date":
                        s = pd.to_datetime(series, errors="coerce")
                        val = filter_item.get("value")
                        val2 = filter_item.get("value2")
                        # Accept ISO date strings
                        if operator == "equals" and val:
                            dv = pd.to_datetime(val, errors="coerce")
                            df = df[s.dt.date == dv.date()] if pd.notna(dv) else df
                        elif operator == "lt" and val:
                            dv = pd.to_datetime(val, errors="coerce")
                            df = df[s < dv] if pd.notna(dv) else df
                        elif operator == "lte" and val:
                            dv = pd.to_datetime(val, errors="coerce")
                            df = df[s <= dv] if pd.notna(dv) else df
                        elif operator == "gt" and val:
                            dv = pd.to_datetime(val, errors="coerce")
                            df = df[s > dv] if pd.notna(dv) else df
                        elif operator == "gte" and val:
                            dv = pd.to_datetime(val, errors="coerce")
                            df = df[s >= dv] if pd.notna(dv) else df
                        elif operator == "between" and val and val2:
                            dv1 = pd.to_datetime(val, errors="coerce")
                            dv2 = pd.to_datetime(val2, errors="coerce")
                            if pd.notna(dv1) and pd.notna(dv2):
                                df = df[(s >= dv1) & (s <= dv2)]
                    elif ftype == "boolean":
                        # Consider common string booleans too
                        truthy = {True, "true", "1", 1, "yes"}
                        falsy = {False, "false", "0", 0, "no"}
                        s = series.astype(str).str.lower()
                        if operator == "is_true":
                            df = df[s.isin({"true", "1", "yes"})]
                        elif operator == "is_false":
                            df = df[s.isin({"false", "0", "no"})]
                    elif ftype == "enum":
                        s = series.astype(str)
                        values = filter_item.get("values") or ([] if filter_item.get("value") is None else [filter_item.get("value")])
                        values = [str(v) for v in values]
                        if operator == "equals" and values:
                            df = df[s == values[0]]
                        elif operator == "in" and values:
                            df = df[s.isin(values)]
                        elif operator == "not_in" and values:
                            df = df[~s.isin(values)]
                except Exception:
                    # Ignore faulty filters
                    pass
                continue

            # Typed string filters (and legacy fallback)
            df[col] = df[col].fillna("").astype(str)
            col_lower = df[col].str.lower()
            values_list = filter_item.get("values")
            if operator in ("in", "not_in") and values_list:
                norm = [str(v).lower() for v in values_list]
                mask = col_lower.isin(norm)
                df = df[mask] if operator == "in" else df[~mask]
            else:
                value = str(filter_item.get("value", "")).lower()
                if not value:
                    continue
                if operator == "equals":
                    df = df[col_lower == value]
                elif operator == "starts_with":
                    df = df[col_lower.str.startswith(value)]
                elif operator == "ends_with":
                    df = df[col_lower.str.endswith(value)]
                else:  # contains (default)
                    df = df[col_lower.str.contains(value, na=False)]

    # Capture SKU series before column filtering (needed for Folder Images)
    sku_series = None
    if "SKU (Old)" in df.columns:
        sku_series = df["SKU (Old)"]
    elif "SKU" in df.columns:
        sku_series = df["SKU"]

    # Apply Folder Images filter if present (read from cache)
    if folder_images_filter and sku_series is not None:
        # Read from cache
        def get_cached_count(sku: str | None) -> int | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_folder_image_count(str(sku))
        
        df["_folder_images_temp"] = sku_series.apply(get_cached_count)
        
        # Apply the filter
        ftype = folder_images_filter.get("type", "number")
        operator = folder_images_filter.get("operator", "gte")
        val = folder_images_filter.get("value")
        val2 = folder_images_filter.get("value2")
        
        s = pd.to_numeric(df["_folder_images_temp"], errors="coerce")
        if operator == "equals" and val is not None:
            df = df[s == float(val)]
        elif operator == "lt" and val is not None:
            df = df[s < float(val)]
        elif operator == "lte" and val is not None:
            df = df[s <= float(val)]
        elif operator == "gt" and val is not None:
            df = df[s > float(val)]
        elif operator == "gte" and val is not None:
            df = df[s >= float(val)]
        elif operator == "between" and val is not None and val2 is not None:
            df = df[(s >= float(val)) & (s <= float(val2))]
        
        # Drop temp column
        df = df.drop(columns=["_folder_images_temp"])

    # Apply Ebay Listing filter if present (read from cache)
    if ebay_listing_filter and sku_series is not None:
        # Read from cache
        def get_cached_listing(sku: str | None) -> bool | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_sku_has_listing(str(sku))
        
        df["_ebay_listing_temp"] = sku_series.apply(get_cached_listing)
        
        # Apply the filter
        operator = ebay_listing_filter.get("operator", "is_true")
        
        if operator == "is_true":
            df = df[df["_ebay_listing_temp"] == True]
        elif operator == "is_false":
            df = df[df["_ebay_listing_temp"] == False]
        
        # Drop temp column
        df = df.drop(columns=["_ebay_listing_temp"])

    # Filter by selected columns if provided
    requested_columns = columns if (columns and isinstance(columns, list) and len(columns) > 0) else None
    if requested_columns:
        valid_columns = [col for col in requested_columns if col in df.columns]
        if valid_columns:
            df = df[valid_columns]

    total = len(df)
    start = max(0, (page - 1) * page_size)
    end = start + page_size

    page_df = df.iloc[start:end].copy()

    # Compute Folder Images column (virtual) from cache
    if requested_columns is None or "Folder Images" in requested_columns:
        def get_cached_count(sku: str | None) -> int | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_folder_image_count(str(sku))

        if sku_series is not None:
            page_df["Folder Images"] = sku_series.loc[page_df.index].apply(get_cached_count)

    # Compute Ebay Listing column (virtual) from cache
    if requested_columns is None or "Ebay Listing" in requested_columns:
        def get_cached_listing(sku: str | None) -> bool | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_sku_has_listing(str(sku))

        if sku_series is not None:
            page_df["Ebay Listing"] = sku_series.loc[page_df.index].apply(get_cached_listing)

    # Replace NaN / +/-Inf with None so JSON serialization is safe
    page_df = page_df.replace([float("inf"), float("-inf")], None)
    page_df = page_df.where(page_df.notna(), None)

    # Convert Json and Ebay Listing column boolean values to "TRUE"/"FALSE" strings for display
    for bool_col in ["Json", "Ebay Listing"]:
        if bool_col in page_df.columns:
            page_df[bool_col] = page_df[bool_col].apply(lambda x: "TRUE" if x is True else ("FALSE" if x is False else None))
    
    # Convert image count columns to integers or empty strings
    for col in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images", "Folder Images"]:
        if col in page_df.columns:
            page_df[col] = page_df[col].apply(lambda x: int(x) if pd.notna(x) and x is not None else "")

    items = page_df.to_dict(orient="records")
    if columns is None:
        available_columns = list(df.columns)
        if "Folder Images" not in available_columns:
            available_columns.append("Folder Images")
        if "Ebay Listing" not in available_columns:
            available_columns.append("Ebay Listing")
    else:
        available_columns = columns

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
        "available_columns": available_columns,
    }

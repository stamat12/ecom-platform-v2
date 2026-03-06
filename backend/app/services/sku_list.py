from __future__ import annotations
from typing import Dict, Any, List
import os
from pathlib import Path
import json
import sqlite3
import threading
import time
from functools import lru_cache

from app.services.excel_inventory import excel_inventory
from app.services.folder_images_cache import get_folder_image_count, read_cache as read_folder_images_cache
from app.services.ebay_listings_cache import get_sku_has_listing, read_cache as read_ebay_listings_cache
from app.repositories.sku_json_repo import _sku_json_path
import config  # type: ignore
import pandas as pd

# Operators by type
STRING_OPS = ["contains", "equals", "starts_with", "ends_with"]
NUM_DATE_OPS = ["equals", "lt", "lte", "gt", "gte", "between"]
BOOL_OPS = ["is_true", "is_false"]
ENUM_OPS = ["equals", "in", "not_in"]

VIRTUAL_JSON_COLUMNS = ["Json", "Json Stock Images", "Json Phone Images", "Json Enhanced Images"]
VIRTUAL_CACHE_COLUMNS = ["Folder Images", "Ebay Listing"]
DB_PATH = Path(__file__).resolve().parents[2] / "legacy" / "cache" / "inventory.db"
FAST_TABLE_NAME = "inventory_fast"
_INDEX_INIT_LOCK = threading.Lock()
_INDEX_INIT_DONE = False
_FAST_TABLE_LOCK = threading.Lock()
_FAST_TABLE_LAST_REFRESH = 0.0
_FAST_TABLE_REFRESH_SECONDS = 90.0
_JSON_FILE_SET_LOCK = threading.Lock()
_JSON_FILE_SET: set[str] = set()
_JSON_FILE_SET_LOADED_AT = 0.0
_JSON_FILE_SET_TTL_SECONDS = 120.0


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


@lru_cache(maxsize=1)
def _get_inventory_db_columns() -> tuple[str, ...]:
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute("PRAGMA table_info(inventory)").fetchall()
            return tuple(str(r[1]) for r in rows)
        finally:
            conn.close()
    except Exception:
        return tuple()


def _ensure_sqlite_indexes() -> None:
    global _INDEX_INIT_DONE
    if _INDEX_INIT_DONE:
        return

    with _INDEX_INIT_LOCK:
        if _INDEX_INIT_DONE:
            return

        if not DB_PATH.exists():
            _INDEX_INIT_DONE = True
            return

        db_cols = set(_get_inventory_db_columns())
        if not db_cols:
            _INDEX_INIT_DONE = True
            return

        preferred = [
            "SKU (Old)", "SKU", "Lager", "Status", "Category", "Brand", "Condition", "Size", "Color", "Price Net"
        ]
        to_index = [c for c in preferred if c in db_cols]

        try:
            conn = sqlite3.connect(DB_PATH)
            try:
                for col in to_index:
                    idx = "idx_inventory_" + "".join(ch.lower() if ch.isalnum() else "_" for ch in col).strip("_")
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {_quote_ident(idx)} ON inventory({_quote_ident(col)})")
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

        _INDEX_INIT_DONE = True


def _normalize_sku_token(token: str) -> str:
    return (token or "").strip()


def _expand_sku_range_if_possible(token: str, max_expand: int = 2000) -> list[str]:
    t = _normalize_sku_token(token)
    if not t or "-" not in t:
        return [t] if t else []

    parts = t.split("-")
    if len(parts) != 2:
        return [t]

    start_sku = parts[0].strip()
    end_sku = parts[1].strip()
    if not start_sku or not end_sku:
        return [t]

    start_prefix = ''.join([c for c in start_sku if not c.isdigit()])
    end_prefix = ''.join([c for c in end_sku if not c.isdigit()])
    if start_prefix != end_prefix:
        return [t]

    start_num_str = start_sku[len(start_prefix):]
    end_num_str = end_sku[len(end_prefix):]
    if not start_num_str.isdigit() or not end_num_str.isdigit():
        return [t]

    start_num = int(start_num_str)
    end_num = int(end_num_str)
    if end_num < start_num:
        start_num, end_num = end_num, start_num

    width = max(len(start_num_str), len(end_num_str))
    if (end_num - start_num + 1) > max_expand:
        return [t]

    return [f"{start_prefix}{str(num).zfill(width)}" for num in range(start_num, end_num + 1)]


def _get_ebay_listed_skus_set() -> set[str]:
    cache = read_ebay_listings_cache() or {}
    listings = cache.get("listings", []) or []
    result: set[str] = set()

    for listing in listings:
        listing_sku = str(listing.get("sku") or "").strip()
        if not listing_sku:
            continue
        tokens = [t.strip() for t in listing_sku.split(",") if t.strip()]
        for token in tokens:
            expanded = _expand_sku_range_if_possible(token)
            for sku in expanded:
                if sku:
                    result.add(sku)

    return result


def _ensure_fast_table(refreshed_recently_ok: bool = True) -> None:
    global _FAST_TABLE_LAST_REFRESH
    now = time.time()
    if refreshed_recently_ok and (now - _FAST_TABLE_LAST_REFRESH) < _FAST_TABLE_REFRESH_SECONDS:
        return

    with _FAST_TABLE_LOCK:
        now = time.time()
        if refreshed_recently_ok and (now - _FAST_TABLE_LAST_REFRESH) < _FAST_TABLE_REFRESH_SECONDS:
            return

        if not DB_PATH.exists():
            _FAST_TABLE_LAST_REFRESH = now
            return

        _ensure_sqlite_indexes()
        db_columns_tuple = _get_inventory_db_columns()
        if not db_columns_tuple:
            _FAST_TABLE_LAST_REFRESH = now
            return

        sku_key = "SKU (Old)" if "SKU (Old)" in db_columns_tuple else ("SKU" if "SKU" in db_columns_tuple else None)
        quoted_inv_cols = ", ".join(_quote_ident(c) for c in db_columns_tuple)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(f"DROP TABLE IF EXISTS {_quote_ident(FAST_TABLE_NAME)}")

            existing_cols = set(db_columns_tuple)
            existing_cols_lower = {c.lower() for c in existing_cols}
            create_cols = [f"{_quote_ident(c)} TEXT" for c in db_columns_tuple]
            if "json" not in existing_cols_lower:
                create_cols.append(f"{_quote_ident('Json')} TEXT")
            if "folder images" not in existing_cols_lower:
                create_cols.append(f"{_quote_ident('Folder Images')} INTEGER")
            if "ebay listing" not in existing_cols_lower:
                create_cols.append(f"{_quote_ident('Ebay Listing')} TEXT")
            conn.execute(f"CREATE TABLE {_quote_ident(FAST_TABLE_NAME)} ({', '.join(create_cols)})")

            conn.execute(
                f"INSERT INTO {_quote_ident(FAST_TABLE_NAME)} ({quoted_inv_cols}) "
                f"SELECT {quoted_inv_cols} FROM inventory"
            )

            folder_cache = read_folder_images_cache() or {}
            folder_counts = folder_cache.get("counts", {}) or {}
            json_set = _get_json_file_set()
            ebay_listed_skus = _get_ebay_listed_skus_set()

            if sku_key:
                rows = conn.execute(
                    f"SELECT rowid AS rid, {_quote_ident(sku_key)} AS sku FROM {_quote_ident(FAST_TABLE_NAME)}"
                ).fetchall()
                updates = []
                for r in rows:
                    sku = str(r["sku"] or "").strip()
                    has_json = "TRUE" if sku and sku in json_set else "FALSE"
                    folder_count = folder_counts.get(sku)
                    ebay_listing = "TRUE" if sku and sku in ebay_listed_skus else "FALSE"
                    updates.append((has_json, folder_count, ebay_listing, int(r["rid"])))

                conn.executemany(
                    f"UPDATE {_quote_ident(FAST_TABLE_NAME)} "
                    f"SET {_quote_ident('Json')} = ?, {_quote_ident('Folder Images')} = ?, {_quote_ident('Ebay Listing')} = ? "
                    f"WHERE rowid = ?",
                    updates,
                )

            fast_idx_cols = [c for c in [sku_key, "Lager", "Status", "Category", "Brand", "Ebay Listing", "Json", "Folder Images"] if c]
            for col in fast_idx_cols:
                if col in set(db_columns_tuple) or col in {"Json", "Folder Images", "Ebay Listing"}:
                    idx = "idx_inventory_fast_" + "".join(ch.lower() if ch.isalnum() else "_" for ch in col).strip("_")
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {_quote_ident(idx)} ON {_quote_ident(FAST_TABLE_NAME)}({_quote_ident(col)})")

            conn.commit()
        finally:
            conn.close()

        _get_fast_table_columns_cached.cache_clear()
        _FAST_TABLE_LAST_REFRESH = now


@lru_cache(maxsize=1)
def _get_fast_table_columns_cached(cache_key: int = 0) -> tuple[str, ...]:
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            rows = conn.execute(f"PRAGMA table_info({_quote_ident(FAST_TABLE_NAME)})").fetchall()
            return tuple(str(r[1]) for r in rows)
        finally:
            conn.close()
    except Exception:
        return tuple()


def _get_fast_table_columns() -> tuple[str, ...]:
    _ensure_fast_table(refreshed_recently_ok=True)
    cols = _get_fast_table_columns_cached(0)
    if cols:
        return cols

    _get_fast_table_columns_cached.cache_clear()
    _ensure_fast_table(refreshed_recently_ok=False)
    return _get_fast_table_columns_cached(0)


def _build_sql_where(filters: List[Dict[str, Any]] | None, db_columns: set[str]) -> tuple[str, list[Any]] | None:
    if not filters:
        return "", []

    clauses: list[str] = []
    params: list[Any] = []

    for f in filters:
        col = f.get("column")
        if not col or col not in db_columns:
            return None

        ftype = (f.get("type") or "string").lower()
        op = (f.get("operator") or "contains").lower()
        col_text = f"LOWER(TRIM(COALESCE(CAST({_quote_ident(col)} AS TEXT), '')))"

        if op == "is_empty":
            clauses.append(f"TRIM(COALESCE(CAST({_quote_ident(col)} AS TEXT), '')) = ''")
            continue

        if ftype == "number":
            col_num = f"CAST({_quote_ident(col)} AS REAL)"
            v = f.get("value")
            v2 = f.get("value2")
            if op == "equals" and v is not None:
                clauses.append(f"{col_num} = ?")
                params.append(float(v))
            elif op == "lt" and v is not None:
                clauses.append(f"{col_num} < ?")
                params.append(float(v))
            elif op == "lte" and v is not None:
                clauses.append(f"{col_num} <= ?")
                params.append(float(v))
            elif op == "gt" and v is not None:
                clauses.append(f"{col_num} > ?")
                params.append(float(v))
            elif op == "gte" and v is not None:
                clauses.append(f"{col_num} >= ?")
                params.append(float(v))
            elif op == "between" and v is not None and v2 is not None:
                clauses.append(f"{col_num} BETWEEN ? AND ?")
                params.extend([float(v), float(v2)])
            continue

        if ftype == "boolean":
            if op == "is_true":
                clauses.append(f"{col_text} IN ('true', '1', 'yes')")
            elif op == "is_false":
                clauses.append(f"{col_text} IN ('false', '0', 'no')")
            continue

        values = f.get("values")
        value = f.get("value")

        if op in ("in", "not_in") and isinstance(values, list) and values:
            norm_values = [str(v).strip().lower() for v in values if str(v).strip() != ""]
            if not norm_values:
                continue
            placeholders = ",".join(["?"] * len(norm_values))
            clauses.append(f"{col_text} {'NOT IN' if op == 'not_in' else 'IN'} ({placeholders})")
            params.extend(norm_values)
            continue

        if value is None:
            continue
        v = str(value).strip().lower()
        if not v:
            continue

        if op == "equals":
            clauses.append(f"{col_text} = ?")
            params.append(v)
        elif op == "starts_with":
            clauses.append(f"{col_text} LIKE ?")
            params.append(f"{v}%")
        elif op == "ends_with":
            clauses.append(f"{col_text} LIKE ?")
            params.append(f"%{v}")
        else:  # contains
            clauses.append(f"INSTR({col_text}, ?) > 0")
            params.append(v)

    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params


def _list_skus_sql_fast(
    page: int,
    page_size: int,
    filters: List[Dict[str, Any]] | None,
    columns: List[str] | None,
) -> Dict[str, Any] | None:
    if not DB_PATH.exists():
        return None

    _ensure_fast_table(refreshed_recently_ok=True)

    fast_columns_tuple = _get_fast_table_columns()
    if not fast_columns_tuple:
        return None

    fast_columns = set(fast_columns_tuple)

    # Keep JSON image count columns in fallback (they require per-file JSON parsing)
    json_count_cols = {"Json Stock Images", "Json Phone Images", "Json Enhanced Images"}
    if filters and any((f.get("column") in json_count_cols) for f in filters):
        return None
    if filters and any((f.get("type") == "date") for f in filters):
        return None

    sql_filter = _build_sql_where(filters, fast_columns)
    if sql_filter is None:
        return None
    where_sql, params = sql_filter

    requested_columns = columns if (columns and isinstance(columns, list) and len(columns) > 0) else None
    requested_fast_columns = [c for c in (requested_columns or []) if c in fast_columns]

    # Ensure SKU column is present for virtual per-row enrichments
    sku_key = "SKU (Old)" if "SKU (Old)" in fast_columns else ("SKU" if "SKU" in fast_columns else None)
    selected_cols_for_query = requested_fast_columns[:] if requested_fast_columns else list(fast_columns_tuple)
    if sku_key and sku_key not in selected_cols_for_query:
        selected_cols_for_query.insert(0, sku_key)

    if not selected_cols_for_query:
        return None

    select_sql = ", ".join(_quote_ident(c) for c in selected_cols_for_query)
    order_sql = _quote_ident(sku_key) if sku_key else _quote_ident(selected_cols_for_query[0])
    offset = max(0, (page - 1) * page_size)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM {_quote_ident(FAST_TABLE_NAME)}{where_sql}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT {select_sql} FROM {_quote_ident(FAST_TABLE_NAME)}{where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
            [*params, int(page_size), int(offset)],
        ).fetchall()
    finally:
        conn.close()

    page_df = pd.DataFrame([dict(r) for r in rows])
    if page_df.empty:
        page_df = pd.DataFrame(columns=selected_cols_for_query)

    # Keep only requested real columns if explicitly set (SKU helper might have been injected)
    if requested_columns:
        keep_real = [c for c in requested_columns if c in page_df.columns]
        if keep_real:
            page_df = page_df[keep_real]

    sku_series = None
    if sku_key and sku_key in page_df.columns:
        sku_series = page_df[sku_key]

    # Only JSON image count virtuals remain lazy (others come from inventory_fast)
    if requested_columns is None or any(c in requested_columns for c in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images"]):
        needed_json_cols = ["Json Stock Images", "Json Phone Images", "Json Enhanced Images"] if requested_columns is None else [c for c in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images"] if c in requested_columns]
        page_df = _add_json_virtual_columns(page_df, sku_series, needed_json_cols)

    # If requested columns include virtuals, keep final order as requested
    if requested_columns:
        final_cols = [c for c in requested_columns if c in page_df.columns]
        if final_cols:
            page_df = page_df[final_cols]

    # Replace NaN / +/-Inf with None so JSON serialization is safe
    page_df = page_df.replace([float("inf"), float("-inf")], None)
    page_df = page_df.where(page_df.notna(), None)

    # Convert bool-like columns to expected display values
    for bool_col in ["Json", "Ebay Listing"]:
        if bool_col in page_df.columns:
            def _to_bool_display(x):
                if x is True:
                    return "TRUE"
                if x is False:
                    return "FALSE"
                if isinstance(x, str):
                    norm = x.strip().lower()
                    if norm in {"true", "1", "yes"}:
                        return "TRUE"
                    if norm in {"false", "0", "no"}:
                        return "FALSE"
                return None

            page_df[bool_col] = page_df[bool_col].apply(_to_bool_display)

    for col in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images", "Folder Images"]:
        if col in page_df.columns:
            page_df[col] = page_df[col].apply(lambda x: int(x) if pd.notna(x) and x is not None else "")

    items = page_df.to_dict(orient="records")
    if requested_columns is None:
        available_columns = list(fast_columns_tuple)
        for col in VIRTUAL_JSON_COLUMNS:
            if col not in available_columns:
                available_columns.append(col)
        if "Folder Images" not in available_columns:
            available_columns.append("Folder Images")
        if "Ebay Listing" not in available_columns:
            available_columns.append("Ebay Listing")
    else:
        available_columns = requested_columns

    return {
        "page": page,
        "page_size": page_size,
        "total": int(total),
        "items": items,
        "available_columns": available_columns,
    }


def _get_sku_series(df: pd.DataFrame) -> pd.Series | None:
    if "SKU (Old)" in df.columns:
        return df["SKU (Old)"]
    if "SKU" in df.columns:
        return df["SKU"]
    return None


@lru_cache(maxsize=50000)
def _json_counts_for_sku_cached(sku: str) -> tuple[int | None, int | None, int | None]:
    try:
        path = _sku_json_path(sku)
        if not path.exists():
            return (None, None, None)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        sku_data = data.get(sku, {}) if isinstance(data, dict) else {}
        images = sku_data.get("Images", {}) if isinstance(sku_data, dict) else {}
        summary = images.get("summary", {}) if isinstance(images, dict) else {}

        return (
            summary.get("count_stock", 0),
            summary.get("count_phone", 0),
            summary.get("count_enhanced", 0),
        )
    except Exception:
        return (None, None, None)


def _get_json_file_set() -> set[str]:
    global _JSON_FILE_SET, _JSON_FILE_SET_LOADED_AT
    now = time.time()
    if _JSON_FILE_SET and (now - _JSON_FILE_SET_LOADED_AT) < _JSON_FILE_SET_TTL_SECONDS:
        return _JSON_FILE_SET

    with _JSON_FILE_SET_LOCK:
        now = time.time()
        if _JSON_FILE_SET and (now - _JSON_FILE_SET_LOADED_AT) < _JSON_FILE_SET_TTL_SECONDS:
            return _JSON_FILE_SET

        products_dir = Path(config.PRODUCTS_FOLDER_PATH)
        if not products_dir.exists():
            _JSON_FILE_SET = set()
            _JSON_FILE_SET_LOADED_AT = now
            return _JSON_FILE_SET

        _JSON_FILE_SET = {p.stem for p in products_dir.glob("*.json")}
        _JSON_FILE_SET_LOADED_AT = now
        return _JSON_FILE_SET


def _json_exists_for_sku(sku: str | None) -> bool:
    if not sku or str(sku).strip() == "":
        return False
    return str(sku).strip() in _get_json_file_set()


def _json_counts_for_sku(sku: str | None) -> tuple[int | None, int | None, int | None]:
    if not sku or str(sku).strip() == "":
        return (None, None, None)
    return _json_counts_for_sku_cached(str(sku).strip())


def _add_json_virtual_columns(df: pd.DataFrame, sku_series: pd.Series | None, required_columns: List[str]) -> pd.DataFrame:
    if sku_series is None or not required_columns:
        return df

    normalized_required = [c for c in required_columns if c in VIRTUAL_JSON_COLUMNS]
    if not normalized_required:
        return df

    need_counts = any(c in normalized_required for c in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images"])

    if "Json" in normalized_required:
        df["Json"] = sku_series.apply(_json_exists_for_sku)

    if need_counts:
        counts = sku_series.apply(_json_counts_for_sku)
        if "Json Stock Images" in normalized_required:
            df["Json Stock Images"] = counts.apply(lambda x: x[0])
        if "Json Phone Images" in normalized_required:
            df["Json Phone Images"] = counts.apply(lambda x: x[1])
        if "Json Enhanced Images" in normalized_required:
            df["Json Enhanced Images"] = counts.apply(lambda x: x[2])

    return df


def _apply_number_filter(df: pd.DataFrame, col: str, operator: str, val: Any, val2: Any) -> pd.DataFrame:
    s = pd.to_numeric(df[col], errors="coerce")
    if operator == "equals" and val is not None:
        return df[s == float(val)]
    if operator == "lt" and val is not None:
        return df[s < float(val)]
    if operator == "lte" and val is not None:
        return df[s <= float(val)]
    if operator == "gt" and val is not None:
        return df[s > float(val)]
    if operator == "gte" and val is not None:
        return df[s >= float(val)]
    if operator == "between" and val is not None and val2 is not None:
        return df[(s >= float(val)) & (s <= float(val2))]
    return df


def _apply_boolean_filter(df: pd.DataFrame, col: str, operator: str, value: Any = None) -> pd.DataFrame:
    s = df[col]
    if operator == "is_true":
        return df[s == True]
    if operator == "is_false":
        return df[s == False]
    if operator == "equals":
        want_true = str(value).strip().lower() in {"true", "1", "yes"}
        return df[s == want_true]
    return df


def get_available_columns() -> List[str]:
    """Get all available columns from the inventory, excluding internal/metadata columns"""
    _ensure_fast_table(refreshed_recently_ok=True)
    cols = list(_get_fast_table_columns())
    if not cols:
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
        "Reference"
    ]
    available = [col for col in cols if col not in excluded]
    for col in VIRTUAL_JSON_COLUMNS:
        if col not in available:
            available.append(col)
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
    if not any(m["name"] == "Json" for m in meta):
        meta.append({
            "name": "Json",
            "type": "boolean",
            "operators": BOOL_OPS,
            "enum_values": None,
        })

    for col in ["Json Stock Images", "Json Phone Images", "Json Enhanced Images"]:
        if not any(m["name"] == col for m in meta):
            meta.append({
                "name": col,
                "type": "number",
                "operators": NUM_DATE_OPS,
                "enum_values": None,
            })

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
    _ensure_fast_table(refreshed_recently_ok=True)
    fast_cols = set(_get_fast_table_columns())
    if column in fast_cols and DB_PATH.exists():
        col_text = f"TRIM(COALESCE(CAST({_quote_ident(column)} AS TEXT), ''))"
        where_sql = f"WHERE {col_text} <> ''"
        params: list[Any] = []
        if q:
            q_norm = str(q).strip().lower()
            if q_norm:
                where_sql += f" AND INSTR(LOWER({col_text}), ?) > 0"
                params.append(q_norm)

        conn = sqlite3.connect(DB_PATH)
        try:
            total_unique = conn.execute(
                f"SELECT COUNT(*) FROM (SELECT DISTINCT {col_text} AS v FROM {_quote_ident(FAST_TABLE_NAME)} {where_sql})",
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {col_text} AS v FROM {_quote_ident(FAST_TABLE_NAME)} {where_sql} GROUP BY v ORDER BY COUNT(*) DESC LIMIT ?",
                [*params, int(limit)],
            ).fetchall()
            values = [str(r[0]) for r in rows]
        finally:
            conn.close()

        return {
            "column": column,
            "values": values,
            "total_unique": int(total_unique),
            "limited": int(total_unique) > int(limit),
        }

    # Fallback to in-memory path
    df = excel_inventory.load()
    if column not in df.columns:
        return {"column": column, "values": [], "total_unique": 0, "limited": False}
    s = df[column].dropna().astype(str)
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
    sql_fast = _list_skus_sql_fast(page=page, page_size=page_size, filters=filters, columns=columns)
    if sql_fast is not None:
        return sql_fast

    df = excel_inventory.load()

    # Separate virtual column filters for later
    virtual_json_filters: List[Dict[str, Any]] = []
    folder_images_filter = None
    ebay_listing_filter = None
    if filters:
        filters = [f for f in filters]  # copy
        virtual_json_filters = [f for f in filters if f.get("column") in set(VIRTUAL_JSON_COLUMNS)]
        folder_images_filter = next((f for f in filters if f.get("column") == "Folder Images"), None)
        ebay_listing_filter = next((f for f in filters if f.get("column") == "Ebay Listing"), None)
        if virtual_json_filters:
            filters = [f for f in filters if f.get("column") not in set(VIRTUAL_JSON_COLUMNS)]
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
                        s = series.astype(str).str.strip().str.lower()
                        if operator == "is_true":
                            df = df[s.isin({"true", "1", "yes"})]
                        elif operator == "is_false":
                            df = df[s.isin({"false", "0", "no"})]
                    elif ftype == "enum":
                        s = series.astype(str).str.strip().str.lower()
                        values = filter_item.get("values") or ([] if filter_item.get("value") is None else [filter_item.get("value")])
                        values = [str(v).strip().lower() for v in values]
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
            col_norm = df[col].fillna("").astype(str).str.strip().str.lower()
            
            # Handle is_empty operator
            if operator == "is_empty":
                df = df[(df[col].isna()) | (df[col].astype(str).str.strip() == "")]
                continue
            
            values_list = filter_item.get("values")
            if operator in ("in", "not_in") and values_list:
                norm = [str(v).strip().lower() for v in values_list]
                mask = col_norm.isin(norm)
                df = df[mask] if operator == "in" else df[~mask]
            else:
                value = str(filter_item.get("value", "")).strip().lower()
                if not value:
                    continue
                if operator == "equals":
                    df = df[col_norm == value]
                elif operator == "starts_with":
                    df = df[col_norm.str.startswith(value)]
                elif operator == "ends_with":
                    df = df[col_norm.str.endswith(value)]
                else:  # contains (default)
                    df = df[col_norm.str.contains(value, na=False, regex=False)]

    # Capture SKU series before column filtering (needed for virtual columns)
    sku_series = _get_sku_series(df)

    # Apply Json virtual filters lazily (computed from JSON files only when needed)
    if virtual_json_filters and sku_series is not None:
        needed = list({f.get("column") for f in virtual_json_filters if f.get("column") in set(VIRTUAL_JSON_COLUMNS)})
        df = _add_json_virtual_columns(df, sku_series, needed)
        for filter_item in virtual_json_filters:
            col = filter_item.get("column")
            if col not in df.columns:
                continue
            ftype = filter_item.get("type")
            operator = filter_item.get("operator", "equals")
            val = filter_item.get("value")
            val2 = filter_item.get("value2")

            if ftype == "boolean" or col == "Json":
                df = _apply_boolean_filter(df, col, operator, val)
            else:
                df = _apply_number_filter(df, col, operator, val, val2)

        sku_series = _get_sku_series(df)

    # Apply Folder Images filter if present (read from cache)
    if folder_images_filter and sku_series is not None:
        # Read from cache
        def get_cached_count(sku: str | None) -> int | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_folder_image_count(str(sku))
        
        folder_counts = sku_series.apply(get_cached_count)

        # Apply the filter
        ftype = folder_images_filter.get("type", "number")
        operator = folder_images_filter.get("operator", "gte")
        val = folder_images_filter.get("value")
        val2 = folder_images_filter.get("value2")
        
        s = pd.to_numeric(folder_counts, errors="coerce")
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

        sku_series = _get_sku_series(df)

    # Apply Ebay Listing filter if present (read from cache)
    if ebay_listing_filter and sku_series is not None:
        # Read from cache
        def get_cached_listing(sku: str | None) -> bool | None:
            if not sku or str(sku).strip() == "":
                return None
            return get_sku_has_listing(str(sku))
        
        ebay_listing_values = sku_series.apply(get_cached_listing)
        
        # Apply the filter
        operator = ebay_listing_filter.get("operator", "is_true")
        
        if operator == "is_true":
            df = df[ebay_listing_values == True]
        elif operator == "is_false":
            # Treat unknown cache state (None) as not-listed to avoid empty result sets
            df = df[ebay_listing_values != True]
        elif operator == "equals":
            want_true = str(ebay_listing_filter.get("value", "")).strip().lower() in {"true", "1", "yes"}
            if want_true:
                df = df[ebay_listing_values == True]
            else:
                df = df[ebay_listing_values != True]

        sku_series = _get_sku_series(df)

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

    # Compute Json virtual columns lazily for visible page rows
    needs_json_virtuals = requested_columns is None or any(c in requested_columns for c in VIRTUAL_JSON_COLUMNS)
    if needs_json_virtuals and sku_series is not None:
        if requested_columns is None:
            needed_json_cols = VIRTUAL_JSON_COLUMNS
        else:
            needed_json_cols = [c for c in VIRTUAL_JSON_COLUMNS if c in requested_columns]
        page_sku_series = sku_series.loc[page_df.index]
        page_df = _add_json_virtual_columns(page_df, page_sku_series, needed_json_cols)

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
        for col in VIRTUAL_JSON_COLUMNS:
            if col not in available_columns:
                available_columns.append(col)
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

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from app.services.sku_list import get_default_columns

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STORE_PATH = DATA_DIR / "preferences.json"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_STATE = {
    "profile_id": "default",
    "selected_columns": get_default_columns(),
    "column_filters": {},
    "filter_mode": {},
    "page_size": 50,
    "column_widths": {},
    "emptyFilters": {},
}


def _read_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        # Corrupt file or unreadable; start fresh
        return {}


def _write_store(data: Dict[str, Any]) -> None:
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_sku_filter_state(profile_id: str = "default") -> Dict[str, Any]:
    """Return persistent filter state for the SKU list page."""
    store = _read_store()
    page_key = "sku_list"
    page_store = store.get(page_key, {})
    state = page_store.get(profile_id)

    if not isinstance(state, dict):
        # Initialize default for this profile
        state = {**DEFAULT_STATE, "profile_id": profile_id}
        page_store[profile_id] = state
        store[page_key] = page_store
        _write_store(store)

    # Sanitize types
    state.setdefault("profile_id", profile_id)
    state.setdefault("selected_columns", DEFAULT_STATE["selected_columns"])
    state.setdefault("column_filters", {})
    state.setdefault("filter_mode", {})
    state.setdefault("page_size", 50)
    state.setdefault("column_widths", {})
    return state


def save_sku_filter_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Persist filter state for the SKU list page and return saved value."""
    profile_id = state.get("profile_id") or "default"
    selected_columns = state.get("selected_columns") or []
    column_filters = state.get("column_filters") or {}
    filter_mode = state.get("filter_mode") or {}
    page_size = int(state.get("page_size") or 50)
    column_widths = state.get("column_widths") or {}
    empty_filters = state.get("emptyFilters") or {}

    cleaned = {
        "profile_id": str(profile_id),
        "selected_columns": list(selected_columns),
        "column_filters": dict(column_filters),
        "filter_mode": dict(filter_mode),
        "page_size": page_size,
        "column_widths": {str(k): int(v) for k, v in dict(column_widths).items() if isinstance(v, (int, float))},
        "emptyFilters": dict(empty_filters),
    }

    store = _read_store()
    page_key = "sku_list"
    page_store = store.get(page_key, {})
    page_store[cleaned["profile_id"]] = cleaned
    store[page_key] = page_store
    _write_store(store)
    return cleaned

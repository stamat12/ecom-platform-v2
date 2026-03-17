"""Audit/change log service for SKU/product updates."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app.repositories.sku_json_repo import read_sku_json, write_sku_json

LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "product_change_log.jsonl"
PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "legacy" / "products"


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_product_change_log(
    sku: str,
    action: str,
    details: Dict[str, Any] | None = None,
    *,
    source: str = "api",
    actor: str = "system",
) -> Dict[str, Any]:
    """Append change log entry to global log and (if present) the SKU product JSON."""
    normalized_sku = str(sku or "").strip()
    entry = {
        "timestamp": _utc_iso_now(),
        "sku": normalized_sku,
        "action": str(action or "").strip() or "unknown",
        "source": source,
        "actor": actor,
        "details": details or {},
    }

    # Global append-only audit trail (JSONL)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    product_json_written = False
    try:
        if normalized_sku and (PRODUCTS_DIR / f"{normalized_sku}.json").exists():
            product_json = read_sku_json(normalized_sku) or {}
            logs_section = product_json.setdefault("System Logs", {})
            history = logs_section.get("Change Log", [])
            if not isinstance(history, list):
                history = []

            # Keep newest first and cap to avoid unbounded growth
            history.insert(0, entry)
            logs_section["Change Log"] = history[:300]
            write_sku_json(normalized_sku, product_json)
            product_json_written = True
    except Exception:
        pass

    return {
        "success": True,
        "sku": normalized_sku,
        "product_json_written": product_json_written,
        "entry": entry,
    }

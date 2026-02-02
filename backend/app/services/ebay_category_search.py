from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from app.services.excel_inventory import _get_db_path


def _pick_column(columns: List[str], keywords: List[str]) -> Optional[str]:
    lowered = {c: c.lower() for c in columns}
    for keyword in keywords:
        for col, col_lower in lowered.items():
            if keyword in col_lower:
                return col
    return None


def search_ebay_categories(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    if not query:
        return []

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(ebay_categories)").fetchall()]
        if not columns:
            return []

        where = " OR ".join([f"LOWER(CAST(\"{c}\" AS TEXT)) LIKE ?" for c in columns])
        like = f"%{query.lower()}%"
        rows = conn.execute(
            f"SELECT * FROM ebay_categories WHERE {where} LIMIT ?",
            [like] * len(columns) + [limit],
        ).fetchall()

        id_col = _pick_column(columns, ["id"])
        path_col = _pick_column(columns, ["path", "full"])
        name_col = _pick_column(columns, ["name", "category"])

        results: List[Dict[str, Any]] = []
        for row in rows:
            row_dict = dict(row)
            category_id = str(row_dict.get(id_col, "")) if id_col else ""
            category_path = str(row_dict.get(path_col, "")) if path_col else ""
            category_name = str(row_dict.get(name_col, "")) if name_col else ""

            label = category_path or category_name
            if not label:
                for col in columns:
                    val = row_dict.get(col)
                    if val is not None and str(val).strip():
                        label = str(val)
                        break

            results.append(
                {
                    "label": label,
                    "category_id": category_id,
                    "category_name": category_name,
                    "category_path": category_path,
                    "raw": row_dict,
                }
            )

        return results
    finally:
        conn.close()

from __future__ import annotations

import base64
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from app.config.ebay_config import EBAY_ENRICHMENT_MODEL
from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.ebay_enrichment import get_openai_client
from app.services.excel_inventory import _get_db_path
from app.services.image_listing import list_images_for_sku

logger = logging.getLogger(__name__)

_category_debug_logger: Optional[logging.Logger] = None


def _get_category_debug_logger() -> logging.Logger:
    global _category_debug_logger
    if _category_debug_logger is not None:
        return _category_debug_logger

    debug_logger = logging.getLogger("ebay_category_ai_debug")
    debug_logger.setLevel(logging.INFO)
    debug_logger.propagate = False

    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "ebay_category_ai.log"

    existing = [
        h for h in debug_logger.handlers
        if isinstance(h, logging.FileHandler) and Path(getattr(h, "baseFilename", "")).resolve() == log_file.resolve()
    ]
    if not existing:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        debug_logger.addHandler(handler)

    _category_debug_logger = debug_logger
    return _category_debug_logger


def _category_log(event: str, trace_id: str, **fields: Any) -> None:
    payload = {
        "event": event,
        "trace_id": trace_id,
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    payload.update(fields)
    try:
        _get_category_debug_logger().info(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception as e:
        logger.warning(f"Failed to write category debug log ({event}): {e}")


def _pick_column(columns: List[str], keywords: List[str]) -> Optional[str]:
    lowered = {c: c.lower() for c in columns}
    for keyword in keywords:
        for col, col_lower in lowered.items():
            if keyword in col_lower:
                return col
    return None


def _normalize_category_path(raw_path: str) -> str:
    parts = [p.strip() for p in str(raw_path or "").split("/") if str(p).strip()]
    return "/" + "/".join(parts) if parts else ""


def _path_parts(path: str) -> List[str]:
    return [p.strip() for p in str(path or "").split("/") if str(p).strip()]


def _load_category_entries() -> List[Dict[str, Any]]:
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(ebay_categories)").fetchall()]
        if not columns:
            return []

        id_col = _pick_column(columns, ["id"])
        path_col = _pick_column(columns, ["path", "full"])
        name_col = _pick_column(columns, ["name", "category"])

        rows = conn.execute("SELECT * FROM ebay_categories").fetchall()
        entries: List[Dict[str, Any]] = []
        seen = set()

        for row in rows:
            row_dict = dict(row)
            category_id = str(row_dict.get(id_col, "") or "").strip() if id_col else ""
            raw_path = row_dict.get(path_col) if path_col else None
            if not raw_path:
                raw_path = row_dict.get(name_col) if name_col else ""

            category_path = _normalize_category_path(str(raw_path or ""))
            if not category_path:
                continue

            parts = _path_parts(category_path)
            if not parts:
                continue

            dedupe_key = (category_path.lower(), category_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            entries.append(
                {
                    "category_id": category_id,
                    "category_path": category_path,
                    "parts": parts,
                }
            )

        return entries
    finally:
        conn.close()


def _collect_main_image_paths(sku: str, product_json: Dict[str, Any], max_images: int = 2) -> List[Path]:
    images_section = product_json.get("Images", {}) or {}
    main_images = images_section.get("main_images", []) or []
    main_filenames: List[str] = []
    for item in main_images:
        if isinstance(item, dict) and item.get("filename"):
            main_filenames.append(str(item["filename"]))
        elif isinstance(item, str):
            main_filenames.append(item)

    if not main_filenames:
        return []

    all_images_info = list_images_for_sku(sku)
    by_name = {
        str(img.get("filename", "")).strip().lower(): img
        for img in (all_images_info.get("images") or [])
        if isinstance(img, dict)
    }

    paths: List[Path] = []
    for fn in main_filenames:
        info = by_name.get(Path(fn).name.lower())
        if not info:
            continue
        full_path = str(info.get("full_path") or "").strip()
        if not full_path:
            continue
        p = Path(full_path)
        if p.exists() and p.is_file():
            paths.append(p)
        if len(paths) >= max_images:
            break

    return paths


def _image_to_data_uri(image_path: Path) -> str:
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/*;base64,{b64}"


def _build_product_context(sku: str, product_json: Dict[str, Any]) -> Dict[str, Any]:
    intern_info = product_json.get("Intern Product Info", {}) if isinstance(product_json.get("Intern Product Info"), dict) else {}
    intern_generated = product_json.get("Intern Generated Info", {}) if isinstance(product_json.get("Intern Generated Info"), dict) else {}
    supplier_data = product_json.get("Supplier Data", {}) if isinstance(product_json.get("Supplier Data"), dict) else {}
    condition_data = product_json.get("Product Condition", {}) if isinstance(product_json.get("Product Condition"), dict) else {}

    return {
        "sku": sku,
        "supplier_title": supplier_data.get("Supplier Title", ""),
        "brand": intern_info.get("Brand", ""),
        "gender": intern_info.get("Gender", ""),
        "color": intern_info.get("Color", ""),
        "size": intern_info.get("Size", ""),
        "keywords": intern_generated.get("Keywords", ""),
        "more_details": intern_generated.get("More details", ""),
        "materials": intern_generated.get("Materials", ""),
        "condition": condition_data.get("Condition", ""),
    }


def _normalize_ai_choice(raw_choice: str, options: List[str]) -> Optional[str]:
    if not raw_choice:
        return None
    cleaned = str(raw_choice).strip()
    if cleaned in options:
        return cleaned

    lowered_map = {opt.lower(): opt for opt in options}
    if cleaned.lower() in lowered_map:
        return lowered_map[cleaned.lower()]

    for opt in options:
        if cleaned.lower() in opt.lower() or opt.lower() in cleaned.lower():
            return opt
    return None


def _fallback_option_by_context(options: List[str], context: Dict[str, Any]) -> str:
    context_text = " ".join([str(v or "") for v in context.values()]).lower()
    scored = []
    for opt in options:
        token_score = 0
        for token in opt.lower().split():
            if token and token in context_text:
                token_score += 1
        scored.append((token_score, opt))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][1]


def _choose_option_with_ai(
    options: List[str],
    context: Dict[str, Any],
    level: int,
    image_paths: Optional[List[Path]] = None,
    trace_id: str = "",
    sku: str = "",
) -> Optional[str]:
    if not options:
        return None
    if len(options) == 1:
        return options[0]

    try:
        if trace_id:
            _category_log(
                "category_ai_level_request",
                trace_id,
                sku=sku,
                level=level + 1,
                options_count=len(options),
                options_preview=options[:12],
                use_images=bool(image_paths),
                image_count=len(image_paths or []),
            )
        client = get_openai_client()
        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Du wählst die passendste eBay-Kategorieebene für ein Produkt. "
                    "Wähle GENAU eine Option aus der Liste und antworte nur als JSON: "
                    '{"choice":"<exakter Options-Text>","reason":"kurz"}.\n\n'
                    f"Level: {level + 1}\n"
                    f"Optionen: {json.dumps(options, ensure_ascii=False)}\n"
                    f"Produktkontext: {json.dumps(context, ensure_ascii=False)}"
                ),
            }
        ]

        for img_path in (image_paths or []):
            try:
                content.append({"type": "image_url", "image_url": {"url": _image_to_data_uri(img_path)}})
            except Exception as e:
                logger.warning(f"Failed to attach image for category AI ({img_path}): {e}")

        response = client.chat.completions.create(
            model=EBAY_ENRICHMENT_MODEL,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=180,
            messages=[
                {"role": "system", "content": "Du bist ein präziser eBay-Kategorisierer."},
                {"role": "user", "content": content},
            ],
        )

        raw = response.choices[0].message.content
        if not raw:
            if trace_id:
                _category_log("category_ai_level_empty_response", trace_id, sku=sku, level=level + 1)
            return None
        parsed = json.loads(raw)
        choice = _normalize_ai_choice(str(parsed.get("choice") or ""), options)
        if trace_id:
            _category_log(
                "category_ai_level_response",
                trace_id,
                sku=sku,
                level=level + 1,
                raw_choice=str(parsed.get("choice") or ""),
                normalized_choice=choice or "",
                reason=str(parsed.get("reason") or ""),
            )
        return choice
    except Exception as e:
        logger.warning(f"Category level AI selection failed: {e}")
        if trace_id:
            _category_log("category_ai_level_error", trace_id, sku=sku, level=level + 1, error=str(e))
        return None


def _select_leaf_candidate_with_ai(candidates: List[Dict[str, Any]], context: Dict[str, Any], trace_id: str = "", sku: str = "") -> Dict[str, Any]:
    if len(candidates) == 1:
        return candidates[0]

    options = [c["category_path"] for c in candidates]
    selected = _choose_option_with_ai(options, context, level=99, image_paths=[], trace_id=trace_id, sku=sku)
    if selected:
        for c in candidates:
            if c["category_path"] == selected:
                if trace_id:
                    _category_log("category_ai_leaf_selected", trace_id, sku=sku, selected=selected, source="ai")
                return c

    options_sorted = sorted(options)
    fallback_path = _fallback_option_by_context(options_sorted, context)
    for c in candidates:
        if c["category_path"] == fallback_path:
            if trace_id:
                _category_log("category_ai_leaf_selected", trace_id, sku=sku, selected=fallback_path, source="fallback")
            return c
    return candidates[0]


def detect_and_save_ebay_category_for_sku(sku: str, use_images: bool = True) -> Dict[str, Any]:
    trace_id = uuid4().hex[:12]
    _category_log("category_detect_start", trace_id, sku=sku, use_images=use_images)

    product_json = read_sku_json(sku)
    if not product_json:
        _category_log("category_detect_no_json", trace_id, sku=sku)
        return {"success": False, "sku": sku, "message": f"No JSON found for SKU {sku}"}

    entries = _load_category_entries()
    if not entries:
        _category_log("category_detect_no_categories", trace_id, sku=sku)
        return {"success": False, "sku": sku, "message": "No eBay categories found in database"}

    context = _build_product_context(sku, product_json)
    image_paths = _collect_main_image_paths(sku, product_json, max_images=2) if use_images else []
    _category_log(
        "category_detect_context_loaded",
        trace_id,
        sku=sku,
        category_count=len(entries),
        image_count=len(image_paths),
        context_preview={
            "supplier_title": context.get("supplier_title", ""),
            "brand": context.get("brand", ""),
            "keywords": context.get("keywords", ""),
            "more_details": str(context.get("more_details", ""))[:240],
        },
    )

    selected_parts: List[str] = []
    current_candidates = entries
    max_depth = min(8, max(len(e["parts"]) for e in entries))

    for level in range(max_depth):
        options = sorted(
            {
                e["parts"][level]
                for e in current_candidates
                if len(e["parts"]) > level and e["parts"][: len(selected_parts)] == selected_parts
            }
        )
        if not options:
            break

        choice = _choose_option_with_ai(
            options,
            context,
            level=level,
            image_paths=image_paths if level < 2 else [],
            trace_id=trace_id,
            sku=sku,
        )
        source = "ai"
        if not choice:
            choice = _fallback_option_by_context(options, context)
            source = "fallback"

        _category_log(
            "category_detect_level_choice",
            trace_id,
            sku=sku,
            level=level + 1,
            choice=choice,
            source=source,
            options_count=len(options),
        )

        selected_parts.append(choice)
        current_candidates = [
            e for e in entries if e["parts"][: len(selected_parts)] == selected_parts
        ]

        if current_candidates and all(len(e["parts"]) == len(selected_parts) for e in current_candidates):
            break

    if not selected_parts:
        _category_log("category_detect_no_selected_parts", trace_id, sku=sku)
        return {"success": False, "sku": sku, "message": "Could not determine category path"}

    final_candidates = [
        e for e in entries if e["parts"][: len(selected_parts)] == selected_parts
    ]
    if not final_candidates:
        _category_log("category_detect_no_final_candidates", trace_id, sku=sku, selected_parts=selected_parts)
        return {
            "success": False,
            "sku": sku,
            "message": "No final category candidate after AI narrowing",
            "selected_parts": selected_parts,
        }

    exact_depth = [e for e in final_candidates if len(e["parts"]) == len(selected_parts)]
    leaf_pool = exact_depth or final_candidates
    chosen = _select_leaf_candidate_with_ai(leaf_pool, context, trace_id=trace_id, sku=sku)

    if "Ebay Category" not in product_json or not isinstance(product_json.get("Ebay Category"), dict):
        product_json["Ebay Category"] = {}

    product_json["Ebay Category"]["Category"] = chosen["category_path"]
    if chosen.get("category_id"):
        product_json["Ebay Category"]["eBay Category ID"] = str(chosen["category_id"])

    write_sku_json(sku, product_json)

    _category_log(
        "category_detect_saved",
        trace_id,
        sku=sku,
        category_path=chosen["category_path"],
        category_id=str(chosen.get("category_id") or ""),
        selected_levels=selected_parts,
        used_images=len(image_paths),
    )

    return {
        "success": True,
        "sku": sku,
        "category_path": chosen["category_path"],
        "category_id": str(chosen.get("category_id") or ""),
        "selected_levels": selected_parts,
        "used_images": len(image_paths),
    }


def detect_and_save_ebay_category_for_skus(skus: List[str], use_images: bool = True) -> Dict[str, Any]:
    batch_trace_id = uuid4().hex[:12]
    _category_log("category_detect_batch_start", batch_trace_id, total=len(skus), use_images=use_images, skus=skus)

    results = []
    succeeded = 0
    failed = 0

    for sku in skus:
        result = detect_and_save_ebay_category_for_sku(sku, use_images=use_images)
        results.append(result)
        if result.get("success"):
            succeeded += 1
        else:
            failed += 1

    _category_log(
        "category_detect_batch_complete",
        batch_trace_id,
        total=len(skus),
        succeeded=succeeded,
        failed=failed,
    )

    return {
        "success": failed == 0,
        "total": len(skus),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }

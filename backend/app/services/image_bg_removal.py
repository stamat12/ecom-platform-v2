from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict

from PIL import Image

from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.image_listing import _find_sku_dir
from app.services.image_enhancement import _ensure_images_section, _update_images_summary

logger = logging.getLogger(__name__)


# Models supported by rembg — label shown in UI
REMBG_MODELS = [
    {"id": "isnet-general-use", "name": "ISNet (Best Quality)"},
    {"id": "u2net",             "name": "U2Net (Fast)"},
    {"id": "silueta",           "name": "Silueta (Clean Edges)"},
    {"id": "sam",               "name": "SAM (Segment Anything)"},
]


def remove_background(sku: str, filename: str, model: str = "isnet-general-use") -> Dict[str, Any]:
    """
    Remove background from an image using rembg.
    model: one of isnet-general-use | u2net | silueta | sam
    Saves result as PNG with transparent background and records it in Images.enhanced.
    """
    # Validate model id to prevent arbitrary string injection
    valid_ids = {m["id"] for m in REMBG_MODELS}
    if model not in valid_ids:
        model = "isnet-general-use"

    sku_dir = _find_sku_dir(sku)
    if not sku_dir:
        return {"success": False, "message": f"Images folder not found for SKU {sku}"}

    source_path = sku_dir / filename
    if not source_path.exists():
        return {"success": False, "message": f"File not found: {filename}"}

    output_filename = f"{source_path.stem}_nobg.png"
    output_path = sku_dir / output_filename

    try:
        from rembg import remove as rembg_remove, new_session  # lazy import — model downloads on first call

        logger.info("Removing background from %s/%s using model=%s", sku, filename, model)
        session = new_session(model)

        with open(source_path, "rb") as f:
            input_bytes = f.read()

        remove_kwargs: Dict[str, Any] = {"session": session}
        if model == "sam":
            # SAM requires explicit prompts; use one positive point at image center.
            with Image.open(io.BytesIO(input_bytes)) as src_img:
                center_x = int(src_img.width / 2)
                center_y = int(src_img.height / 2)
            remove_kwargs["sam_prompt"] = [
                {"type": "point", "label": 1, "data": [center_x, center_y]}
            ]

        output_bytes = rembg_remove(input_bytes, **remove_kwargs)
        img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        img.save(output_path, "PNG")
        logger.info("Background removed → %s", output_path.name)

    except Exception as exc:
        logger.error("Background removal failed for %s/%s: %s", sku, filename, exc)
        return {"success": False, "message": f"Background removal failed: {exc}"}

    # Update metadata
    try:
        product_json = read_sku_json(sku) or {}
        images_section = _ensure_images_section(product_json)
        enhanced = list(images_section.get("enhanced", []) or [])
        existing = {e.get("filename") for e in enhanced if isinstance(e, dict)}

        if output_filename not in existing:
            enhanced.append({
                "filename": output_filename,
                "source": filename,
                "method": f"rembg/{model}",
                "generated": True,
                "upscaled": False,
            })

        images_section["enhanced"] = enhanced
        _update_images_summary(images_section)
        product_json["Images"] = images_section
        write_sku_json(sku, product_json)
    except Exception as exc:
        logger.warning("Metadata update failed after bg removal for %s: %s", sku, exc)

    return {
        "success": True,
        "message": "Background removed successfully",
        "sku": sku,
        "source": filename,
        "filename": output_filename,
    }

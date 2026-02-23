"""
eBay item specifics enrichment service using OpenAI vision
"""
import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os

from app.config.ebay_config import (
    EBAY_ENRICHMENT_MODEL,
    EBAY_ENRICHMENT_TEMP,
    EBAY_ENRICHMENT_MAX_TOKENS,
    EBAY_FIELD_ENRICHMENT_PROMPT,
    EBAY_SEO_ENRICHMENT_PROMPT,
)
from app.services.ebay_schema import get_schema_for_sku
from app.repositories.sku_json_repo import read_sku_json, _sku_json_path
from app.services.image_listing import list_images_for_sku

logger = logging.getLogger(__name__)

# OpenAI client
_openai_client: Optional[OpenAI] = None

SEO_FIELD_KEYS = ["product_type", "product_model", "keyword_1", "keyword_2", "keyword_3"]


def _parse_hybrid_sku(sku_string: str) -> List[str]:
    """
    Parse hybrid SKU formats and return list of individual SKUs.
    
    Supports:
    - Comma-separated: "SKU1,SKU2,SKU3"
    - Dash-separated: "SKU1 - SKU2 - SKU3"
    - Range format: "P0010482-P0010490" (expands to P0010482...P0010490)
    - Hybrid: "SKU1,SKU2 - SKU3"
    """
    import re
    
    if not sku_string:
        return []
    
    normalized = str(sku_string).strip()
    skus = []
    
    # First split by comma if it exists
    if "," in normalized:
        parts = normalized.split(",")
        for part in parts:
            part = part.strip()
            # Each part might contain dash-separated SKUs or ranges
            if " - " in part:
                # Space-dash-separated (explicit list)
                sub_skus = [s.strip() for s in part.split(" - ")]
                skus.extend(sub_skus)
            elif "-" in part:
                # Could be a range like "P0010482-P0010490"
                range_skus = _expand_sku_range(part)
                if range_skus:
                    skus.extend(range_skus)
                else:
                    skus.append(part)
            else:
                skus.append(part)
    else:
        # No comma - try dash separation
        if " - " in normalized:
            # Space-dash-separated
            parts = normalized.split(" - ")
            skus.extend([s.strip() for s in parts])
        elif "-" in normalized:
            # Could be a range like "P0010482-P0010490"
            range_skus = _expand_sku_range(normalized)
            if range_skus:
                skus.extend(range_skus)
            else:
                skus.append(normalized)
        else:
            skus.append(normalized)
    
    # Remove empty strings
    skus = [s for s in skus if s.strip()]
    return skus if skus else [sku_string]


def _expand_sku_range(sku_range: str) -> List[str]:
    """
    Expand a SKU range like 'P0010482-P0010490' into individual SKUs.
    Returns empty list if not a valid range format.
    """
    import re
    
    sku_range = sku_range.strip()
    if "-" not in sku_range:
        return []
    
    # Split by dash
    parts = sku_range.split("-")
    if len(parts) != 2:
        return []  # More than one dash, not a simple range
    
    start_sku = parts[0].strip()
    end_sku = parts[1].strip()
    
    # Extract prefix and numeric parts
    start_match = re.match(r"^([A-Za-z]*)(\d+)$", start_sku)
    end_match = re.match(r"^([A-Za-z]*)(\d+)$", end_sku)
    
    if not start_match or not end_match:
        return []  # Not a valid range format
    
    start_prefix, start_num_str = start_match.groups()
    end_prefix, end_num_str = end_match.groups()
    
    # Prefixes must match
    if start_prefix != end_prefix:
        return []
    
    # Preserve original digit width from the start SKU string
    num_digits = len(start_num_str)  # e.g., "00246" -> 5 digits
    
    start_num = int(start_num_str)
    end_num = int(end_num_str)
    
    # Validate range
    if start_num >= end_num or (end_num - start_num) > 1000:
        logger.warning(f"[SKU] Invalid range: {sku_range} (span={end_num - start_num})")
        return []
    
    # Generate range with proper padding
    skus = []
    for i in range(start_num, end_num + 1):
        sku = f"{start_prefix}{str(i).zfill(num_digits)}"
        skus.append(sku)
    
    logger.debug(f"[SKU] Expanded range {sku_range} into {len(skus)} SKUs: {skus[:3]}...")
    return skus


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _image_to_data_uri(image_path: Path) -> str:
    """Convert image to data URI for OpenAI vision"""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/*;base64,{b64}"


def _collect_main_image_paths(sku: str, product_json: Dict[str, Any]) -> List[Path]:
    """
    Collect paths to main images for SKU.
    Finds actual file paths for main images defined in product JSON.
    
    Returns:
        List of Path objects to main images
    """
    images_section = product_json.get("Images", {}) or {}
    main_images = images_section.get("main_images", []) or []
    
    logger.debug(f"Looking for main_images in Images section for {sku}")
    logger.debug(f"Found {len(main_images)} main_images defined")
    
    if not main_images:
        logger.warning(f"No main images defined for SKU {sku}")
        logger.debug(f"Images section content: {list(images_section.keys())}")
        return []
    
    # Extract main image filenames from JSON structure
    main_filenames = []
    for item in main_images:
        if isinstance(item, dict):
            fn = item.get("filename")
            if fn:
                main_filenames.append(fn)
                logger.debug(f"Added main filename from dict: {fn}")
        elif isinstance(item, str):
            main_filenames.append(item)
            logger.debug(f"Added main filename from string: {item}")
    
    logger.debug(f"Main filenames to locate: {main_filenames}")
    
    # Use image_listing service to find actual image paths
    all_images_info = list_images_for_sku(sku)
    all_images = all_images_info.get("images", [])
    
    logger.debug(f"Found {len(all_images)} total images on disk for {sku}")
    
    if not all_images:
        logger.warning(f"No images found on disk for SKU {sku}")
        # If folder not found, return empty
        if not all_images_info.get("folder_found"):
            logger.debug(f"Images folder not found for {sku}")
        return []
    
    # Build set of main filenames for fast lookup
    main_set = {Path(fn).name.lower() for fn in main_filenames}
    logger.debug(f"Main filenames (normalized): {main_set}")
    
    # Find matching image paths - reconstruct full paths from disk listing
    image_paths = []
    for img_info in all_images:
        img_filename = img_info.get("filename", "")
        if img_filename.lower() in main_set:
            # Get SKU directory
            sku_dir = all_images_info.get("sku_dir")
            if not sku_dir:
                # Reconstruct from original_url if needed
                logger.debug(f"SKU dir not in response, attempting to locate for {sku}")
                from app.services.image_listing import _find_sku_dir
                sku_dir = _find_sku_dir(sku)
            
            if sku_dir:
                img_path = Path(sku_dir) / img_filename
                if img_path.exists():
                    image_paths.append(img_path)
                    logger.debug(f"Matched main image: {img_path}")
                else:
                    logger.warning(f"Main image file not found: {img_path}")
            else:
                logger.warning(f"Could not locate SKU directory for {sku}")
    
    logger.info(f"Collected {len(image_paths)} main image paths for {sku}")
    if not image_paths:
        logger.warning(f"No matching main image paths found for {sku}")
    return image_paths


def _merge_fill_only(existing: Dict[str, str], proposed: Dict[str, str]) -> Dict[str, str]:
    """
    Merge proposed values into existing, only filling empty fields
    
    Args:
        existing: Current field values
        proposed: New proposed values
    
    Returns:
        Merged dict (preserves existing non-empty values)
    """
    merged = dict(existing)
    for k, v in (proposed or {}).items():
        # Only fill if current value is empty/whitespace
        if not (merged.get(k) or "").strip() and v is not None:
            merged[k] = str(v).strip()
    return merged


def _merge_fill_only_seo(existing: Dict[str, str], proposed: Dict[str, str]) -> Dict[str, str]:
    merged = {
        "product_type": str(existing.get("product_type") or "").strip(),
        "product_model": str(existing.get("product_model") or "").strip(),
        "keyword_1": str(existing.get("keyword_1") or "").strip(),
        "keyword_2": str(existing.get("keyword_2") or "").strip(),
        "keyword_3": str(existing.get("keyword_3") or "").strip(),
    }
    for key in SEO_FIELD_KEYS:
        incoming = "" if proposed.get(key) is None else str(proposed.get(key)).strip()
        if not merged.get(key) and incoming:
            merged[key] = incoming
    return merged


def _read_ebay_seo_fields(product_json: Dict[str, Any]) -> Dict[str, str]:
    section = product_json.get("eBay SEO", {})
    if not isinstance(section, dict):
        section = {}
    return {
        "product_type": str(section.get("Product Type") or "").strip(),
        "product_model": str(section.get("Product Model") or "").strip(),
        "keyword_1": str(section.get("Keyword 1") or "").strip(),
        "keyword_2": str(section.get("Keyword 2") or "").strip(),
        "keyword_3": str(section.get("Keyword 3") or "").strip(),
    }


def _write_ebay_seo_fields(product_json: Dict[str, Any], seo_fields: Dict[str, str]) -> None:
    if "eBay SEO" not in product_json or not isinstance(product_json.get("eBay SEO"), dict):
        product_json["eBay SEO"] = {}
    product_json["eBay SEO"]["Product Type"] = str(seo_fields.get("product_type") or "").strip()
    product_json["eBay SEO"]["Product Model"] = str(seo_fields.get("product_model") or "").strip()
    product_json["eBay SEO"]["Keyword 1"] = str(seo_fields.get("keyword_1") or "").strip()
    product_json["eBay SEO"]["Keyword 2"] = str(seo_fields.get("keyword_2") or "").strip()
    product_json["eBay SEO"]["Keyword 3"] = str(seo_fields.get("keyword_3") or "").strip()


def _extract_title_for_seo(product_json: Dict[str, Any], sku: str) -> str:
    candidates: List[str] = []

    def _push(value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            candidates.append(text)

    title_keys = [
        "Title",
        "Product Title",
        "Titel",
        "Name",
        "Product Name",
        "eBay Title",
        "Ebay Title",
    ]
    for key in title_keys:
        _push(product_json.get(key))

    intern_product = product_json.get("Intern Product Info", {})
    if isinstance(intern_product, dict):
        for key in ["Title", "Product Title", "Titel", "Name", "Model", "Product Name"]:
            _push(intern_product.get(key))

    intern_generated = product_json.get("Intern Generated Info", {})
    if isinstance(intern_generated, dict):
        for key in ["Title", "Product Title", "Titel", "Name", "SEO Title", "Keywords"]:
            _push(intern_generated.get(key))

    ebay_listing = product_json.get("Ebay Listing", {})
    if isinstance(ebay_listing, dict):
        for key in ["Title", "Listing Title", "eBay Title", "Ebay Title"]:
            _push(ebay_listing.get(key))

    if candidates:
        return candidates[0]

    logger.warning(f"No title candidate found for SEO enrichment on SKU {sku}")
    return ""


def _call_openai_text_json(system_prompt: str, user_prompt: str) -> Dict[str, str]:
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=EBAY_ENRICHMENT_MODEL,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        cleaned: Dict[str, str] = {}
        for key in SEO_FIELD_KEYS:
            value = parsed.get(key)
            cleaned[key] = "" if value is None else str(value).strip()
        return cleaned
    except Exception as e:
        logger.error(f"OpenAI SEO extraction failed: {e}")
        return {}


def enrich_ebay_seo_fields(sku: str, force: bool = False) -> Dict[str, Any]:
    """
    Enrich SEO fields for a single SKU or hybrid SKU.
    
    For hybrid SKUs:
    - Generates SEO using ONLY the first SKU's images + text (to save API tokens)
    - Copies the same SEO fields to all other SKUs with JSON files
    - Skips SKUs without JSON files gracefully
    """
    # Parse hybrid SKUs
    individual_skus = _parse_hybrid_sku(sku)
    
    if not individual_skus:
        raise ValueError(f"Could not parse SKU: {sku}")
    
    if len(individual_skus) > 1:
        logger.info(f"[SEO] Hybrid SKU detected: {sku} -> {individual_skus}")
    
    # Filter to only SKUs that have JSON files
    from app.repositories.sku_json_repo import _sku_json_path
    skus_with_json = []
    skus_without_json = []
    
    for individual_sku in individual_skus:
        json_path = _sku_json_path(individual_sku)
        if json_path.exists():
            skus_with_json.append(individual_sku)
        else:
            skus_without_json.append(individual_sku)
    
    if not skus_with_json:
        return {
            "success": False,
            "sku": sku,
            "individual_skus": individual_skus,
            "skus_with_json": [],
            "skus_without_json": skus_without_json,
            "all_results": [],
            "seo_fields": {},
            "updated_seo_fields": 0,
            "title_used": "",
            "message": f"No JSON files found for any SKU: {', '.join(individual_skus)}",
        }
    
    logger.info(f"[SEO] Processing {len(skus_with_json)} SKU(s) with JSON files (skipping {len(skus_without_json)})")
    
    # Process ONLY the first SKU with image analysis (to save tokens)
    first_sku = skus_with_json[0]
    first_result = _enrich_single_sku_seo(first_sku, force)
    
    all_results = [first_result]
    
    # For remaining SKUs, copy the same SEO fields without re-generating
    if len(skus_with_json) > 1:
        logger.info(f"[SEO] Copying SEO from {first_sku} to {len(skus_with_json)-1} other SKU(s)")
        seo_fields_to_copy = first_result.get("seo_fields", {})
        
        for other_sku in skus_with_json[1:]:
            # Copy without re-generating (no image analysis needed)
            result = _copy_seo_to_sku(other_sku, seo_fields_to_copy, force)
            all_results.append(result)
    
    # If hybrid, log summary
    if len(individual_skus) > 1:
        successful = sum(1 for r in all_results if r.get("success"))
        logger.info(f"[SEO] Hybrid SEO complete: {successful}/{len(skus_with_json)} SKU(s) processed")
    
    # Display first result
    display_result = first_result if first_result.get("success") else all_results[0] if all_results else {}
    
    return {
        "success": bool(first_result.get("success")),
        "sku": sku,
        "individual_skus": individual_skus,
        "skus_with_json": skus_with_json,
        "skus_without_json": skus_without_json,
        "all_results": all_results,
        "seo_fields": display_result.get("seo_fields", {}),
        "updated_seo_fields": display_result.get("updated_seo_fields", 0),
        "title_used": display_result.get("title_used", ""),
        "message": f"Generated SEO from {first_sku} and copied to {len(skus_with_json)} SKU(s)" + 
                   (f" (skipped {len(skus_without_json)} without JSON)" if skus_without_json else ""),
    }


def _copy_seo_to_sku(sku: str, seo_fields: Dict[str, str], force: bool = False) -> Dict[str, Any]:
    """Copy SEO fields to a SKU without re-generating (saves tokens)."""
    product_json = read_sku_json(sku)
    if not product_json:
        return {
            "success": False,
            "sku": sku,
            "error": f"No product JSON found for SKU {sku}",
            "seo_fields": {},
            "updated_seo_fields": 0,
        }
    
    current = _read_ebay_seo_fields(product_json)
    
    # Determine which fields will be updated
    if force:
        # Force overwrite all fields
        merged = seo_fields
    else:
        # Only fill empty fields (preserve existing values)
        merged = _merge_fill_only_seo(current, seo_fields)
    
    # Count updates
    updated_count = sum(1 for key in SEO_FIELD_KEYS if (current.get(key) or "").strip() != (merged.get(key) or "").strip())
    
    # Write SEO fields to product JSON
    _write_ebay_seo_fields(product_json, merged)
    
    # Save back to file
    json_path = _sku_json_path(sku)
    full_data = {sku: product_json}
    temp_path = json_path.with_suffix(".tmp.json")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    temp_path.replace(json_path)
    
    logger.info(f"[SEO] Copied SEO to {sku} ({updated_count} fields updated)")
    
    return {
        "success": True,
        "sku": sku,
        "seo_fields": merged,
        "updated_seo_fields": updated_count,
        "title_used": "(copied from first SKU, no title generation)",
    }


def _enrich_single_sku_seo(sku: str, force: bool = False) -> Dict[str, Any]:
    """Enrich SEO fields for a single SKU."""
    product_json = read_sku_json(sku)
    if not product_json:
        return {
            "success": False,
            "sku": sku,
            "error": f"No product JSON found for SKU {sku}",
            "seo_fields": {},
            "updated_seo_fields": 0,
        }

    current = _read_ebay_seo_fields(product_json)
    if not force and all((current.get(k) or "").strip() for k in SEO_FIELD_KEYS):
        return {
            "success": True,
            "sku": sku,
            "seo_fields": current,
            "updated_seo_fields": 0,
            "title_used": _extract_title_for_seo(product_json, sku),
        }

    # Collect main images for vision analysis
    image_paths = _collect_main_image_paths(sku, product_json)
    
    title = _extract_title_for_seo(product_json, sku)
    if not title:
        return {
            "success": False,
            "sku": sku,
            "error": f"No product title found for SKU {sku}",
            "seo_fields": {},
            "updated_seo_fields": 0,
        }
    
    # If we have images, use vision API with images + title
    if image_paths:
        logger.info(f"Using vision API with {len(image_paths)} images for SEO enrichment of {sku}")
        
        # Build prompt that includes title context for vision analysis
        user_prompt_vision = (
            f"Produkt-Titel: {title}\n\n"
            "Analysiere die Bilder und den Titel um folgende SEO-Felder auszufüllen:\n"
            "- product_type: Art des Produkts (z.B. 'Short', 'Dress', 'Jacket')\n"
            "- product_model: Modellnummer oder spezifisches Modell (falls sichtbar)\n"
            "- keyword_1, keyword_2, keyword_3: Relevante Suchbegriffe für dieses Produkt\n\n"
            "Liefere ausschließlich JSON mit genau diesen Keys: "
            "product_type, product_model, keyword_1, keyword_2, keyword_3"
        )
        
        proposed = _call_openai_vision(image_paths, EBAY_SEO_ENRICHMENT_PROMPT, SEO_FIELD_KEYS)
        
        # If vision returns nothing, fallback to text-based approach
        if not proposed:
            logger.warning(f"Vision API returned no results for {sku}, falling back to text-based SEO")
            user_prompt_text = (
                "Produkt-Titel:\n"
                f"{title}\n\n"
                "Liefere ausschließlich JSON mit genau diesen Keys: "
                "product_type, product_model, keyword_1, keyword_2, keyword_3"
            )
            proposed = _call_openai_text_json(EBAY_SEO_ENRICHMENT_PROMPT, user_prompt_text)
    else:
        # No images available, use text-based approach
        logger.info(f"No images found for {sku}, using text-based SEO enrichment")
        user_prompt_text = (
            "Produkt-Titel:\n"
            f"{title}\n\n"
            "Liefere ausschließlich JSON mit genau diesen Keys: "
            "product_type, product_model, keyword_1, keyword_2, keyword_3"
        )
        proposed = _call_openai_text_json(EBAY_SEO_ENRICHMENT_PROMPT, user_prompt_text)
    
    if force:
        merged = {
            "product_type": str(proposed.get("product_type") or current.get("product_type") or "").strip(),
            "product_model": str(proposed.get("product_model") or current.get("product_model") or "").strip(),
            "keyword_1": str(proposed.get("keyword_1") or current.get("keyword_1") or "").strip(),
            "keyword_2": str(proposed.get("keyword_2") or current.get("keyword_2") or "").strip(),
            "keyword_3": str(proposed.get("keyword_3") or current.get("keyword_3") or "").strip(),
        }
    else:
        merged = _merge_fill_only_seo(current, proposed)

    updated_count = sum(1 for key in SEO_FIELD_KEYS if (current.get(key) or "").strip() != (merged.get(key) or "").strip())

    _write_ebay_seo_fields(product_json, merged)

    json_path = _sku_json_path(sku)
    full_data = {sku: product_json}
    temp_path = json_path.with_suffix(".tmp.json")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    temp_path.replace(json_path)
    
    return {
        "success": True,
        "sku": sku,
        "seo_fields": merged,
        "updated_seo_fields": updated_count,
        "title_used": title,
    }

    return {
        "success": True,
        "sku": sku,
        "seo_fields": merged,
        "updated_seo_fields": updated_count,
        "message": "SEO enrichment completed",
        "title_used": title,
    }


def _build_enrichment_prompt(
    category_name: str,
    category_id: str,
    required_aspects: List[Dict[str, Any]],
    optional_aspects: List[Dict[str, Any]],
    current_fields: Dict[str, str],
    product_json: Dict[str, Any] = None
) -> str:
    """Build enrichment prompt for OpenAI"""
    
    # Extract Intern Product Info and Intern Generated Info if available
    intern_product_info = ""
    if product_json:
        intern_data = product_json.get("Intern Product Info", {})
        if intern_data:
            intern_product_info = "Manuell hinzugefügte Produktinformationen:\n"
            for key, value in intern_data.items():
                if value and str(value).strip():
                    intern_product_info += f"  - {key}: {value}\n"
    
    intern_generated_info = ""
    if product_json:
        intern_gen = product_json.get("Intern Generated Info", {})
        if intern_gen:
            intern_generated_info = "Manuell eingegebene oder generierte Informationen:\n"
            for key, value in intern_gen.items():
                if value and str(value).strip():
                    intern_generated_info += f"  - {key}: {value}\n"
    
    # Format required fields
    required_lines = []
    for aspect in required_aspects:
        name = aspect.get("name", "")
        values = aspect.get("values") or []
        if values:
            values_str = f" (Erlaubte Werte: {', '.join(values[:20])})"
        else:
            values_str = ""
        required_lines.append(f"- {name}{values_str}")
    
    required_fields = "\n".join(required_lines) if required_lines else "Keine"
    
    # Format optional fields
    optional_lines = []
    for aspect in optional_aspects:
        name = aspect.get("name", "")
        values = aspect.get("values") or []
        if values:
            values_str = f" (Erlaubte Werte: {', '.join(values[:20])})"
        else:
            values_str = ""
        optional_lines.append(f"- {name}{values_str}")
    
    optional_fields = "\n".join(optional_lines) if optional_lines else "Keine"
    
    # Format current values
    current_values = json.dumps(current_fields, ensure_ascii=False, indent=2)
    
    # Build additional context
    additional_context = ""
    if intern_product_info or intern_generated_info:
        additional_context = "\nZUSÄTZLICHE KONTEXTINFORMATIONEN (manuell hinzugefügt):\n"
        if intern_product_info:
            additional_context += intern_product_info + "\n"
        if intern_generated_info:
            additional_context += intern_generated_info
    
    return EBAY_FIELD_ENRICHMENT_PROMPT.format(
        category_name=category_name,
        category_id=category_id,
        required_fields=required_fields,
        optional_fields=optional_fields,
        current_values=current_values,
        additional_context=additional_context
    )


def _call_openai_vision(
    image_paths: List[Path],
    system_prompt: str,
    field_names: List[str]
) -> Dict[str, str]:
    """
    Call OpenAI vision API to extract field values from images
    
    Returns:
        Dict of field_name -> value
    """
    if not image_paths:
        logger.warning("No images provided for vision extraction")
        return {}
    
    try:
        client = get_openai_client()
        
        # Build content with images
        content: List[dict] = []
        
        for img_path in image_paths:
            try:
                data_uri = _image_to_data_uri(img_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": data_uri}
                })
            except Exception as e:
                logger.warning(f"Failed to encode image {img_path}: {e}")
        
        if not content:
            logger.error("No images successfully encoded")
            return {}
        
        # Add text instruction
        content.insert(0, {
            "type": "text",
            "text": f"Analysiere die Bilder und fülle die Felder aus. Erwartete Felder: {', '.join(field_names)}"
        })
        
        # Call OpenAI
        response = client.chat.completions.create(
            model=EBAY_ENRICHMENT_MODEL,
            response_format={"type": "json_object"},
            temperature=EBAY_ENRICHMENT_TEMP,
            max_tokens=EBAY_ENRICHMENT_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
        )
        
        # Parse response
        raw = response.choices[0].message.content
        if not raw:
            logger.warning("Empty response from OpenAI")
            return {}
        
        parsed = json.loads(raw)
        
        # Extract required/optional sections
        result = {}
        if isinstance(parsed, dict):
            # Handle both flat and nested responses
            required = parsed.get("required", {})
            optional = parsed.get("optional", {})
            
            if required or optional:
                result.update(required or {})
                result.update(optional or {})
            else:
                # Flat response
                result = {k: str(v) if v is not None else "" for k, v in parsed.items()}
        
        # Filter to expected fields
        cleaned = {k: str(v).strip() for k, v in result.items() if k in field_names and v}
        
        logger.info(f"OpenAI extracted {len(cleaned)} field values from {len(image_paths)} images")
        return cleaned
        
    except Exception as e:
        logger.error(f"OpenAI vision extraction failed: {e}")
        return {}


def enrich_ebay_fields(sku: str, force: bool = False) -> Dict[str, Any]:
    """
    Enrich eBay fields for SKU using OpenAI vision
    
    Args:
        sku: Product SKU
        force: Force re-enrichment even if fields exist
    
    Returns:
        Dict with enrichment results
    """
    logger.info(f"Starting eBay field enrichment for SKU {sku}")
    
    # Load product JSON
    product_json = read_sku_json(sku)
    if not product_json:
        raise ValueError(f"No product JSON found for SKU {sku}")
    
    # Get schema for SKU's category
    schema_data = get_schema_for_sku(sku, use_cache=True)
    if not schema_data:
        raise ValueError(f"No eBay schema found for SKU {sku}")
    
    metadata = schema_data.get("_metadata", {})
    schema = schema_data.get("schema", {})
    
    category_id = metadata.get("category_id", "")
    category_name = metadata.get("category_name", "")
    
    required_aspects = schema.get("required", [])
    optional_aspects = schema.get("optional", [])
    
    if not required_aspects and not optional_aspects:
        raise ValueError(f"Empty schema for category {category_id}")
    
    # Get current eBay fields
    existing_ebay_fields = product_json.get("eBay Fields", {}) or {}
    current_required = existing_ebay_fields.get("required", {}) if isinstance(existing_ebay_fields, dict) else {}
    current_optional = existing_ebay_fields.get("optional", {}) if isinstance(existing_ebay_fields, dict) else {}
    current_fields = {**current_required, **current_optional}
    
    # Collect main images
    image_paths = _collect_main_image_paths(sku, product_json)
    if not image_paths:
        raise ValueError(f"No main images found for SKU {sku}")
    
    # Build prompt
    all_field_names = [a.get("name") for a in required_aspects + optional_aspects if a.get("name")]
    system_prompt = _build_enrichment_prompt(
        category_name, category_id, required_aspects, optional_aspects, current_fields, product_json
    )
    
    # Call OpenAI
    proposed = _call_openai_vision(image_paths, system_prompt, all_field_names)
    
    # Merge (fill only empty)
    merged = _merge_fill_only(current_fields, proposed)
    
    # Split back into required/optional
    required_names = {a.get("name") for a in required_aspects if a.get("name")}
    merged_required = {k: v for k, v in merged.items() if k in required_names}
    merged_optional = {k: v for k, v in merged.items() if k not in required_names}
    
    # Calculate missing required
    missing_required = [name for name in required_names if not (merged_required.get(name) or "").strip()]
    
    # Save back to JSON
    product_json["eBay Fields"] = {
        "required": merged_required,
        "optional": merged_optional
    }
    
    # Remove legacy Ebay section if exists
    if "Ebay" in product_json and "Fields" in product_json.get("Ebay", {}):
        del product_json["Ebay"]
    
    # Atomic write
    json_path = _sku_json_path(sku)
    full_data = {sku: product_json}
    
    temp_path = json_path.with_suffix(".tmp.json")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)
    temp_path.replace(json_path)
    
    seo_result = enrich_ebay_seo_fields(sku, force=force)
    updated_seo_fields = int(seo_result.get("updated_seo_fields", 0))

    logger.info(
        f"eBay fields enriched for SKU {sku}: {len(merged)} total fields, "
        f"{len(missing_required)} missing required, SEO updated={updated_seo_fields}"
    )
    
    return {
        "success": True,
        "sku": sku,
        "fields": merged,
        "required_fields": merged_required,
        "optional_fields": merged_optional,
        "missing_required": missing_required,
        "used_images": len(image_paths),
        "updated_fields": len(proposed) + updated_seo_fields,
        "seo_fields": seo_result.get("seo_fields", {}),
        "updated_seo_fields": updated_seo_fields,
    }


def enrich_multiple_skus(skus: List[str], force: bool = False) -> Dict[str, Any]:
    """
    Enrich eBay fields for multiple SKUs
    
    Args:
        skus: List of SKUs
        force: Force re-enrichment
    
    Returns:
        Dict with batch results
    """
    results = []
    successful = 0
    failed = 0
    
    for sku in skus:
        try:
            result = enrich_ebay_fields(sku, force)
            results.append(result)
            successful += 1
        except Exception as e:
            logger.error(f"Failed to enrich SKU {sku}: {e}")
            results.append({
                "success": False,
                "sku": sku,
                "message": f"Error: {str(e)}",
                "missing_required": [],
                "updated_fields": 0,
                "used_images": 0
            })
            failed += 1
    
    return {
        "success": successful > 0,
        "total_count": len(skus),
        "successful_count": successful,
        "failed_count": failed,
        "results": results
    }


def validate_ebay_fields(sku: str) -> Dict[str, Any]:
    """
    Validate eBay fields for SKU (check required fields are filled)
    
    Returns:
        Dict with validation results
    """
    try:
        # Load product JSON
        product_json = read_sku_json(sku)
        if not product_json:
            return {
                "sku": sku,
                "valid": False,
                "message": "Product JSON not found",
                "missing_required": [],
                "category_id": "",
                "category_name": "",
                "total_required": 0,
                "filled_required": 0,
                "total_optional": 0,
                "filled_optional": 0
            }
        
        # Get schema
        schema_data = get_schema_for_sku(sku, use_cache=True)
        if not schema_data:
            return {
                "sku": sku,
                "valid": False,
                "message": "No eBay schema found",
                "missing_required": [],
                "category_id": "",
                "category_name": "",
                "total_required": 0,
                "filled_required": 0,
                "total_optional": 0,
                "filled_optional": 0
            }
        
        metadata = schema_data.get("_metadata", {})
        schema = schema_data.get("schema", {})
        
        raw_category_id = metadata.get("category_id", "")
        category_id = "" if raw_category_id is None else str(raw_category_id)
        category_name = "" if metadata.get("category_name") is None else str(metadata.get("category_name"))
        
        required_aspects = schema.get("required", [])
        optional_aspects = schema.get("optional", [])
        
        # Get current fields
        existing_ebay_fields = product_json.get("eBay Fields", {}) or {}
        current_required = existing_ebay_fields.get("required", {}) if isinstance(existing_ebay_fields, dict) else {}
        current_optional = existing_ebay_fields.get("optional", {}) if isinstance(existing_ebay_fields, dict) else {}

        def _normalize_field_value(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, dict) and "value" in value:
                raw = value.get("value")
                return "" if raw is None else str(raw).strip()
            if isinstance(value, list):
                return ", ".join([str(v).strip() for v in value if v is not None]).strip()
            return str(value).strip()
        
        # Check missing required
        required_names = {a.get("name") for a in required_aspects if a.get("name")}
        missing_required = [name for name in required_names if not _normalize_field_value(current_required.get(name))]
        
        # Calculate stats
        filled_required = len([v for v in current_required.values() if _normalize_field_value(v)])
        filled_optional = len([v for v in current_optional.values() if _normalize_field_value(v)])
        
        valid = len(missing_required) == 0
        
        return {
            "sku": sku,
            "valid": valid,
            "missing_required": missing_required,
            "category_id": category_id,
            "category_name": category_name,
            "total_required": len(required_names),
            "filled_required": filled_required,
            "total_optional": len(optional_aspects),
            "filled_optional": filled_optional,
            "message": "All required fields filled" if valid else f"{len(missing_required)} required fields missing"
        }
    except Exception as e:
        logger.error(f"Validation failed for SKU {sku}: {e}")
        return {
            "sku": sku,
            "valid": False,
            "missing_required": [],
            "category_id": "",
            "category_name": "",
            "total_required": 0,
            "filled_required": 0,
            "total_optional": 0,
            "filled_optional": 0,
            "message": f"Validation failed: {str(e)}"
        }

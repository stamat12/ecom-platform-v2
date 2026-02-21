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
    EBAY_FIELD_ENRICHMENT_PROMPT
)
from app.services.ebay_schema import get_schema_for_sku
from app.repositories.sku_json_repo import read_sku_json, _sku_json_path
from app.services.image_listing import list_images_for_sku

logger = logging.getLogger(__name__)

# OpenAI client
_openai_client: Optional[OpenAI] = None


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
    
    logger.info(f"eBay fields enriched for SKU {sku}: {len(merged)} total fields, {len(missing_required)} missing required")
    
    return {
        "success": True,
        "sku": sku,
        "fields": merged,
        "required_fields": merged_required,
        "optional_fields": merged_optional,
        "missing_required": missing_required,
        "used_images": len(image_paths),
        "updated_fields": len(proposed)
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

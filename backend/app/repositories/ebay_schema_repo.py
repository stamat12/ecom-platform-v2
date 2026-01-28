"""
Repository for eBay category schema caching
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Schemas directory (relative to backend folder)
SCHEMAS_DIR = Path(__file__).parent.parent.parent / "legacy" / "schemas"

def ensure_schemas_dir():
    """Create schemas directory if it doesn't exist"""
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

def get_schema_path(category_id: str) -> Path:
    """Get path to schema file for category ID"""
    return SCHEMAS_DIR / f"EbayCat_{category_id}_EBAY_DE.json"

def schema_exists(category_id: str) -> bool:
    """Check if schema cached for category ID"""
    return get_schema_path(category_id).exists()

def get_schema(category_id: str) -> Optional[Dict[str, Any]]:
    """
    Load cached schema for category ID
    
    Returns:
        Schema dict with _metadata and schema keys, or None if not found
    """
    schema_path = get_schema_path(category_id)
    
    if not schema_path.exists():
        logger.debug(f"Schema not found for category {category_id}")
        return None
    
    try:
        with schema_path.open("r", encoding="utf-8") as f:
            schema_data = json.load(f)
        
        logger.debug(f"Loaded schema for category {category_id}")
        return schema_data
        
    except Exception as e:
        logger.error(f"Error loading schema for category {category_id}: {e}")
        return None

def save_schema(category_id: str, schema_data: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
    """
    Save schema to cache with metadata
    
    Args:
        category_id: eBay category ID
        schema_data: Schema with required/optional fields
        metadata: Category metadata (name, fees, etc.)
    
    Returns:
        True if saved successfully
    """
    ensure_schemas_dir()
    schema_path = get_schema_path(category_id)
    
    payload = {
        "_metadata": metadata,
        "schema": schema_data
    }
    
    try:
        # Atomic write
        temp_path = schema_path.with_suffix(".tmp.json")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        temp_path.replace(schema_path)
        logger.info(f"Saved schema for category {category_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving schema for category {category_id}: {e}")
        return False

def list_cached_schemas() -> List[str]:
    """
    Get list of all cached category IDs
    
    Returns:
        List of category IDs
    """
    if not SCHEMAS_DIR.exists():
        return []
    
    category_ids = []
    for schema_file in SCHEMAS_DIR.glob("EbayCat_*_EBAY_DE.json"):
        # Extract category ID from filename: EbayCat_112529_EBAY_DE.json -> 112529
        parts = schema_file.stem.split("_")
        if len(parts) >= 2:
            category_ids.append(parts[1])
    
    return sorted(category_ids)

def delete_schema(category_id: str) -> bool:
    """
    Delete cached schema
    
    Returns:
        True if deleted successfully
    """
    schema_path = get_schema_path(category_id)
    
    if not schema_path.exists():
        return False
    
    try:
        schema_path.unlink()
        logger.info(f"Deleted schema for category {category_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting schema for category {category_id}: {e}")
        return False

def get_schema_metadata(category_id: str) -> Optional[Dict[str, Any]]:
    """
    Get only metadata for schema (without full schema)
    
    Returns:
        Metadata dict or None
    """
    schema = get_schema(category_id)
    if schema:
        return schema.get("_metadata")
    return None

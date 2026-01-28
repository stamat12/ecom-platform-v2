import json
from functools import lru_cache
from pathlib import Path
from typing import Optional
def get_image_classification(sku: str, filename: str) -> Optional[str]:
    """Infer classification ('phone'|'stock'|'enhanced') for an image by filename.
    Looks into the SKU's JSON `Images` section. Matches both plain strings and
    dict records with a `filename` field. Returns None if not found or on error.
    """
    try:
        data = load_product_detail(sku) or {}
        images = data.get('Images', {}) or {}

        def contains(list_obj) -> bool:
            for item in list_obj or []:
                if isinstance(item, str):
                    if Path(item).name == filename:
                        return True
                elif isinstance(item, dict):
                    fn = item.get('filename', '')
                    if Path(fn).name == filename:
                        return True
            return False

        if contains(images.get('phone')):
            return 'phone'
        if contains(images.get('stock')):
            return 'stock'
        if contains(images.get('enhanced')):
            return 'enhanced'
        return None
    except Exception:
        return None
from typing import Dict, List, Optional, Tuple
import sys

# Ensure project root is on path for local imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from agents.image_classification import get_image_classification

# Image extensions
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


# ============================================================================
# PRODUCT DATA HELPERS
# ============================================================================

def load_product_detail(sku: str) -> dict:
    """Load product detail JSON for a SKU."""
    path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(sku, {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_field_value(product_detail: Dict, field_name: str) -> str:
    """Extract a field value from nested product detail structure."""
    for category, fields in product_detail.items():
        if isinstance(fields, dict) and field_name in fields:
            val = fields[field_name]
            return str(val) if val else ""
    return ""


def get_collected_data_summary(sku: str) -> Optional[dict]:
    """Extract a summary of collected data for a SKU from its JSON file."""
    product_detail = load_product_detail(sku)
    if not product_detail:
        return None

    summary = {}
    for category, fields in product_detail.items():
        if isinstance(fields, dict):
            non_empty_fields = [k for k, v in fields.items() if v and v != ""]
            if non_empty_fields:
                summary[category] = len(non_empty_fields)
    
    return summary if summary else None


def get_all_collected_data(sku: str) -> Optional[Dict]:
    """Get all collected data for a SKU with all fields (empty and filled)."""
    product_detail = load_product_detail(sku)
    return product_detail if product_detail else None


def build_editable_data_dict(sku: str) -> Dict[str, Dict[str, str]]:
    """Build a dict for editing: {field_name: {value: current_value, category: category}}."""
    from agents.inventory_data_collector import get_important_fields
    
    product_detail = load_product_detail(sku)
    if not product_detail:
        return {}
    
    important_fields = get_important_fields()
    editable = {}
    
    for field_name in important_fields:
        value = extract_field_value(product_detail, field_name)
        # Find which category this field belongs to
        category = None
        for cat, fields in product_detail.items():
            if isinstance(fields, dict) and field_name in fields:
                category = cat
                break
        
        editable[field_name] = {
            'value': value,
            'category': category or 'Unknown'
        }
    
    return editable


def get_ordered_fields(sku: str) -> List[str]:
    """Get all fields ordered as they appear in the JSON file."""
    product_detail = load_product_detail(sku)
    if not product_detail:
        return []
    
    ordered_fields = []
    # Preserve order of categories and fields as they are in the JSON
    for category, fields in product_detail.items():
        if isinstance(fields, dict):
            for field_name in fields.keys():
                ordered_fields.append(field_name)
    
    return ordered_fields


def is_sku_collected(sku: str) -> bool:
    """Check if a SKU has collected data (JSON file exists with data)."""
    product_detail = load_product_detail(sku)
    if not product_detail:
        return False
    # Check if there's at least one non-empty category with data
    for category, fields in product_detail.items():
        if isinstance(fields, dict) and any(v and v != "" for v in fields.values()):
            return True
    return False


def has_main_images(sku: str) -> bool:
    """Check if SKU has main images selected in JSON."""
    product_detail = load_product_detail(sku)
    if not product_detail:
        return False
    images_section = product_detail.get("Images", {}) or {}
    main_images = images_section.get("main_images", []) or []
    return bool(main_images)


# ============================================================================
# IMAGE FILE HELPERS
# ============================================================================

def find_images_dir_for_sku(sku: str) -> Optional[Path]:
    """Find the images directory for a SKU."""
    for base in config.IMAGE_FOLDER_PATHS:
        base_path = base if base.is_absolute() else (config.PROJECT_ROOT / base)
        candidate = base_path / sku
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def folder_signature(images_dir: Path) -> Tuple[int, float]:
    """A cheap signature to detect changes (count, newest mtime)."""
    try:
        files = [p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    except Exception:
        return (0, 0.0)
    if not files:
        return (0, 0.0)
    newest = max(p.stat().st_mtime for p in files)
    return (len(files), newest)


@lru_cache(maxsize=512)
def list_image_files_cached(images_dir: Path, _sig: Tuple[int, float]) -> List[Path]:
    """Cache listing by (dir, signature). Pass folder_signature(dir) as _sig."""
    try:
        return sorted(
            [p for p in images_dir.glob("*") if p.suffix.lower() in IMAGE_EXTS and p.is_file()]
        )
    except Exception:
        return []


def list_image_files(images_dir: Optional[Path]) -> List[Path]:
    """List image files in a directory with caching."""
    if not images_dir:
        return []
    sig = folder_signature(images_dir)
    return list_image_files_cached(images_dir, sig)


# ============================================================================
# CLASSIFICATION HELPERS
# ============================================================================

def get_classification_status(sku: str) -> str:
    """Return 'fully_classified', 'partly_classified', or 'unclassified'."""
    images_dir = find_images_dir_for_sku(sku)
    folder_files = list_image_files(images_dir)
    
    if not folder_files:
        return 'unclassified'  # No images means unclassified
    
    classified_count = 0
    for img_path in folder_files:
        if get_image_classification(sku, img_path.name):
            classified_count += 1
    
    total = len(folder_files)
    if classified_count == total:
        return 'fully_classified'
    elif classified_count == 0:
        return 'unclassified'
    else:
        return 'partly_classified'


def is_fully_classified(sku: str) -> bool:
    """Check if all folder images for a SKU are classified in JSON."""
    return get_classification_status(sku) == 'fully_classified'

# ============================================================================
# EBAY SCHEMA HELPERS
# ============================================================================

def load_schema_for_category(category_id: str) -> Dict:
    """
    Load eBay schema for a given category ID.
    Returns a dict with 'required' and 'optional' lists of aspects.
    Each aspect is: {'name': str, 'values': [str, ...]}
    Returns empty dict if schema doesn't exist.
    """
    if not category_id:
        return {}
    
    try:
        schema_filename = f"EbayCat_{category_id}_{config.MARKETPLACE_DE_ID}.json"
        schema_path = config.SCHEMAS_FOLDER_PATH / schema_filename
        
        if not schema_path.exists():
            return {}
        
        with schema_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract schema from the payload
        schema = data.get("schema", {})
        return {
            "required": schema.get("required", []),
            "optional": schema.get("optional", []),
            "metadata": data.get("_metadata", {})
        }
    except Exception as e:
        print(f"Error loading schema for category {category_id}: {e}")
        return {}


def schema_exists_for_category(category_id: str) -> bool:
    """Check if a schema file exists for the given category ID."""
    if not category_id:
        return False
    
    try:
        schema_filename = f"EbayCat_{category_id}_{config.MARKETPLACE_DE_ID}.json"
        schema_path = config.SCHEMAS_FOLDER_PATH / schema_filename
        return schema_path.exists()
    except Exception:
        return False
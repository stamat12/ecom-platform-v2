"""
State management for the ecommerceAI GUI application.

This module contains all global state containers and the SKUState dataclass.
Extracted from gui_nicegui.py during Phase 2 refactoring.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Set, Any


# ============================================================================
# STATE DATACLASS
# ============================================================================

@dataclass
class SKUState:
    """Per-SKU state for pagination, filters, and display settings."""
    sku: str
    grid_columns: int = 8
    page: int = 1
    page_size: int = 60
    image_filter: str = "all"  # Filter for image classification: 'all', 'phone', 'stock', 'enhanced'


# ============================================================================
# GLOBAL STATE CONTAINERS
# ============================================================================

# Per-SKU state instances
states: Dict[str, SKUState] = {}

# Per-SKU mount containers (will store ui.column references)
sku_mounts: Dict[str, Any] = {}

# SKU selection for actions (export, etc.)
sku_action_selected: Set[str] = set()

# Track selected fields per SKU for display
sku_selected_fields: Dict[str, Set[str]] = {}

# Selection is a set of absolute path strings for selected images
GLOBAL_SELECTED: Set[str] = set()

# Store image button references for quick updates
image_buttons: Dict[str, Any] = {}  # {image_path: ui.button}

# Store expansion control references globally
sku_expansions: Dict[str, Any] = {}  # {sku: ui.expansion}


# ============================================================================
# FILTER STATES
# ============================================================================

# Track whether all collapsibles should be open/closed
collapsibles_state = {'open': True}

# Track filter state for SKU display
filter_state = {'filter': 'all'}  # 'all', 'collected', 'missing'

# Track classification filter state separately
classification_filter_state = {'filter': 'all'}  # 'all', 'fully_classified', 'partly_classified', 'unclassified'

# Track main images filter state
main_images_filter_state = {'filter': 'all'}  # 'all', 'has_main_images', 'no_main_images'

# SKU list for Actions page (sent from Inventory page)
actions_sku_list: Set[str] = set()

# Track whether Actions page is showing user-selected SKUs (True) or loaded from file (False)
actions_skus_from_inventory: bool = False

# Metadata caching
_product_detail_cache: Dict[str, Any] = {}  # {sku: product_detail_json}
_classification_status_cache: Dict[str, str] = {}  # {sku: 'fully_classified'|'partly_classified'|'unclassified'}
_inventory_data_cache: Dict[str, Any] = {'data': None, 'valid': False}  # {data: DataFrame|None, valid: bool}

# State persistence
STATE_PERSISTENCE_FILE = Path(__file__).resolve().parent / ".state_cache.json"


# ============================================================================
# STATE HELPER FUNCTIONS
# ============================================================================

def get_state(sku: str) -> SKUState:
    """Get or create SKUState for a SKU."""
    if sku not in states:
        states[sku] = SKUState(sku=sku)
    return states[sku]


def clear_image_selection():
    """Clear all selected images."""
    GLOBAL_SELECTED.clear()


def clear_sku_selection():
    """Clear all selected SKUs for actions."""
    sku_action_selected.clear()


def reset_all_state():
    """Reset all state to initial values (useful for testing or restart)."""
    states.clear()
    sku_mounts.clear()
    sku_action_selected.clear()
    sku_selected_fields.clear()
    GLOBAL_SELECTED.clear()
    image_buttons.clear()
    sku_expansions.clear()
    collapsibles_state['open'] = True
    filter_state['filter'] = 'all'
    actions_sku_list.clear()
    _product_detail_cache.clear()
    _classification_status_cache.clear()
    _inventory_data_cache['data'] = None
    _inventory_data_cache['valid'] = False


# ============================================================================
# SKU LIST MANAGEMENT FOR ACTIONS PAGE
# ============================================================================

def set_actions_skus(skus: Set[str], from_inventory: bool = True):
    """Set the SKU list for the Actions page (called when sending from Inventory)."""
    global actions_skus_from_inventory
    actions_sku_list.clear()
    actions_sku_list.update(skus)
    actions_skus_from_inventory = from_inventory
    # Invalidate caches when SKU list changes
    clear_metadata_caches()
    # Persist to disk
    _save_state_to_disk()


def get_actions_skus() -> Set[str]:
    """Get the current SKU list for the Actions page."""
    return actions_sku_list.copy()


def add_sku_to_actions(sku: str):
    """Add a single SKU to the Actions list."""
    actions_sku_list.add(sku)


def remove_sku_from_actions(sku: str):
    """Remove a single SKU from the Actions list."""
    actions_sku_list.discard(sku)


def clear_actions_skus():
    """Clear all SKUs from the Actions list."""
    global actions_skus_from_inventory
    actions_sku_list.clear()
    actions_skus_from_inventory = False
    # Persist to disk
    _save_state_to_disk()


# ============================================================================
# METADATA CACHING
# ============================================================================

def cache_product_detail(sku: str, product_detail: Any):
    """Cache product detail for a SKU."""
    _product_detail_cache[sku] = product_detail


def get_cached_product_detail(sku: str) -> Any:
    """Get cached product detail for a SKU, or None if not cached."""
    return _product_detail_cache.get(sku)


def cache_classification_status(sku: str, status: str):
    """Cache classification status for a SKU."""
    _classification_status_cache[sku] = status


def get_cached_classification_status(sku: str) -> Any:
    """Get cached classification status for a SKU, or None if not cached."""
    return _classification_status_cache.get(sku)


def cache_inventory_data(inventory_data: Any):
    """Cache the entire inventory DataFrame."""
    _inventory_data_cache['data'] = inventory_data
    _inventory_data_cache['valid'] = True


def get_cached_inventory_data() -> Any:
    """Get cached inventory data if valid, else None."""
    if _inventory_data_cache['valid']:
        return _inventory_data_cache['data']
    return None


def clear_metadata_caches():
    """Invalidate all metadata caches (call when data changes)."""
    _product_detail_cache.clear()
    _classification_status_cache.clear()
    _inventory_data_cache['valid'] = False
    _inventory_data_cache['data'] = None
    classification_filter_state['filter'] = 'all'
    main_images_filter_state['filter'] = 'all'


# ============================================================================
# STATE PERSISTENCE
# ============================================================================

def _save_state_to_disk():
    """Save current SKU list to persistent cache file."""
    try:
        state_data = {
            'actions_skus': list(actions_sku_list),
            'from_inventory': actions_skus_from_inventory,
        }
        with STATE_PERSISTENCE_FILE.open('w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save state: {e}")


def _load_state_from_disk():
    """Load SKU list from persistent cache file if it exists."""
    global actions_skus_from_inventory
    try:
        if STATE_PERSISTENCE_FILE.exists():
            with STATE_PERSISTENCE_FILE.open('r', encoding='utf-8') as f:
                state_data = json.load(f)
            actions_sku_list.update(state_data.get('actions_skus', []))
            actions_skus_from_inventory = state_data.get('from_inventory', False)
            print(f"[State] Loaded {len(actions_sku_list)} SKUs from cache")
    except Exception as e:
        print(f"Warning: Failed to load state: {e}")


# Load state on module import
_load_state_from_disk()

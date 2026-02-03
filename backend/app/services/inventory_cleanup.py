"""Service to clean up duplicate SKUs in the inventory database."""

import sqlite3
from pathlib import Path
from typing import Dict, Any

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
DB_PATH = LEGACY / "cache" / "inventory.db"


def cleanup_duplicate_skus() -> Dict[str, Any]:
    """
    Remove duplicate SKUs from inventory table, keeping only the first occurrence.
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        if not DB_PATH.exists():
            return {"success": False, "message": f"Database not found: {DB_PATH}"}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get SKU column name (from config)
        import sys
        sys.path.insert(0, str(LEGACY))
        import config
        sku_col = config.SKU_COLUMN  # e.g., "SKU (Old)"
        
        # Check if inventory table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'")
        if not cursor.fetchone():
            return {"success": False, "message": "inventory table not found"}
        
        # Get total rows before cleanup
        cursor.execute("SELECT COUNT(*) FROM inventory")
        rows_before = cursor.fetchone()[0]
        
        # Find duplicates
        cursor.execute(f"""
            SELECT "{sku_col}", COUNT(*) as count 
            FROM inventory 
            WHERE "{sku_col}" IS NOT NULL 
            GROUP BY "{sku_col}" 
            HAVING count > 1
            ORDER BY count DESC
        """)
        duplicates = cursor.fetchall()
        
        if not duplicates:
            return {
                "success": True,
                "message": "No duplicate SKUs found",
                "stats": {
                    "rows_before": rows_before,
                    "rows_after": rows_before,
                    "rows_deleted": 0,
                    "duplicate_skus": []
                }
            }
        
        duplicate_skus = [dup[0] for dup in duplicates]
        total_duplicates = sum(dup[1] for dup in duplicates)
        
        # For each duplicate SKU, keep the first row and delete the rest
        # We identify "first" by rowid
        for sku, count in duplicates:
            # Get all rowids for this SKU, ordered by rowid
            cursor.execute(f"""
                SELECT rowid FROM inventory 
                WHERE "{sku_col}" = ? 
                ORDER BY rowid
            """, (sku,))
            rowids = [row[0] for row in cursor.fetchall()]
            
            # Delete all but the first
            if len(rowids) > 1:
                rowids_to_delete = rowids[1:]
                placeholders = ",".join("?" * len(rowids_to_delete))
                cursor.execute(f"DELETE FROM inventory WHERE rowid IN ({placeholders})", rowids_to_delete)
        
        conn.commit()
        
        # Get total rows after cleanup
        cursor.execute("SELECT COUNT(*) FROM inventory")
        rows_after = cursor.fetchone()[0]
        rows_deleted = rows_before - rows_after
        
        conn.close()
        
        return {
            "success": True,
            "message": f"Successfully cleaned up database. Removed {rows_deleted} duplicate rows.",
            "stats": {
                "rows_before": rows_before,
                "rows_after": rows_after,
                "rows_deleted": rows_deleted,
                "duplicate_skus_found": len(duplicate_skus),
                "sample_duplicates": duplicate_skus[:10]  # Show first 10
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error cleaning up database: {str(e)}"
        }

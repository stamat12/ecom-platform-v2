"""Service to selectively sync columns from Excel to SQLite database."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl import load_workbook

from app.services.excel_inventory import excel_inventory, _get_db_path

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
import sys
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def get_excel_sheets() -> List[str]:
    """Get list of sheet names from Excel file."""
    try:
        wb = load_workbook(config.INVENTORY_FILE_PATH)
        return wb.sheetnames
    except Exception as e:
        print(f"Error reading Excel sheets: {e}")
        return []


def get_excel_columns(sheet_name: str) -> List[str]:
    """Get list of column names from a specific Excel sheet."""
    try:
        df = pd.read_excel(config.INVENTORY_FILE_PATH, sheet_name=sheet_name, nrows=0)
        return list(df.columns)
    except Exception as e:
        print(f"Error reading columns from sheet {sheet_name}: {e}")
        return []


def sync_excel_to_db(sheet_name: str, columns: List[str]) -> Dict[str, Any]:
    """Sync specific columns from an Excel sheet to the corresponding database table.
    Matches rows by unique identifiers, updates existing rows and inserts new ones.
    
    Args:
        sheet_name: Name of the Excel sheet
        columns: List of column names to sync
    
    Returns:
        Dict with success, message, and stats
    """
    if not sheet_name or not columns:
        return {"success": False, "message": "Sheet name and columns are required"}

    # Map sheet names to table names (lowercase with underscores)
    table_name = sheet_name.lower().replace(" ", "_")

    # Define unique key columns for each sheet
    UNIQUE_KEYS = {
        "inventory": ["SKU (Old)"],
        "listings": ["SKU (Old)"],
        "expenses": ["Pay Date", "Invoice", "Partner"],  # Combo to identify an expense
        "income": ["Pay Date", "Platform", "Item Title", "Sale Date", "SKU (Old)"],  # Combo to identify a sale
        "ebay_categories": ["Category", "ID"],  # Category name + ID
    }

    # Tables that should be completely replaced (delete all, insert all)
    FULL_REPLACE_TABLES = ["income"]

    try:
        # Read Excel sheet
        df = pd.read_excel(config.INVENTORY_FILE_PATH, sheet_name=sheet_name)
        if df.empty:
            return {"success": False, "message": f"Sheet '{sheet_name}' is empty"}

        # Filter to only requested columns that exist
        available_cols = [c for c in columns if c in df.columns]
        if not available_cols:
            return {"success": False, "message": f"None of the requested columns exist in sheet '{sheet_name}'"}

        # Connect to database
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Check if table exists
            table_check = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            ).fetchone()
            
            if not table_check:
                return {"success": False, "message": f"Table '{table_name}' not found in database"}

            # Get all columns in the table
            table_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            db_columns = {r[1]: r[0] for r in table_info}  # {col_name: col_id}

            if not db_columns:
                return {"success": False, "message": f"Table '{table_name}' has no columns"}

            # Get unique key columns for this table
            unique_keys = UNIQUE_KEYS.get(table_name, [])
            if not unique_keys:
                return {"success": False, "message": f"No unique key defined for table '{table_name}'. Cannot safely sync."}

            # Verify all unique key columns exist in both Excel and DB
            missing_in_excel = [k for k in unique_keys if k not in df.columns]
            missing_in_db = [k for k in unique_keys if k not in db_columns]
            if missing_in_excel:
                return {"success": False, "message": f"Unique key columns missing in Excel: {missing_in_excel}"}
            if missing_in_db:
                return {"success": False, "message": f"Unique key columns missing in DB: {missing_in_db}"}

            print(f"[SYNC] Sheet: {sheet_name}, Table: {table_name}, Unique keys: {unique_keys}, Syncing cols: {available_cols}")

            rows_updated = 0
            rows_inserted = 0
            rows_failed = 0

            # Check if this table should be fully replaced
            if table_name in FULL_REPLACE_TABLES:
                print(f"[SYNC] {table_name} is marked for FULL REPLACEMENT - deleting all existing rows...")
                conn.execute(f'DELETE FROM "{table_name}"')
                conn.commit()

                # INSERT all rows fresh from Excel
                for idx, (_, row) in enumerate(df.iterrows()):
                    try:
                        all_values = {}
                        for db_col in db_columns.keys():
                            if db_col in df.columns:
                                val = row[db_col]
                                if pd.isna(val):
                                    val = None
                                elif hasattr(val, 'isoformat'):
                                    val = val.isoformat()
                                all_values[db_col] = val
                            else:
                                all_values[db_col] = None
                        
                        cols_str = ", ".join([f'"{col}"' for col in all_values.keys()])
                        placeholders = ", ".join(['?' for _ in all_values])
                        conn.execute(
                            f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})',
                            list(all_values.values()),
                        )
                        rows_inserted += 1

                    except Exception as e:
                        print(f"[SYNC ERROR] Row {idx}: {e}")
                        import traceback
                        traceback.print_exc()
                        rows_failed += 1

                conn.commit()
                print(f"[SYNC RESULT] Full replacement: inserted {rows_inserted} rows, failed {rows_failed}")
            
            else:
                # Smart sync: Load all existing rows from DB and match by unique key
                db_rows = {}
                all_db_rows = conn.execute(f'SELECT rowid, * FROM "{table_name}"').fetchall()
                for db_row in all_db_rows:
                    # Build unique key tuple
                    key_values = []
                    for key_col in unique_keys:
                        val = db_row[key_col]
                        # Normalize for comparison
                        if isinstance(val, str):
                            val = val.strip()
                        key_values.append(val)
                    key_tuple = tuple(key_values)
                    db_rows[key_tuple] = dict(db_row)

                print(f"[SYNC] Found {len(db_rows)} existing rows in database")

                # Sync rows - UPDATE existing by unique key, INSERT new
                for idx, (_, row) in enumerate(df.iterrows()):
                    try:
                        # Build unique key for this Excel row
                        key_values = []
                        for key_col in unique_keys:
                            val = row[key_col]
                            if pd.isna(val):
                                val = None
                            elif hasattr(val, 'isoformat'):
                                val = val.isoformat()
                            elif isinstance(val, str):
                                val = val.strip()
                            key_values.append(val)
                        key_tuple = tuple(key_values)

                        # Skip if unique key has None values
                        if None in key_values:
                            rows_failed += 1
                            continue

                        # Check if this row exists in database
                        existing_row = db_rows.get(key_tuple)

                        if existing_row:
                            # UPDATE existing row
                            updates = {}
                            for col in available_cols:
                                if col not in db_columns:
                                    continue
                                val = row[col]
                                if pd.isna(val):
                                    val = None
                                elif hasattr(val, 'isoformat'):
                                    val = val.isoformat()
                                updates[col] = val

                            if updates:
                                set_clause = ", ".join([f'"{col}" = ?' for col in updates.keys()])
                                conn.execute(
                                    f'UPDATE "{table_name}" SET {set_clause} WHERE rowid = ?',
                                    list(updates.values()) + [existing_row['rowid']],
                                )
                                rows_updated += 1
                        else:
                            # INSERT new row - include ALL columns from Excel
                            all_values = {}
                            for db_col in db_columns.keys():
                                if db_col in df.columns:
                                    val = row[db_col]
                                    if pd.isna(val):
                                        val = None
                                    elif hasattr(val, 'isoformat'):
                                        val = val.isoformat()
                                    all_values[db_col] = val
                                else:
                                    all_values[db_col] = None
                            
                            cols_str = ", ".join([f'"{col}"' for col in all_values.keys()])
                            placeholders = ", ".join(['?' for _ in all_values])
                            conn.execute(
                                f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})',
                                list(all_values.values()),
                            )
                            rows_inserted += 1

                    except Exception as e:
                        print(f"[SYNC ERROR] Row {idx}: {e}")
                        import traceback
                        traceback.print_exc()
                        rows_failed += 1

            # Invalidate cache
            if table_name == "inventory":
                excel_inventory.invalidate()

            return {
                "success": True,
                "message": f"Synced '{sheet_name}': updated {rows_updated} rows, inserted {rows_inserted} new rows",
                "rows_updated": rows_updated,
                "rows_inserted": rows_inserted,
                "rows_failed": rows_failed,
                "columns_synced": available_cols,
            }
        finally:
            conn.close()

    except Exception as e:
        print(f"[SYNC EXCEPTION] Error syncing Excel to DB: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"Error: {str(e)}"}

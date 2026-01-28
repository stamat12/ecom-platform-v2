import os
import re
import shutil
import datetime
import json
import time
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration & Setup ---

# Define Paths
AGENT_FILE_PATH = Path(__file__).resolve()
PROJECT_ROOT = AGENT_FILE_PATH.parent.parent  # Assumes agents/invoice_agent.py
INVOICES_DIR = PROJECT_ROOT.parent / "Invoices"
EXTRACTED_DIR = INVOICES_DIR / "Extracted"
EXCEL_PATH = PROJECT_ROOT / "Invoices.xlsx"
ENV_PATH = PROJECT_ROOT / ".env"

# Load Environment Variables from .env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"Warning: .env file not found at {ENV_PATH}")

# Configure Gemini
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "models/gemini-3-pro-preview"

if not API_KEY:
    print("CRITICAL: GOOGLE_API_KEY not found in .env or environment variables.")
else:
    genai.configure(api_key=API_KEY)

# Column Definitions
COLUMNS_INVENTORY = [
    "SKU (Old)", "Buying Entity", "Supplier", "Invoice", "Invoice Date",
    "Price Net", "Shipping Net", "Total Cost Net", "Supplier Number",
    "ISIN", "Supplier Title"
]

COLUMNS_INVOICES_LOG = [
    "Supplier", "Invoice", "Invoice Date", "PDF Filename", "Imported At"
]

# --- Helper Classes ---

class InvoiceItem:
    def __init__(self, description: str, unit_price: float, quantity: float, 
                 is_shipping: bool = False, supplier_number: str = "", isin: str = ""):
        self.description = description
        self.unit_price = unit_price
        self.quantity = quantity
        self.is_shipping = is_shipping
        self.supplier_number = supplier_number
        self.isin = isin

    @property
    def total_net(self):
        return self.unit_price * self.quantity

class InvoiceData:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.supplier = "Unknown"
        self.invoice_number = "Unknown"
        self.invoice_date = None
        self.buying_entity = ""
        self.items: List[InvoiceItem] = []

    def get_date_str(self):
        return self.invoice_date.strftime("%Y-%m-%d") if self.invoice_date else "1970-01-01"

# --- Core Logic ---

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts raw text from PDF using pdfplumber."""
    text_content = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
    except Exception as e:
        print(f"Error reading PDF text for {pdf_path.name}: {e}")
    return text_content

def parse_with_gemini(text_content: str) -> dict:
    """
    Sends invoice text to Gemini 3 Pro to extract structured JSON data.
    """
    if not API_KEY:
        return {}

    prompt = """
    You are an expert data entry specialist. Analyze the invoice text below and extract data into a strict JSON format.

    ### Instructions:
    1. **Dates:** Format as DD.MM.YYYY.
    2. **Numbers:** Convert European formats (e.g., "1.200,50") to standard floats (1200.50).
    3. **Shipping:** Identify any line items related to shipping, freight, porto, or delivery and mark "is_shipping": true.
    4. **Output:** Return ONLY valid JSON. Do not include markdown blocks.

    ### JSON Structure:
    {
      "supplier_name": "string",
      "invoice_number": "string",
      "invoice_date": "DD.MM.YYYY",
      "buying_entity": "string (person/company bill is addressed to)",
      "line_items": [
        {
          "description": "string",
          "quantity": float,
          "unit_price_net": float (price per single unit),
          "is_shipping": boolean,
          "supplier_sku": "string (optional)",
          "isin": "string (optional)"
        }
      ]
    }

    ### Invoice Text:
    """
    
    full_prompt = prompt + text_content[:100000] # Leverage massive context window

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  Gemini Error ({MODEL_NAME}): {e}")
        return {}

def extract_invoice_data(pdf_path: Path) -> InvoiceData:
    """Orchestrates the extraction process."""
    data = InvoiceData(pdf_path)
    
    # 1. Read PDF Text
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        print(f"  [Warn] No text found in {pdf_path.name} (image-based?). Skipping.")
        return data

    # 2. Extract with Gemini
    print(f"  Analyzing {pdf_path.name}...")
    ai_data = parse_with_gemini(raw_text)
    
    if not ai_data:
        return data

    # 3. Map JSON to InvoiceData
    data.supplier = ai_data.get("supplier_name", "Unknown")
    data.invoice_number = ai_data.get("invoice_number", "Unknown")
    data.buying_entity = ai_data.get("buying_entity", "")
    
    date_str = ai_data.get("invoice_date")
    if date_str:
        try:
            data.invoice_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            data.invoice_date = datetime.datetime.now()
    else:
        data.invoice_date = datetime.datetime.now()

    items_list = ai_data.get("line_items", [])
    for item in items_list:
        desc = item.get("description", "Item")
        # Handle cases where AI returns None for numeric fields
        qty = float(item.get("quantity") or 1.0)
        price = float(item.get("unit_price_net") or 0.0)
        is_ship = item.get("is_shipping", False)
        sku = item.get("supplier_sku", "")
        isin = item.get("isin", "")
        
        data.items.append(InvoiceItem(desc, price, qty, is_ship, sku, isin))

    return data

def get_next_sku(df_inventory: pd.DataFrame, prefix: str) -> str:
    """Finds the next sequential SKU based on the prefix."""
    if df_inventory.empty or "SKU (Old)" not in df_inventory.columns:
        return f"{prefix}00001"

    # Filter to SKUs starting with prefix
    relevant = df_inventory["SKU (Old)"].astype(str)
    relevant = relevant[relevant.str.startswith(prefix)]
    
    max_val = 0
    for sku in relevant:
        try:
            num_part = sku.replace(prefix, "")
            val = int(num_part)
            if val > max_val:
                max_val = val
        except ValueError:
            continue
            
    return f"{prefix}{max_val + 1:05d}"

def load_or_create_excel():
    """Handles loading the Excel database."""
    if EXCEL_PATH.exists():
        try:
            with pd.ExcelFile(EXCEL_PATH) as xls:
                df_inv = pd.read_excel(xls, "Inventory") if "Inventory" in xls.sheet_names else pd.DataFrame(columns=COLUMNS_INVENTORY)
                df_log = pd.read_excel(xls, "Invoices") if "Invoices" in xls.sheet_names else pd.DataFrame(columns=COLUMNS_INVOICES_LOG)
        except Exception:
            df_inv = pd.DataFrame(columns=COLUMNS_INVENTORY)
            df_log = pd.DataFrame(columns=COLUMNS_INVOICES_LOG)
    else:
        df_inv = pd.DataFrame(columns=COLUMNS_INVENTORY)
        df_log = pd.DataFrame(columns=COLUMNS_INVOICES_LOG)
    
    # Enforce column order and fill NaNs
    df_inv = df_inv.reindex(columns=COLUMNS_INVENTORY).fillna("")
    df_log = df_log.reindex(columns=COLUMNS_INVOICES_LOG).fillna("")
        
    return df_inv, df_log

def main():
    print(f"--- Invoice Agent (Model: {MODEL_NAME}) ---")
    
    # 1. Setup
    if not INVOICES_DIR.exists():
        print(f"Input directory not found: {INVOICES_DIR}")
        return
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    
    df_inventory, df_log = load_or_create_excel()
    
    # 2. Scanning & Deduplication
    pdf_files = list(INVOICES_DIR.glob("*.pdf"))
    new_invoices = []
    
    # Create a set of (Supplier, Invoice) tuples for fast lookup
    # Using string conversion to ensure type safety during comparison
    existing_records = set(zip(df_log["Supplier"].astype(str), df_log["Invoice"].astype(str)))
    
    print(f"Found {len(pdf_files)} PDFs.")
    
    for pdf in pdf_files:
        try:
            data = extract_invoice_data(pdf)
            
            # Deduplication Check
            key = (str(data.supplier), str(data.invoice_number))
            if key in existing_records:
                print(f"  [Skip] Duplicate: {data.supplier} - {data.invoice_number}")
                continue
                
            new_invoices.append(data)
            
        except Exception as e:
            print(f"  [Error] Failed to process {pdf.name}: {e}")

    if not new_invoices:
        print("No new invoices to import.")
        return

    # 3. Grouping by Supplier
    supplier_groups: Dict[str, List[InvoiceData]] = {}
    for inv in new_invoices:
        supplier_groups.setdefault(inv.supplier, []).append(inv)

    rows_inventory = []
    rows_log = []
    move_queue = [] # (src, dest)

    # 4. Processing Per Group
    for supplier, invoices in supplier_groups.items():
        print(f"\n--- Supplier Group: {supplier} ({len(invoices)} invoices) ---")
        
        # Prompt for Prefix
        prefix = input(f"Enter SKU prefix for '{supplier}' (e.g., MYA): ").strip().upper()
        
        # Calculate Starting SKU Number
        next_sku_str = get_next_sku(df_inventory, prefix)
        try:
            current_sku_num = int(next_sku_str.replace(prefix, ""))
        except:
            current_sku_num = 1
            
        # Global Shipping Aggregation for this group
        group_shipping_total = 0.0
        group_items = []
        
        for inv in invoices:
            inv_date_str = inv.get_date_str()
            
            # Log Entry
            rows_log.append({
                "Supplier": inv.supplier,
                "Invoice": inv.invoice_number,
                "Invoice Date": inv_date_str,
                "PDF Filename": inv.filename,
                "Imported At": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Prepare file move
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', f"{inv.supplier}_{inv_date_str}_{inv.invoice_number}.pdf")
            move_queue.append((inv.filepath, EXTRACTED_DIR / safe_filename))
            
            for item in inv.items:
                if item.is_shipping:
                    group_shipping_total += item.total_net
                else:
                    # Flatten item with parent invoice metadata
                    group_items.append({
                        "item": item,
                        "inv_date": inv.invoice_date,
                        "inv_num": inv.invoice_number,
                        "inv_obj": inv
                    })

        # Sort items: Date ASC -> Invoice Num ASC
        group_items.sort(key=lambda x: (x["inv_date"], x["inv_num"]))

        # Shipping Allocation (Even split)
        item_count = len(group_items)
        shipping_per_item = group_shipping_total / item_count if item_count > 0 else 0.0
        
        print(f"  Total items: {item_count}. Total Shipping: {group_shipping_total:.2f}. Allocated: {shipping_per_item:.4f}/item")

        # Create Inventory Rows
        for entry in group_items:
            item = entry["item"]
            inv = entry["inv_obj"]
            
            sku = f"{prefix}{current_sku_num:05d}"
            current_sku_num += 1
            
            price_net = round(item.total_net, 4)
            ship_net = round(shipping_per_item, 4)
            total_cost = round(price_net + ship_net, 4)
            
            rows_inventory.append({
                "SKU (Old)": sku,
                "Buying Entity": inv.buying_entity,
                "Supplier": inv.supplier,
                "Invoice": inv.invoice_number,
                "Invoice Date": inv.get_date_str(),
                "Price Net": price_net,
                "Shipping Net": ship_net,
                "Total Cost Net": total_cost,
                "Supplier Number": item.supplier_number,
                "ISIN": item.isin,
                "Supplier Title": item.description
            })
            
            # Sync back to in-memory DF to keep track of SKU counts for subsequent groups
            new_row = pd.DataFrame([rows_inventory[-1]])
            df_inventory = pd.concat([df_inventory, new_row], ignore_index=True)

    # 5. Save & Clean Up
    if rows_inventory:
        print("\nWriting to Excel...")
        try:
            with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode="w") as writer:
                # Write Inventory
                df_inventory.to_excel(writer, sheet_name="Inventory", index=False)
                
                # Update and Write Logs
                if rows_log:
                    new_log_df = pd.DataFrame(rows_log)
                    df_log = pd.concat([df_log, new_log_df], ignore_index=True)
                df_log.to_excel(writer, sheet_name="Invoices", index=False)
                
            print("Excel updated successfully.")
            
            print("Moving processed files...")
            for src, dest in move_queue:
                try:
                    if dest.exists():
                        ts = datetime.datetime.now().strftime("%H%M%S")
                        dest = dest.parent / f"{dest.stem}_{ts}{dest.suffix}"
                    shutil.move(src, dest)
                except Exception as e:
                    print(f"Error moving {src.name}: {e}")
                    
        except Exception as e:
            print(f"CRITICAL ERROR Saving Excel: {e}")
            print("Files have NOT been moved to prevent data loss.")

    print("\n--- Done ---")

if __name__ == "__main__":
    main()

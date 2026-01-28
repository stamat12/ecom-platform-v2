import os
import pandas as pd
import google.generativeai as genai
from google.cloud import vision
from dotenv import load_dotenv
import mimetypes
from io import StringIO
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

# --- Configuration ---
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Setup Google Cloud Credentials
if GOOGLE_CREDENTIALS_FILE and os.path.exists(GOOGLE_CREDENTIALS_FILE):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_FILE
else:
    print("Warning: Google Cloud Credentials not found. OCR will fail.")

# --- Dynamic Path Configuration ---
PROJECT_ROOT = os.getcwd()
# Attempt to find the cloud directory (adjust usually 1-3 levels up depending on your setup)
try:
    CLOUD_DIRECTORY = os.path.dirname(os.path.dirname(PROJECT_ROOT))
    if "Users" not in CLOUD_DIRECTORY: 
        CLOUD_DIRECTORY = os.path.dirname(PROJECT_ROOT)
except:
    CLOUD_DIRECTORY = os.path.dirname(PROJECT_ROOT)

# Folders where images might be located
SKU_IMAGE_BASE_FOLDERS = [
    os.path.join(CLOUD_DIRECTORY, "AUCTIONS_SEGMENT", "Auktionen", "_FOTOS"),
    os.path.join(CLOUD_DIRECTORY, "HANDEL_SEGMENT", "Images"),
    os.path.join(CLOUD_DIRECTORY, "TRADING_SEGMENT", "Images")
]

SKU_LIST_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "engine_test.xlsx")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "ean_price_output.xlsx")

# --- Helper Functions ---

def read_skus(file_path):
    """Reads SKUs from the first column of Excel."""
    try:
        df = pd.read_excel(file_path, header=None)
        return df[0].astype(str).tolist()
    except Exception as e:
        print(f"Error reading SKU file: {e}")
        return []

def find_sku_folder(sku, base_folders):
    """Locates the specific folder for a SKU."""
    for base_folder in base_folders:
        potential_path = os.path.join(base_folder, str(sku))
        if os.path.isdir(potential_path):
            return potential_path
    return None

def scan_barcodes_local(image_paths):
    """Scans for EAN-13 barcodes using local processor (pyzbar)."""
    found = []
    for path in image_paths:
        try:
            with Image.open(path) as img:
                results = decode(img, symbols=[ZBarSymbol.EAN13])
                for r in results:
                    found.append(r.data.decode("utf-8"))
        except Exception:
            continue
    return list(set(found))

def scan_text_ocr(image_paths):
    """Uses Google Cloud Vision to read ALL text from tags (for price finding)."""
    full_text = ""
    try:
        client = vision.ImageAnnotatorClient()
        for path in image_paths:
            with open(path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            if response.text_annotations:
                full_text += response.text_annotations[0].description + "\n"
    except Exception as e:
        print(f"  > OCR Error: {e}")
    return full_text

def extract_ean_price_ai(image_paths, scanned_text, potential_eans):
    """Uses Gemini to supervise the EAN and extract the Price from text."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')

    eans_str = ", ".join(potential_eans) if potential_eans else "None"

    prompt = f"""
    You are a data extraction specialist.
    
    **Input Data:**
    1. Potential EANs found by scanner: [{eans_str}]
    2. Raw Text found on tags: "{scanned_text[:3000]}"
    
    **Task:**
    1. **EAN:** Confirm the correct 13-digit EAN from the list. If the list is empty, try to read it from the image.
    2. **Price:** Find the price on the tag text. Look for numbers near currency symbols (€, EUR). 
       - Ignore crossed-out prices (old prices).
       - Look for "UVP" or standard retail prices.
    
    **Output JSON:**
    {{
        "ean": "The best 13-digit EAN string (or null if none)",
        "price": "The price as a number (e.g. 29.99) (or null if none)"
    }}
    """
    
    prompt_parts = [prompt]
    # Attach images so AI can visually confirm (e.g. distinguish sale price from regular)
    for path in image_paths:
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            with open(path, 'rb') as f:
                prompt_parts.append({'mime_type': mime_type, 'data': f.read()})

    try:
        response = model.generate_content(prompt_parts)
        cleaned = response.text.strip().replace("```json", "").replace("```", "")
        return pd.read_json(StringIO(cleaned), typ='series')
    except Exception as e:
        print(f"  > AI Extraction Error: {e}")
        return None

# --- Main Execution ---

if __name__ == "__main__":
    print("--- Starting EAN & Price Extractor ---")
    
    skus = read_skus(SKU_LIST_FILE)
    results = []
    
    print(f"Processing {len(skus)} SKUs...")

    for sku in skus:
        print(f"\nSKU: {sku}")
        
        # 1. Find Images
        folder = find_sku_folder(sku, SKU_IMAGE_BASE_FOLDERS)
        if not folder:
            print("  > Folder not found.")
            continue
            
        images = [os.path.join(folder, f) for f in os.listdir(folder) 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if not images:
            print("  > No images found.")
            continue

        # 2. Hard Scanning (Barcode + Text)
        local_eans = scan_barcodes_local(images)
        tag_text = scan_text_ocr(images)
        
        # 3. AI Extraction
        data = extract_ean_price_ai(images, tag_text, local_eans)
        
        ean = ""
        price = ""
        
        if data is not None:
            ean = data.get("ean", "")
            price = data.get("price", "")
            print(f"  > Found: EAN={ean}, Price={price}")
        else:
            print("  > AI failed to extract data.")

        results.append({
            "SKU": sku,
            "EAN": ean,
            "Price": price
        })

    # Save
    if results:
        pd.DataFrame(results).to_excel(OUTPUT_FILE, index=False)
        print(f"\nSaved {len(results)} items to {OUTPUT_FILE}")
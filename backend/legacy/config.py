"""Configuration module for ecommerceAI project."""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

# Navigate to TRADING_SEGMENT directory
# From: .../TRADING_SEGMENT/ecom-platform-v2/backend/legacy/config.py
# We need: .../TRADING_SEGMENT/
TRADING_ROOT = Path(__file__).resolve().parents[3]

# Root cloud storage directory
CLOUD_ROOT = TRADING_ROOT.parent

# Poppler directory for PDF processing
POPPLER_PATH = TRADING_ROOT / "Invoices" / "poppler-25.12.0" / "Library" / "bin"

# Inventory management
# Main inventory data source
INVENTORY_FILE_PATH = TRADING_ROOT / "Inventory.xlsx"

# SKU file path
SKU_FILE_PATH = PROJECT_ROOT / "sku.xlsx"

# Folders paths
AGENTS_FOLDER_PATH = PROJECT_ROOT / "agents"
SCHEMAS_FOLDER_PATH = PROJECT_ROOT / "schemas"
PRODUCTS_FOLDER_PATH = PROJECT_ROOT / "products"

# Names of the sheets in the inventory file
INVENTORY_SHEET_NAME = "Inventory"
LISTINGS_SHEET_NAME = "Listings"
CATEGORY_SHEET_NAME = "Ebay Categories"

# Names of the columns in the Inventory sheet of the inventory file
SKU_COLUMN = "SKU (Old)"
BUYING_ENTITY_COLUMN = "Buying Entity"
SUPPLIER_COLUMN = "Supplier"
INVOICE_COLUMN = "Invoice"
INVOICE_DATE_COLUMN = "Invoice Date"
PRICE_NET_COLUMN = "Price Net"
SHIPPING_NET_COLUMN = "Shipping Net"
TOTAL_COST_NET_COLUMN = "Total Cost Net"
SUPPLIER_NUMBER_COLUMN = "Supplier Number"
ISIN_COLUMN = "ISIN"
TITLE_COLUMN = "Supplier Title"
CATEGORY_COLUMN = "Category"
EAN_COLUMN = "EAN"
CONDITION_COLUMN = "Condition"
GENDER_COLUMN = "Gender"
BRAND_COLUMN = "Brand"
COLOR_COLUMN = "Color"
SIZE_COLUMN = "Size"
MORE_DETAILS_COLUMN = "More details"
MATERIALS_COLUMN = "Materials"
OP_COLUMN = "OP"
KEYWORDS_COLUMN = "Keywords"
STATUS_COLUMN = "Status"
LAGER_COLUMN = "Lager"
JSON_COLUMN = "JSON"
IMAGES_JSON_PHONE_COLUMN = "Images JSON Phone"
IMAGES_JSON_STOCK_COLUMN = "Images JSON Stock"
IMAGES_JSON_ENHANCED_COLUMN = "Images JSON Enhanced"

READY_STATUS_VALUE = "Ready"
OK_STATUS_VALUE = "OK"

# OpenAI model name for product field completion
OPENAI_MODEL = "gpt-4-vision-preview"

# Names of the columns in the Listings sheet of the inventory file
LISTINGS_SKU_COLUMN = "SKU (Old)"
LISTINGS_TITLE_COLUMN = "Title"
LISTINGS_DESCRIPTION_COLUMN = "Text Description"

# Names of the columns in the Ebay Categories sheet of the inventory file
CATEGORY_TITLE_COLUMN = "Category" 
CATEGORY_ID_COLUMN = "ID"
PAYMENT_FEE_COLUMN = "Payment Fee"
FINAL_AMOUNT_UP_TO_COLUMN = "Up To"
SALES_COMMISSION_UP_TO_COLUMN = "Sales commission per item Up To"
FINAL_AMOUNT_FROM_COLUMN = "From"
SALES_COMMISSION_FROM_COLUMN = "Sales commission per item From"

# eBay Marketplace Setup
MARKETPLACE_DE_ID = "EBAY_DE"

# eBay API Configuration
EBAY_API_ENDPOINT = "https://api.ebay.com/ws/api.dll"
EBAY_COMPATIBILITY_LEVEL = "1149"
EBAY_SITE_ID = "77"  # 77 = Germany (DE)
EBAY_LOCATION_COUNTRY = "AT"
EBAY_LOCATION_CITY = "Wien"
EBAY_LOCATION_POSTALCODE = "1210"
EBAY_PAYMENT_POLICY_NAME = "EbayZahlungen"
EBAY_RETURN_POLICY_NAME = "14TageRücknahme"
EBAY_SHIPPING_POLICY_NAME = "Deutschland_bis50cm_KOSTENLOS"

# eBay Condition Mapping: German text to eBay ConditionID
CONDITION_MAPPING = {
    "Neu mit Karton": 1000,
    "Neu mit Etiketten": 1000,
    "Neu ohne Karton": 1500,
    "Neu mit Fehlern": 1750,
    "Generalüberholt": 2000,
    "Gebraucht": 3000,
    "Sehr gut": 4000,
    "Gut": 5000,
    "Akzeptabel": 6000,
}

# Search Paths
IMAGE_FOLDER_PATHS = [
    Path("../Images"),
    Path("../../HANDEL_SEGMENT/Images"),
    Path("../../AUCTIONS_SEGMENT/Auktionen/_FOTOS"),
    Path("../../BAGS_SEGMENT/Images")
]

MODEL_IMAGE = "gemini-2.5-flash-image"
MODEL_FIELD_COMPLETION = "gpt-4o-mini"
MODEL_MANUFACTURER_LOOKUP = "gpt-4o-mini"  # For manufacturer information extraction

MANUFACTURER_PROMPT = """
You are a research assistant helping an e-commerce seller in the EU.

Task:
Find the OFFICIAL manufacturer or main company information for the brand "{brand}".
Try to find:
1. The main company/headquarters in the EU / DACH region
2. OR the official EU distributor/representative
3. OR the international headquarters if brand is based outside EU

Search Strategy:
- Check the official brand website for contact/imprint/about pages
- Look for "Contact", "About Us", "Impressum", "Imprint" sections
- For smaller brands, the company address might be on their online shop footer
- If main HQ is outside EU (e.g. USA, China), try to find their EU office/distributor

IMPORTANT:
- If you CANNOT find ANY real information after thorough search, return: {{"error": "No verified manufacturer data found"}}
- Do NOT generate placeholder, example, or fake data like "Musterstraße", "info@example.com", etc.
- It's OK if you can't find phone/email - just provide address info you can verify
- Provide what you CAN find, don't reject partial data

Return ONLY a JSON object with these EXACT keys:

- "CompanyName": Full legal name of the company (string)
- "Street1": Main street and house number (string)
- "Street2": Additional address line if needed, otherwise "" (string)
- "CityName": City (string)
- "StateOrProvince": State, province or Bundesland if applicable, otherwise "" (string)
- "PostalCode": Postal code (string)
- "Country": 2-letter country code like "DE", "AT", "UK", "FR", "IT", "NL", etc. (string)
- "Phone": Main customer service or company phone (optional, use "" if not found) (string)
- "Email": Official contact email (optional, use "" if not found) (string)
- "ContactURL": Official contact/support page URL (optional, use "" if not found) (string)

RULES:
- "Country" MUST be a 2-letter country code (e.g. "DE", "AT", "FR", "UK", "ES", "IT", "NL").
- "Phone" if found, MUST include country code starting with "00" (not "+"), no spaces/brackets/dashes. Example: "0049301234567"
- "Phone", "Email", "ContactURL" can be "" if you can't find them - focus on getting address right

Output:
Return ONLY valid JSON, no explanation, no comments.
"""

PROMPTS = {
    "studio_restoration": (
        "Task: Transform this amateur product photograph into a premium, professional e-commerce studio shot. "
        "Goal: The product must look pristine and high-quality, while maintaining pixel-perfect fidelity to all original text and branding details. "
        "1. Background & Isolation: Isolate the product perfectly from the floor background. Place it on a seamless, pure white background (#FFFFFF). "
        "2. General Surface Enhancement (Non-Text Areas): On the main fabric and materials *only*, gently smooth out unsightly wrinkles, creases, and remove dust or dirt to create a flawless, new appearance. Ensure materials look premium. "
        "3. CRITICAL: Extreme Text and Label Preservation (PROTECTED ZONES): "
        "The model MUST NOT apply any smoothing, denoising, blurring, or 'cleaning' effects to areas containing text, logos, or small labels. "
        "All alphanumeric text, branding details (like 'NIKE GRIPKNIT'), sizing tags, and fine print must remain incredibly SHARP, CRISP, and LEGIBLE. "
        "Treat these areas as protected high-fidelity zones. It is better to leave a tiny imperfection near text than to blur the text itself. The text must be identical to the source image, just cleaner. "
        "4. Perspective & Lighting: Strictly maintain the exact camera angle and perspective seen in the input image. "
        "Do not rotate or tilt the object. Replace the amateur lighting with professional, soft, even studio lighting that defines the form. "
        "Add a subtle, realistic contact shadow on the white floor so the product does not look like it is floating. "
        "5. Framing: Center the product fully within the frame with balanced white space."
    ),
    
    "studio_restoration_2": (
        "Task: High-Fidelity Background Replacement & Studio Lighting Composition. "
        "Goal: Isolate the product EXACTLY as it appears in the source image onto a white background. "
        "1. Background: Seamless pure white (#FFFFFF). Add a natural, soft contact shadow to ground the object. "
        "2. Source Fidelity (CRITICAL): Do NOT 'regenerate', 'repaint', or 'smooth' the product texture. "
        "The goal is to preserve the authentic reality of the item, not to create a 3D render. "
        "Keep the original fabric texture and material definition exactly as provided in the input. "
        "3. Text Protection: The text, logos, and labels (e.g., 'NIKE GRIPKNIT', size tags) must be preserved pixel-for-pixel from the original. "
        "Do not apply any denoising or beautification filters to text areas. They must remain sharp and readable. "
        "4. Lighting: Adjust only the global exposure and contrast to match a professional studio look. "
        "Do not alter the local shadows or highlights on the shoe itself to ensure the design remains 100% accurate. "
        "5. Framing: Center the product with balanced white space."
    ),
    
    "studio_restoration_3": (
        "Task: Technical Background Replacement & Color Correction ONLY. "
        "Goal: Isolate the product exactly as it appears in the source image onto a white background. "
        "1. STRICT OBJECT PRESERVATION (CRITICAL): Do NOT redraw, re-render, repaint, or 'clean' the product structure. "
        "The pixels constituting the shoes (fabric texture, laces, and especially TEXT/LOGOS) must remain identical to the source image. "
        "Do not attempt to fix wrinkles or texture if it risks altering the text. Authenticity is the priority over 'perfect' smoothness. "
        "2. Text & Label Integrity: Absolutely NO smoothing, blurring, or changing of text areas (e.g., 'NIKE GRIPKNIT', tags). "
        "Treat the product as a 'protected layer' that cannot be modified, only brightened. "
        "3. Background: Replace the floor with seamless pure white (#FFFFFF). "
        "4. Lighting Adjustment: Apply GLOBAL brightness and contrast adjustments only to match studio standards. "
        "Do not change the lighting direction or cast new shadows on the shoe structure itself. "
        "5. Output: The result should look like the original photo was skillfully cut out and placed on white, NOT like a 3D render or a generated image."
    ),
    "studio_restoration_ultra_gpt": (
        "Task: Convert this amateur product photo into a premium, professional studio image.\n"
        "Objective: Produce a pristine e-commerce shot on pure white while preserving EVERY pixel-level detail of the original product.\n"
        "\n"
        "STRICT RULES:\n"
        "1) Background & Isolation\n"
        "   - Remove the original background completely.\n"
        "   - Place the product on seamless pure white (#FFFFFF).\n"
        "   - Add a soft, realistic contact shadow directly underneath.\n"
        "   - Do NOT rotate, tilt, flip, or alter the camera angle/perspective.\n"
        "\n"
        "2) Professional Finish (Without Altering Product)\n"
        "   - Remove dust/dirt/debris only on non-text areas.\n"
        "   - Subtle surface smoothing is allowed but must not remove true texture.\n"
        "   - Do NOT alter shape, geometry, curvature, or material structure.\n"
        "\n"
        '3) Absolute Design Preservation (CRITICAL)\n'
        "   - Colors must remain EXACT: no recoloring or tone shifts.\n"
        "   - Preserve stitching, patterns, textures, gradients, and materials.\n"
        "   - No regeneration or “beautifying” of design features.\n"
        "\n"
        "4) Text, Labels & Micro-Elements (Pixel-Perfect Accuracy)\n"
        "   - Preserve ALL micro-details EXACTLY as they appear, including:\n"
        "     printed/woven text, logos/branding, numbers/product codes, size/inner labels,\n"
        "     stitching patterns, perforations, mesh, fabric weave, seam lines, edge contours.\n"
        "   - Do NOT redraw, smooth, sharpen, replace, or modify any text or logo pixels.\n"
        "   - Text must match original pixel-by-pixel: same font, size, thickness, orientation,\n"
        "     spacing, curvature, and imperfections. If partially visible, keep it exactly so.\n"
        "\n"
        "5) Pixel-Lock Rule (Strongest Protection)\n"
        "   - Treat all micro-details (text/labels/logos/stitching) as LOCKED/immutable.\n"
        "   - Only background removal and lighting enhancement are allowed around them.\n"
        "   - No hallucination, guessing, or filling in missing areas on the product itself.\n"
        "\n"
        "6) Lighting\n"
        "   - Use soft, even, professional studio lighting.\n"
        "   - Improve clarity without altering true colors or hiding details via glare/overexposure.\n"
        "\n"
        "7) Framing\n"
        "   - Center the product with balanced white space; maintain true proportions and scale.\n"
        "\n"
        "Output: ONLY the restored product on pure white with a subtle realistic shadow—NO changes to product details.\n"
    ),
    "background_remover": (
        "Task: Strict Foreground Extraction / Background Removal ONLY. "
        "Goal: Isolate the foreground objects (the two shoes) exactly as they appear pixel-for-pixel in the source image. "
        "1. Operation: Perform a precise segmentation cut-out of the shoes. "
        "2. Background: Replace the wooden floor completely with a solid, neutral color (like pure white #FFFFFF) or transparent pixels if supported. "
        "3. ZERO ALTERATION POLICY (CRITICAL): Do NOT change the subject. "
        "Do not clean, smooth, relight, enhance, or 'fix' the shoes. "
        "All wrinkles, dirt, textures, and crucially ALL TEXT and LOGOS must remain exactly as blurred or sharp as they are in the original photo. "
        "Your only job is cutting them out accurately. Do not be creative. "
        "4. Output: The original shoe pixels isolated on a clean background."
    )
}

PDF_MAX_PAGES = 2
PARSER_ORDER = ["camelot_lattice", "camelot_stream", "tabula"]
OCR_ENGINE = "tesseract"          # or "paddleocr"
OCR_LANGS = "deu+eng"
USE_LLM_NORMALIZATION = True
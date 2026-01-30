"""
eBay API and business configuration
"""
import os
from typing import Dict

# eBay API Endpoints
EBAY_API_ENDPOINT = "https://api.ebay.com/ws/api.dll"
EBAY_SANDBOX_ENDPOINT = "https://api.sandbox.ebay.com/ws/api.dll"
EBAY_TAXONOMY_ENDPOINT = "https://api.ebay.com/commerce/taxonomy/v1"
EBAY_SANDBOX_TAXONOMY_ENDPOINT = "https://api.sandbox.ebay.com/commerce/taxonomy/v1"

# API Configuration
EBAY_COMPATIBILITY_LEVEL = "1149"
EBAY_SITE_ID = "77"  # Germany
MARKETPLACE_ID = "EBAY_DE"

# Use sandbox mode (set to False for production)
USE_SANDBOX = os.getenv("EBAY_USE_SANDBOX", "true").lower() == "true"

# Get appropriate endpoints based on sandbox mode
def get_api_endpoint() -> str:
    return EBAY_SANDBOX_ENDPOINT if USE_SANDBOX else EBAY_API_ENDPOINT

def get_taxonomy_endpoint() -> str:
    return EBAY_SANDBOX_TAXONOMY_ENDPOINT if USE_SANDBOX else EBAY_TAXONOMY_ENDPOINT

# Location Settings
LOCATION_COUNTRY = "AT"
LOCATION_CITY = "Wien"
LOCATION_POSTALCODE = "1210"

# Business Policies (from env or defaults)
PAYMENT_POLICY_NAME = os.getenv("EBAY_PAYMENT_POLICY", "EbayZahlungen")
RETURN_POLICY_NAME = os.getenv("EBAY_RETURN_POLICY", "14TageRücknahme")
SHIPPING_POLICY_NAME = os.getenv("EBAY_SHIPPING_POLICY", "Deutschland_bis50cm_KOSTENLOS")

# Listing Settings
DEFAULT_SCHEDULE_DAYS = 14
DEFAULT_LISTING_DURATION = "GTC"  # Good 'Til Cancelled
DEFAULT_QUANTITY = 1

# Condition Mapping (German text → eBay Condition ID)
CONDITION_MAPPING: Dict[str, int] = {
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

# eBay Field Enrichment Settings
EBAY_ENRICHMENT_MODEL = "gpt-4o-mini"
EBAY_ENRICHMENT_TEMP = 0.1
EBAY_ENRICHMENT_MAX_TOKENS = 800

# Manufacturer Lookup Settings
MANUFACTURER_CACHE_DURATION_DAYS = 90
MANUFACTURER_LOOKUP_MODEL = "gpt-4o"
MANUFACTURER_LOOKUP_TEMP = 0
MANUFACTURER_LOOKUP_MAX_TOKENS = 500

# Image Upload Settings
EBAY_MAX_IMAGES = 12
EBAY_IMAGE_SIZE_LIMIT_MB = 12

# Listing Template Settings
LISTING_BANNER_URL = os.getenv("EBAY_BANNER_URL", "https://i.postimg.cc/523Rftvm/I-Love-You-So-Much-1.jpg")
LISTING_RETURN_POLICY_DAYS = 14
LISTING_SHIPPING_INFO = "Kostenloser Versand innerhalb Deutschlands"

# Cache Settings
SCHEMA_CACHE_DIR = "schemas"
LISTINGS_CACHE_FILE = "cache/ebay_listings_cache.json"
MANUFACTURERS_CACHE_FILE = "cache/ebay_manufacturers.json"
LISTINGS_CACHE_DURATION_HOURS = 6

# Enrichment Prompt Template
EBAY_FIELD_ENRICHMENT_PROMPT = """Du bist ein Produktdaten-Spezialist für eBay-Listings.

Aufgabe: Fülle die folgenden eBay-Produktfelder AUSSCHLIESSLICH basierend auf den bereitgestellten Produktfotos aus.

Kategorie: {category_name}
eBay Kategorie ID: {category_id}

ERFORDERLICHE FELDER (müssen ausgefüllt werden):
{required_fields}

OPTIONALE FELDER (falls erkennbar):
{optional_fields}

AKTUELLE WERTE (bereits ausgefüllt):
{current_values}

WICHTIGE REGELN:
1. Fülle NUR leere Felder aus - überschreibe KEINE bereits ausgefüllten Werte
2. Verwende wenn möglich die erlaubten Werte aus der Liste
3. Wenn erlaubte Werte angegeben sind, wähle EXAKT einen davon
4. Wenn keine erlaubten Werte angegeben sind, gib eine präzise Beschreibung
5. Antworte auf Deutsch
6. Wenn du ein Feld nicht sicher bestimmen kannst, lasse es leer
7. Gib NUR die Felder zurück, die du ausfüllen möchtest

Antworte im folgenden JSON-Format:
{{
  "required": {{
    "Feldname1": "Wert1",
    "Feldname2": "Wert2"
  }},
  "optional": {{
    "Feldname3": "Wert3"
  }}
}}
"""

# Manufacturer Lookup Prompt
MANUFACTURER_LOOKUP_PROMPT = """
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

# Listing Description HTML Template (exact match from old project)
LISTING_DESCRIPTION_TEMPLATE = (
    '<img src="https://i.postimg.cc/523Rftvm/I-Love-You-So-Much-1.jpg" style="width:100%; max-width:100%; height:auto; display:block; margin:0 auto;" alt="Header Banner">'
    '<h2 style="text-align:center; color:#FF0000; margin-top:0.5em; margin-bottom:0.5em;">🏷️ {title}</h2>'
    '<div style="text-align:center;">'
    '{description_block}'
    '<div style="margin-top:1.5em;"><strong><span style="color:#008000;">'
    'Sie möchten mehr über die Passform oder weitere Details erfahren? '
    'Geben Sie einfach die Produktbezeichnung oder Artikelnummer online ein – '
    'dort finden Sie zusätzliche Informationen und Bilder.'
    '</span></strong></div>'
    '<div style="font-size:20px; margin-top:1.5em;"><strong><span style="color:#FF0000;">Versand</span></strong>'
    ' 📦 – erfolgt <b>innerhalb von 2 Werktagen</b>!'
    '</div>'
    '<div style="font-size:20px; margin-top:0.75em;"><strong><span style="color:#FF0000;">14 Tage Rückgaberecht</span></strong> ↩️ – '
    '<span style="color:#0039f3;"><strong><i>risikofrei einkaufen!</i></strong></span><br>'
    '<strong style="display:inline-block; margin-top:0.25em;"><span style="color:#FF0000;">Sparen</span></strong>💸: '
    'Entdecken Sie all unsere Angebote und die wöchentlichen Schnäppchen-Auktionen – '
    '<span style="color:#0039f3;"><i><strong>mit Kombiversand sparen Sie Versandkosten</strong></i></span>!'
    '</div>'
    '<div style="font-size:20px; margin-top:0.75em;"><strong><span style="color:#FF0000;">Bei Fragen</span></strong>💬 – '
    'Wir antworten <i><strong><span style="color:#0039f3;">innerhalb von 24h!</span></strong></i>'
    '</div>'
    '</div>'
    '<div style="text-align:center; font-size:20px; margin-top:1.5em; margin-bottom:1em;"><br></div>'
    '<p style="text-align:center; margin-bottom:1em;"><br></p>'
)

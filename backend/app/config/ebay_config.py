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
MANUFACTURER_LOOKUP_TEMP = 0.3
MANUFACTURER_LOOKUP_MAX_TOKENS = 500

# Image Upload Settings
EBAY_MAX_IMAGES = 12
EBAY_IMAGE_SIZE_LIMIT_MB = 12

# Listing Template Settings
LISTING_BANNER_URL = os.getenv("EBAY_BANNER_URL", "")
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
MANUFACTURER_LOOKUP_PROMPT = """Du bist ein Recherche-Assistent für Herstellerinformationen.

Aufgabe: Finde die offizielle Kontaktadresse des Herstellers/der Marke: "{brand}"

ANFORDERUNGEN:
1. Suche nach der offiziellen EU- oder Deutschland-Adresse
2. Priorisiere deutsche oder österreichische Adressen
3. Gib vollständige Kontaktdaten zurück

Antworte im JSON-Format:
{{
  "company_name": "Offizieller Firmenname",
  "street": "Straße und Hausnummer",
  "city": "Stadt",
  "state": "Bundesland/Region (optional)",
  "postal_code": "PLZ",
  "country": "Land",
  "email": "Kontakt-Email (falls verfügbar)",
  "phone": "Telefonnummer (falls verfügbar)"
}}

Wenn du keine verlässlichen Informationen findest, gib null zurück.
"""

# Listing Description HTML Template
LISTING_DESCRIPTION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .banner {{ width: 100%; margin-bottom: 20px; }}
        .section {{ margin-bottom: 20px; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #e67e22; padding-bottom: 5px; }}
        .details {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
        .details p {{ margin: 5px 0; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    {banner}
    
    <div class="section">
        <h2>Produktbeschreibung</h2>
        <div class="details">
            {description}
        </div>
    </div>
    
    <div class="section">
        <h2>Produktdetails</h2>
        <div class="details">
            {product_details}
        </div>
    </div>
    
    <div class="section">
        <h2>Versand & Rückgabe</h2>
        <div class="details">
            <p><strong>Versand:</strong> {shipping_info}</p>
            <p><strong>Rückgabe:</strong> {return_days} Tage Rückgaberecht</p>
        </div>
    </div>
    
    <div class="footer">
        <p>Vielen Dank für Ihr Interesse!</p>
    </div>
</body>
</html>
"""

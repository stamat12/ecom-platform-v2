"""
eBay API and business configuration
"""
import os
import json
from pathlib import Path
from typing import Dict

# eBay API Endpoints
EBAY_API_ENDPOINT = "https://api.ebay.com/ws/api.dll"
EBAY_SANDBOX_ENDPOINT = "https://api.sandbox.ebay.com/ws/api.dll"
EBAY_TAXONOMY_ENDPOINT = "https://api.ebay.com/commerce/taxonomy/v1"
EBAY_SANDBOX_TAXONOMY_ENDPOINT = "https://api.sandbox.ebay.com/commerce/taxonomy/v1"
EBAY_OAUTH_ENDPOINT = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SANDBOX_OAUTH_ENDPOINT = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

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

def get_oauth_endpoint() -> str:
  return EBAY_SANDBOX_OAUTH_ENDPOINT if USE_SANDBOX else EBAY_OAUTH_ENDPOINT

# OAuth Settings
EBAY_OAUTH_CLIENT_ID = os.getenv("EBAY_OAUTH_CLIENT_ID", "")
EBAY_OAUTH_CLIENT_SECRET = os.getenv("EBAY_OAUTH_CLIENT_SECRET", "")
EBAY_OAUTH_REDIRECT_URI = os.getenv("EBAY_OAUTH_REDIRECT_URI", "")
EBAY_REFRESH_TOKEN = os.getenv("EBAY_REFRESH_TOKEN", "")
EBAY_OAUTH_SCOPES = os.getenv("EBAY_OAUTH_SCOPES", "")

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

# Condition Mapping (eBay ConditionID → German label)
CONDITION_ID_TO_LABEL: Dict[int, str] = {
    1000: "Neu (New)",
    1500: "Neu ohne Originalverpackung (New other)",
    1750: "Neu mit Fehlern (New with defects)",
    2000: "Generalüberholt (Manufacturer refurbished)",
    2500: "Verkäufer überholt (Seller refurbished)",
    3000: "Gebraucht (Used)",
    4000: "Sehr gut (Very Good)",
    5000: "Gut (Good)",
    6000: "Akzeptabel (Acceptable)",
    7000: "Für Teile / nicht funktionsfähig (For parts or not working)",
}

# Reverse mapping (German text → eBay ConditionID)
CONDITION_MAPPING: Dict[str, int] = {
    "Neu": 1000,
    "Neu mit Karton": 1000,
    "Neu mit Etiketten": 1000,
    "Neu ohne Originalverpackung": 1500,
    "Neu ohne Karton": 1500,
    "Neu mit Fehlern": 1750,
    "Generalüberholt": 2000,
    "Verkäufer überholt": 2500,
    "Gebraucht": 3000,
    "Sehr gut": 4000,
    "Gut": 5000,
    "Akzeptabel": 6000,
    "Für Teile / nicht funktionsfähig": 7000,
    "Für Teile": 7000,
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

# Condition Description AI Settings
CONDITION_NOTE_MODEL = "gpt-4o-mini"
CONDITION_NOTE_TEMP = 0.2
CONDITION_NOTE_MAX_TOKENS = 120

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
_DEFAULT_EBAY_FIELD_ENRICHMENT_PROMPT = """Du bist ein Produktdaten-Spezialist für eBay-Listings.

Aufgabe: Fülle die folgenden eBay-Produktfelder basierend auf den bereitgestellten Produktfotos UND verfügbaren Produktinformationen aus.

Kategorie: {category_name}
eBay Kategorie ID: {category_id}

ERFORDERLICHE FELDER (müssen ausgefüllt werden):
{required_fields}

OPTIONALE FELDER (falls erkennbar):
{optional_fields}

AKTUELLE WERTE (bereits ausgefüllt):
{current_values}
{additional_context}

WICHTIGE REGELN:
1. Fülle NUR leere Felder aus - überschreibe KEINE bereits ausgefüllten Werte
2. Nutze die manuell hinzugefügten Produktinformationen (falls vorhanden)
3. Verwende wenn möglich die erlaubten Werte aus der Liste
4. Wenn du ein Feld nicht sicher bestimmen kannst, lasse es leer
5. Antworte auf Deutsch

Antworte im folgenden JSON-Format:
{{
  "required": {{
    "Feldname1": "Wert1"
  }},
  "optional": {{
    "Feldname2": "Wert2"
  }}
}}
"""

_DEFAULT_MANUFACTURER_LOOKUP_PROMPT = """You are a research assistant helping an e-commerce seller in the EU.
Find the OFFICIAL manufacturer or main company information for the brand "{brand}".
Return ONLY valid JSON, no explanation, no comments."""

_DEFAULT_CONDITION_NOTE_PROMPT = """Du bist ein eBay-Verkaeufer. Schreibe eine kurze Zustandsbeschreibung (1-2 Saetze) basierend nur auf den Bildern.
Zustand: {condition_label} (ID {condition_id})
Regeln:
- Nur sichtbare Merkmale oder Gebrauchsspuren nennen.
- Wenn nichts Sicheres erkennbar ist, schreibe: "Keine auffaelligen Gebrauchsspuren erkennbar, bitte Bilder beachten."
- Kein Markdown, keine Emojis, keine Aufzaehlungen.
- Antworte nur mit dem Text, ohne Anfuehrungszeichen.
"""

_DEFAULT_EBAY_SEO_ENRICHMENT_PROMPT = """You are an expert eBay Germany product classifier.
Extract exactly these fields as JSON only:
product_type, product_model, keyword_1, keyword_2, keyword_3.
All output must be in German.
Do not include brand, color, size, or condition words.
"""


def _load_enrichment_prompts() -> dict:
    data_path = Path(__file__).resolve().parents[2] / "data" / "enrichment_prompts.json"
    try:
        with data_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


_ENRICHMENT_PROMPTS = _load_enrichment_prompts()


def _prompt_value(key: str, default: str) -> str:
    raw = _ENRICHMENT_PROMPTS.get(key)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return "\n".join(str(line) for line in raw)
    return default


EBAY_FIELD_ENRICHMENT_PROMPT = _prompt_value("ebay_field_enrichment_prompt", _DEFAULT_EBAY_FIELD_ENRICHMENT_PROMPT)
EBAY_SEO_ENRICHMENT_PROMPT = _prompt_value("ebay_seo_enrichment_prompt", _DEFAULT_EBAY_SEO_ENRICHMENT_PROMPT)
MANUFACTURER_LOOKUP_PROMPT = _prompt_value("manufacturer_lookup_prompt", _DEFAULT_MANUFACTURER_LOOKUP_PROMPT)
CONDITION_NOTE_PROMPT = _prompt_value("condition_note_prompt", _DEFAULT_CONDITION_NOTE_PROMPT)

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

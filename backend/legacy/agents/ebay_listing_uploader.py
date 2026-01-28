"""
eBay Trading API - Fetch active listings with caching support.
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json
import html
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import re
import config
from openai import OpenAI

# Load environment variables from project root
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

# Initialize OpenAI client
openai_client = OpenAI()

# Cache settings
MANUFACTURER_CACHE_FILE = Path(__file__).parent.parent / "cache" / "ebay_manufacturers.json"

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}


# Endpoint and IDs (you can keep these in config.py or hardcode them)
EBAY_ENDPOINT = getattr(config, "EBAY_API_ENDPOINT", "https://api.ebay.com/ws/api.dll")
EBAY_COMPAT_LEVEL = str(getattr(config, "EBAY_COMPATIBILITY_LEVEL", "1149"))
EBAY_SITE_ID = str(getattr(config, "EBAY_SITE_ID", "77"))  # 77 = DE

EBAY_LOCATION_COUNTRY = getattr(config, "EBAY_LOCATION_COUNTRY", "AT")
EBAY_LOCATION_CITY = getattr(config, "EBAY_LOCATION_CITY", "Wien")
EBAY_LOCATION_POSTALCODE = getattr(config, "EBAY_LOCATION_POSTALCODE", "1210")

print(f"✓ eBay API config loaded (Site: {EBAY_SITE_ID}, Compat: {EBAY_COMPAT_LEVEL})")


def map_condition_to_id(condition_text: str) -> int:
    """
    Map German condition text to eBay ConditionID.
    
    Args:
        condition_text: German condition string from JSON
    
    Returns:
        eBay ConditionID (default: 1000 for New with box)
    """
    if not condition_text:
        return 1000  # Default to new
    
    condition_clean = condition_text.strip()
    condition_id = config.CONDITION_MAPPING.get(condition_clean, 1000)
    
    if condition_clean not in config.CONDITION_MAPPING:
        print(f"⚠️  Unknown condition '{condition_clean}', defaulting to 'Neu mit Karton' (1000)")
    
    return condition_id


def load_manufacturer_cache() -> Dict[str, Dict[str, Any]]:
    """Load the manufacturer cache from file."""
    if not MANUFACTURER_CACHE_FILE.exists():
        return {}
    try:
        with open(MANUFACTURER_CACHE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # Handle empty file
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        print(f"Warning: Manufacturer cache file is corrupted or empty, starting fresh")
        return {}
    except Exception as e:
        print(f"Warning: Could not load manufacturer cache: {e}")
        return {}


def save_manufacturer_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    """Save the manufacturer cache to file."""
    try:
        MANUFACTURER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MANUFACTURER_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save manufacturer cache: {e}")


def get_manufacturer_info(brand: str) -> Optional[Dict[str, Any]]:
    """
    Get manufacturer information for a brand.
    First checks cache, then uses OpenAI to research if not found.
    
    Args:
        brand: Brand name to look up
    
    Returns:
        Dict with manufacturer info or None if lookup fails
    """
    if not brand or not brand.strip():
        return None
    
    brand = brand.strip()
    
    # Check cache first
    cache = load_manufacturer_cache()
    if brand in cache:
        print(f"  ✓ Manufacturer info found in cache for '{brand}'")
        return cache[brand]
    
    # If not in cache, use OpenAI to research
    print(f"  🔍 Looking up manufacturer info for '{brand}'...")
    
    try:
        from config import MANUFACTURER_PROMPT
        
        prompt = MANUFACTURER_PROMPT.format(brand=brand)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            timeout=30
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Strip markdown code fences if present
        if result_text.startswith('```'):
            # Remove opening ```json or ``` 
            lines = result_text.split('\n')
            lines = lines[1:]  # Remove first line
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]  # Remove last line
            result_text = '\n'.join(lines).strip()
        
        # Parse JSON response
        manufacturer_info = json.loads(result_text)
        
        # Check if AI returned error (no real data found)
        if 'error' in manufacturer_info:
            print(f"  ⚠️  {manufacturer_info['error']}")
            print(f"  → Continuing without manufacturer contact info")
            return None
        
        # Validate that we got real data (not placeholder)
        if 'Muster' in manufacturer_info.get('Street1', '') or 'example' in manufacturer_info.get('Email', '').lower():
            print(f"  ⚠️  AI returned placeholder/example data, ignoring")
            print(f"  → Continuing without manufacturer contact info")
            return None
        
        # Save to cache
        cache[brand] = manufacturer_info
        save_manufacturer_cache(cache)
        
        print(f"  ✓ Manufacturer info extracted and cached for '{brand}'")
        return manufacturer_info
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Failed to parse manufacturer info for '{brand}': {e}")
        print(f"  → Continuing without manufacturer contact info")
        return None
    except Exception as e:
        print(f"  ⚠️  Error looking up manufacturer info for '{brand}': {e}")
        print(f"  → Continuing without manufacturer contact info")
        return None


# Business policy names
payment_profile_default = getattr(config, "EBAY_PAYMENT_POLICY_NAME", "EbayZahlungen")
return_profile_default = getattr(config, "EBAY_RETURN_POLICY_NAME", "14TageRücknahme")
shipping_profile_default = getattr(config, "EBAY_SHIPPING_POLICY_NAME", "Deutschland_bis50cm_KOSTENLOS")

# JSON products directory
PRODUCTS_DIR = getattr(config, "PRODUCTS_DIR", Path(__file__).parent.parent / "products")
EBAY_AUTH_TOKEN = os.getenv("EBAY_ACCESS_TOKEN")

if EBAY_AUTH_TOKEN:
    print(f"✓ eBay auth token loaded")
else:
    print(f"⚠️  WARNING: EBAY_AUTH_TOKEN not found in {ENV_PATH}")


def find_images_dir_for_sku(sku: str) -> Optional[Path]:
    """Find the images directory for a given SKU."""
    image_folder_paths = getattr(config, "IMAGE_FOLDER_PATHS", [])
    if not image_folder_paths:
        print(f"    Warning: IMAGE_FOLDER_PATHS not configured")
        return None
    
    for base in image_folder_paths:
        base_path = base if base.is_absolute() else (config.PROJECT_ROOT / base)
        candidate = base_path / sku
        if candidate.exists() and candidate.is_dir():
            return candidate
    
    print(f"    Images folder not found for SKU {sku} in configured paths")
    return None


def _build_headers(operation_name: str) -> Dict[str, str]:
    """Build headers for eBay Trading API requests using token authentication."""
    headers = {
        "X-EBAY-API-CALL-NAME": operation_name,
        "X-EBAY-API-SITEID": EBAY_SITE_ID,
        "X-EBAY-API-COMPATIBILITY-LEVEL": EBAY_COMPAT_LEVEL,
        "Content-Type": "text/xml",
    }
    print(f"[DEBUG] Headers: {headers}")
    return headers


def upload_picture_to_ebay(image_path: Path) -> str:
    """
    Upload a single local image file to eBay Picture Services (EPS)
    using UploadSiteHostedPictures (binary attachment).

    Returns the EPS FullURL for use in AddFixedPriceItem.
    """
    if EBAY_AUTH_TOKEN is None:
        raise RuntimeError("EBAY_ACCESS_TOKEN not configured in .env file")

    # Build the XML part
    picture_name = image_path.stem  # e.g. '1', 'VER02081 (2)'
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{EBAY_AUTH_TOKEN}</eBayAuthToken>
  </RequesterCredentials>
  <PictureName>{picture_name}</PictureName>
  <PictureSet>Standard</PictureSet>
</UploadSiteHostedPicturesRequest>"""

    # Build headers for Trading API, but REMOVE Content-Type
    headers = _build_headers("UploadSiteHostedPictures")
    headers.pop("Content-Type", None)  # let requests set multipart/form-data

    # Send multipart/form-data:
    #   - one part named "XML Payload" with the XML
    #   - one part named "file" with the binary image
    with image_path.open("rb") as f:
        files = {
            "XML Payload": (None, xml_body, "text/xml; charset=utf-8"),
            "file": (image_path.name, f, "application/octet-stream"),
        }
        response = requests.post(
            EBAY_ENDPOINT,
            headers=headers,
            files=files,
            timeout=60,
        )

    response.raise_for_status()
    text = response.text

    # Parse FullURL from response
    m = re.search(r"<FullURL>(.*?)</FullURL>", text)
    if not m:
        raise RuntimeError(f"Could not find FullURL in eBay response: {text[:500]}")

    full_url = m.group(1).strip()
    return full_url


def upload_pictures_for_listing(
    sku: str,
    ebay_images: List[Dict[str, Any]],
    max_images: int = 12,
) -> List[str]:
    """
    Uploads up to max_images for the given SKU from eBay Images section.
    Images are sorted by order and uploaded to eBay Picture Services.
    Caches eBay URLs in JSON to avoid re-uploading.
    
    Args:
        sku: Product SKU
        ebay_images: List of dicts with 'filename' and 'order' keys
        max_images: Maximum number of images to upload (default 12)
    
    Returns:
        List of eBay-hosted URLs in order
    """
    if not ebay_images:
        return []

    images_dir = find_images_dir_for_sku(sku)
    if images_dir is None:
        print(f"Warning: Could not find images directory for SKU {sku}")
        return []

    # Load JSON to check/update eBay URLs
    json_path = PRODUCTS_DIR / f"{sku}.json"
    product_data = {}
    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as f:
            product_data = json.load(f)
    
    if sku not in product_data:
        product_data[sku] = {}
    if "Images" not in product_data[sku]:
        product_data[sku]["Images"] = {}
    if "eBay Images" not in product_data[sku]["Images"]:
        product_data[sku]["Images"]["eBay Images"] = []
    
    ebay_images_section = product_data[sku]["Images"]["eBay Images"]

    # Sort by order field
    sorted_images = sorted(ebay_images, key=lambda x: x.get('order', 999))
    
    urls: List[str] = []
    updated = False
    
    for img_data in sorted_images[:max_images]:
        filename = img_data.get('filename', '')
        if not filename:
            continue
        
        # Check if already uploaded (has eBay URL cached)
        cached_url = img_data.get('eBay URL')
        if cached_url:
            urls.append(cached_url)
            print(f"  ✓ Using cached URL for {filename} (order {img_data.get('order', '?')})")
            continue
        
        image_path = images_dir / filename
        if not image_path.is_file():
            print(f"Warning: Image file not found: {image_path}")
            continue
        
        try:
            url = upload_picture_to_ebay(image_path)
            urls.append(url)
            print(f"  ✓ Uploaded {filename} (order {img_data.get('order', '?')})")
            
            # Update JSON with eBay URL
            for item in ebay_images_section:
                if item.get('filename') == filename:
                    item['eBay URL'] = url
                    updated = True
                    break
            
        except Exception as e:
            print(f"  ✗ Failed to upload {filename}: {e}")
            continue
    
    # Save updated JSON with eBay URLs
    if updated:
        try:
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            print(f"  💾 Saved eBay URLs to JSON")
        except Exception as e:
            print(f"  ⚠️  Failed to save eBay URLs: {e}")
    
    return urls


def _build_manufacturer_xml(manufacturer_info: Dict[str, Any]) -> str:
    """Build the Regulatory/Manufacturer block if data is complete enough."""
    if not manufacturer_info:
        return ""

    company = str(manufacturer_info.get("CompanyName", "") or "").strip()
    if not company:
        return ""

    street1 = str(manufacturer_info.get("Street1", "") or "").strip()
    street2 = str(manufacturer_info.get("Street2", "") or "").strip()
    city = str(manufacturer_info.get("CityName", "") or "").strip()
    state = str(manufacturer_info.get("StateOrProvince", "") or "").strip()
    postal = str(manufacturer_info.get("PostalCode", "") or "").strip()
    country = str(manufacturer_info.get("Country", "") or "").strip() or "DE"
    phone = str(manufacturer_info.get("Phone", "") or "").strip()
    email = str(manufacturer_info.get("Email", "") or "").strip()
    contact_url = str(manufacturer_info.get("ContactURL", "") or "").strip()

    # Require minimum fields to avoid sending junk
    if not (street1 and city and postal and country):
        return ""

    parts = [
        "<Regulatory>",
        "  <Manufacturer>",
        f"    <CompanyName>{html.escape(company)}</CompanyName>",
        f"    <Street1>{html.escape(street1)}</Street1>",
    ]

    if street2:
        parts.append(f"    <Street2>{html.escape(street2)}</Street2>")

    parts.append(f"    <CityName>{html.escape(city)}</CityName>")

    if state:
        parts.append(f"    <StateOrProvince>{html.escape(state)}</StateOrProvince>")

    parts.append(f"    <PostalCode>{html.escape(postal)}</PostalCode>")
    parts.append(f"    <Country>{html.escape(country)}</Country>")

    if phone:
        parts.append(f"    <Phone>{html.escape(phone)}</Phone>")
    if email:
        parts.append(f"    <Email>{html.escape(email)}</Email>")
    if contact_url:
        parts.append(f"    <ContactURL>{html.escape(contact_url)}</ContactURL>")

    parts.append("  </Manufacturer>")
    parts.append("</Regulatory>")

    return "\n    ".join(parts)


HTML_TEMPLATE = (
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


def load_product_json(sku: str) -> Optional[Dict[str, Any]]:
    """Load product data from JSON file for the given SKU."""
    json_path = PRODUCTS_DIR / f"{sku}.json"
    if not json_path.exists():
        print(f"Warning: JSON not found for SKU {sku} at {json_path}")
        return None
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error loading JSON for {sku}: {exc}")
        return None


def _safe_get_nested(data: Dict[str, Any], category: str, key: str, default: str = "") -> str:
    """Safely extract value from nested JSON structure."""
    if category not in data:
        return default
    section = data[category]
    if not isinstance(section, dict):
        return default
    val = section.get(key, default)
    if val is None or (isinstance(val, float) and val != val):  # NaN check
        return default
    return str(val).strip()


def build_title_from_json(product_info: Dict[str, Any], generated_info: Dict[str, Any], sku: str) -> str:
    """Build title: Brand + Keywords + Color + Size"""
    brand = product_info.get("Brand", "").strip()
    keywords = generated_info.get("Keywords", "").strip()
    color = product_info.get("Color", "").strip()
    size = product_info.get("Size", "").strip()

    if not keywords:
        raise ValueError(f"Keywords missing in JSON for SKU {sku}")

    # Build title parts: Brand + Keywords + Color + Size
    parts = []
    if brand and keywords:
        parts.append(f"{brand} {keywords}".strip())
    elif keywords:
        parts.append(keywords)
    
    if color:
        parts.append(color)
    
    if size:
        parts.append(f"Größe {size}")

    title = ", ".join(parts)

    # Optimize length: drop "Größe" if too long
    if len(title) > 80 and size:
        title = title.replace(f"Größe {size}", size)
    
    if len(title) > 80:
        raise ValueError(f"Title exceeds 80 chars for SKU {sku}: {title}")

    return title


def add_fixed_price_item(
    sku: str,
    price: float,
    condition_id: int = 1000,  # 1000=New, 3=Used
) -> Tuple[bool, Optional[str], str]:
    """
    Create eBay listing from JSON product data.
    
    Args:
        sku: Product SKU (used to find JSON file)
        price: Listing price in EUR
        condition_id: eBay condition ID (1000=New, 3=Used)
    
    Returns:
        (success: bool, item_id: Optional[str], raw_response: str)
    """

    if EBAY_AUTH_TOKEN is None:
        raise RuntimeError("EBAY_ACCESS_TOKEN not configured in .env file")

    # Load JSON product data
    json_data = load_product_json(sku)
    if json_data is None:
        raise RuntimeError(f"Cannot load JSON for SKU {sku}")

    # JSON structure: top-level key is the SKU itself
    if sku not in json_data:
        raise RuntimeError(f"SKU {sku} not found in JSON data")
    
    product_data = json_data[sku]

    # Extract main sections
    product_info = product_data.get("Intern Product Info", {})
    generated_info = product_data.get("Intern Generated Info", {})
    condition_section = product_data.get("Product Condition", {})
    ebay_cat = product_data.get("Ebay Category", {})
    ebay_fields = product_data.get("eBay Fields", {})
    images_data = product_data.get("Images", {})

    # Build title
    title = build_title_from_json(product_info, generated_info, sku)

    # Build description from JSON fields
    condition = condition_section.get("Condition", "")
    size = product_info.get("Size", "")
    color = product_info.get("Color", "")
    brand = product_info.get("Brand", "")
    materials = generated_info.get("Materials", "")
    more_details = generated_info.get("More details", "")

    desc_lines = []
    if condition:
        desc_lines.append(f"Zustand: {condition}")
    if size:
        desc_lines.append(f"Größe: {size}")
    if color:
        desc_lines.append(f"Farbe: {color}")
    if brand:
        desc_lines.append(f"Marke: {brand}")
    if more_details:
        desc_lines.append("")
        desc_lines.append(more_details)
    if materials:
        desc_lines.append("")
        desc_lines.append(materials)

    description_block = ""
    for line in desc_lines:
        description_block += (
            f'<div style="font-size:18px; margin-top:0.35em;">'
            f'<strong>{line}</strong>'
            f'</div>'
        )
    html_desc = HTML_TEMPLATE.format(title=title, description_block=description_block)

    # Get category ID from JSON
    category_id = ebay_cat.get("eBay Category ID")
    if not category_id:
        raise RuntimeError(f"Missing eBay Category ID for SKU {sku}")

    # Build ItemSpecifics from eBay Fields (required + optional)
    item_specifics_lines = ["<ItemSpecifics>"]
    required_fields = ebay_fields.get("required", {})
    optional_fields = ebay_fields.get("optional", {})
    
    for name, value in required_fields.items():
        if value:
            item_specifics_lines.append(f"  <NameValueList>")
            item_specifics_lines.append(f"    <Name>{html.escape(str(name))}</Name>")
            item_specifics_lines.append(f"    <Value>{html.escape(str(value))}</Value>")
            item_specifics_lines.append(f"  </NameValueList>")
    
    for name, value in optional_fields.items():
        if value:
            item_specifics_lines.append(f"  <NameValueList>")
            item_specifics_lines.append(f"    <Name>{html.escape(str(name))}</Name>")
            item_specifics_lines.append(f"    <Value>{html.escape(str(value))}</Value>")
            item_specifics_lines.append(f"  </NameValueList>")
    
    item_specifics_lines.append("</ItemSpecifics>")
    item_specifics_xml = "\n    ".join(item_specifics_lines)

    # Upload eBay Images and build picture URLs
    picture_details_xml = ""
    ebay_images = images_data.get("eBay Images", [])
    if ebay_images:
        print(f"Uploading {len(ebay_images)} images to eBay Picture Services...")
        uploaded_urls = upload_pictures_for_listing(sku, ebay_images, max_images=12)
        
        if uploaded_urls:
            lines = ["<PictureDetails>"]
            for url in uploaded_urls:
                lines.append(f"  <PictureURL>{url}</PictureURL>")
            lines.append("</PictureDetails>")
            picture_details_xml = "\n    ".join(lines)
            print(f"Successfully uploaded {len(uploaded_urls)} images")
        else:
            print("Warning: No images were uploaded")

    # Get manufacturer information (optional - continue if lookup fails)
    manufacturer_info = None
    manufacturer_contact_xml = ""
    if brand:
        try:
            manufacturer_info = get_manufacturer_info(brand)
            manufacturer_contact_xml = _build_manufacturer_xml(manufacturer_info)
        except Exception as e:
            print(f"  ⚠️  Manufacturer lookup error for '{brand}': {str(e)[:80]} - continuing without it")
            manufacturer_contact_xml = ""  # Skip manufacturer info, continue with upload

    # Business policy names
    payment_profile = payment_profile_default
    return_profile = return_profile_default
    shipping_profile = shipping_profile_default

    # Schedule listing 14 days in the future (UTC)
    schedule_time = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    price_str = f"{price:.2f}"

    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<AddFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{EBAY_AUTH_TOKEN}</eBayAuthToken>
  </RequesterCredentials>
  <ErrorLanguage>de_DE</ErrorLanguage>
  <WarningLevel>High</WarningLevel>
  <Item>
    <SKU>{sku}</SKU>
    <Title>{html.escape(title)}</Title>
    <Description><![CDATA[{html_desc}]]></Description>
    <PrimaryCategory>
      <CategoryID>{category_id}</CategoryID>
    </PrimaryCategory>
    <StartPrice currencyID="EUR">{price_str}</StartPrice>
    <Currency>EUR</Currency>
    <CategoryMappingAllowed>true</CategoryMappingAllowed>
    <ConditionID>{condition_id}</ConditionID>

    <Country>{EBAY_LOCATION_COUNTRY}</Country>
    <Location>{EBAY_LOCATION_CITY}</Location>
    <PostalCode>{EBAY_LOCATION_POSTALCODE}</PostalCode>

    <DispatchTimeMax>1</DispatchTimeMax>
    <ListingDuration>GTC</ListingDuration>
    <ListingType>FixedPriceItem</ListingType>
    <BestOfferDetails>
        <BestOfferEnabled>true</BestOfferEnabled>
    </BestOfferDetails>
    <ScheduleTime>{schedule_time}</ScheduleTime>

    <SellerProfiles>
      <SellerPaymentProfile>
        <PaymentProfileName>{payment_profile}</PaymentProfileName>
      </SellerPaymentProfile>
      <SellerReturnProfile>
        <ReturnProfileName>{return_profile}</ReturnProfileName>
      </SellerReturnProfile>
      <SellerShippingProfile>
        <ShippingProfileName>{shipping_profile}</ShippingProfileName>
      </SellerShippingProfile>
    </SellerProfiles>

    <Quantity>1</Quantity>
    {manufacturer_contact_xml}
    {picture_details_xml}
    {item_specifics_xml}
  </Item>
</AddFixedPriceItemRequest>"""

    headers = _build_headers("AddFixedPriceItem")
    response = requests.post(EBAY_ENDPOINT, headers=headers, data=xml_body.encode("utf-8"))
    response.raise_for_status()
    text = response.text

    ack_m = re.search(r"<Ack>(.*?)</Ack>", text)
    ack = ack_m.group(1).strip() if ack_m else "Failure"
    item_m = re.search(r"<ItemID>(.*?)</ItemID>", text)
    item_id = item_m.group(1).strip() if item_m else None

    success = ack in ("Success", "Warning")

    if not success:
        print("    > [EBAY RESPONSE Ack]", ack)
        error_blocks = re.findall(r"<Errors>(.*?)</Errors>", text, flags=re.DOTALL)
        if error_blocks:
            for block in error_blocks:
                sm = re.search(r"<ShortMessage>(.*?)</ShortMessage>", block)
                lm = re.search(r"<LongMessage>(.*?)</LongMessage>", block)
                code = re.search(r"<ErrorCode>(.*?)</ErrorCode>", block)
                print("    > [EBAY ERROR]",
                      f"Code={code.group(1).strip() if code else '?'} |",
                      f"Short='{sm.group(1).strip() if sm else ''}' |",
                      f"Long='{lm.group(1).strip() if lm else ''}'")
        else:
            print("    > [EBAY RAW RESPONSE SNIPPET]")
            print(text[:500])

    return success, item_id, text
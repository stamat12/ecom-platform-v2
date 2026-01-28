"""
eBay listing creation and image upload service
"""
import html
import json
import logging
import os
import re
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI

from app.config.ebay_config import (
    get_api_endpoint,
    EBAY_COMPATIBILITY_LEVEL,
    EBAY_SITE_ID,
    LOCATION_COUNTRY,
    LOCATION_CITY,
    LOCATION_POSTALCODE,
    PAYMENT_POLICY_NAME,
    RETURN_POLICY_NAME,
    SHIPPING_POLICY_NAME,
    DEFAULT_SCHEDULE_DAYS,
    DEFAULT_LISTING_DURATION,
    DEFAULT_QUANTITY,
    CONDITION_MAPPING,
    EBAY_MAX_IMAGES,
    MANUFACTURER_LOOKUP_MODEL,
    MANUFACTURER_LOOKUP_TEMP,
    MANUFACTURER_LOOKUP_MAX_TOKENS,
    MANUFACTURER_LOOKUP_PROMPT,
    LISTING_DESCRIPTION_TEMPLATE,
    LISTING_BANNER_URL,
    LISTING_RETURN_POLICY_DAYS,
    LISTING_SHIPPING_INFO
)
from app.repositories import ebay_cache_repo
from app.repositories.sku_json_repo import read_sku_json, _sku_json_path
from app.services.image_listing import list_images_for_sku

logger = logging.getLogger(__name__)

# OpenAI client
_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_ebay_token() -> str:
    """Get eBay access token from environment"""
    token = os.getenv("EBAY_ACCESS_TOKEN")
    if not token:
        raise ValueError("EBAY_ACCESS_TOKEN not found in environment variables")
    return token


def map_condition_to_id(condition_text: str) -> int:
    """
    Map German condition text to eBay ConditionID
    
    Returns:
        eBay ConditionID (default: 1000 for New)
    """
    if not condition_text:
        return 1000
    
    condition_clean = condition_text.strip()
    condition_id = CONDITION_MAPPING.get(condition_clean, 1000)
    
    if condition_clean not in CONDITION_MAPPING:
        logger.warning(f"Unknown condition '{condition_clean}', defaulting to 'Neu mit Karton' (1000)")
    
    return condition_id


def _build_headers(operation_name: str) -> Dict[str, str]:
    """Build headers for eBay Trading API requests"""
    return {
        "X-EBAY-API-CALL-NAME": operation_name,
        "X-EBAY-API-SITEID": EBAY_SITE_ID,
        "X-EBAY-API-COMPATIBILITY-LEVEL": EBAY_COMPATIBILITY_LEVEL,
        "Content-Type": "text/xml",
    }


def upload_picture_to_ebay(image_path: Path) -> str:
    """
    Upload single image to eBay Picture Services (EPS)
    
    Returns:
        EPS FullURL for use in listings
    """
    token = get_ebay_token()
    endpoint = get_api_endpoint()
    
    picture_name = image_path.stem
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{token}</eBayAuthToken>
  </RequesterCredentials>
  <PictureName>{picture_name}</PictureName>
  <PictureSet>Standard</PictureSet>
</UploadSiteHostedPicturesRequest>"""
    
    # Build headers without Content-Type (let requests set multipart)
    headers = _build_headers("UploadSiteHostedPictures")
    headers.pop("Content-Type", None)
    
    # Send multipart/form-data
    with image_path.open("rb") as f:
        files = {
            "XML Payload": (None, xml_body, "text/xml; charset=utf-8"),
            "file": (image_path.name, f, "application/octet-stream"),
        }
        response = requests.post(
            endpoint,
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
    logger.info(f"Uploaded image {image_path.name} to EPS: {full_url[:50]}...")
    return full_url


def upload_images_for_sku(
    sku: str,
    max_images: int = EBAY_MAX_IMAGES,
    force_reupload: bool = False
) -> Dict[str, Any]:
    """
    Upload images for SKU to eBay Picture Services
    
    Args:
        sku: Product SKU
        max_images: Maximum number of images to upload
        force_reupload: Force re-upload even if URLs cached
    
    Returns:
        Dict with upload results
    """
    logger.info(f"Uploading images for SKU {sku} (max: {max_images})")
    
    # Load product JSON
    product_json = read_sku_json(sku)
    if not product_json:
        raise ValueError(f"No product JSON found for SKU {sku}")
    
    images_section = product_json.get("Images", {}) or {}
    ebay_images = images_section.get("eBay Images", [])
    
    if not ebay_images:
        raise ValueError(f"No eBay images defined for SKU {sku}")
    
    # Get all image info
    all_images_info = list_images_for_sku(sku)
    all_images = all_images_info.get("images", [])
    
    if not all_images:
        raise ValueError(f"No images found for SKU {sku}")
    
    # Build filename -> path mapping
    image_path_map = {
        Path(img["full_path"]).name: Path(img["full_path"])
        for img in all_images
        if Path(img.get("full_path", "")).exists()
    }
    
    # Sort eBay images by order
    sorted_ebay_images = sorted(ebay_images, key=lambda x: x.get('order', 999))
    
    urls: List[str] = []
    uploaded_count = 0
    cached_count = 0
    updated = False
    
    for img_data in sorted_ebay_images[:max_images]:
        filename = img_data.get('filename', '')
        if not filename:
            continue
        
        # Check if already uploaded (has eBay URL cached)
        cached_url = img_data.get('eBay URL')
        if cached_url and not force_reupload:
            urls.append(cached_url)
            cached_count += 1
            logger.debug(f"Using cached URL for {filename}")
            continue
        
        # Get image path
        image_path = image_path_map.get(Path(filename).name)
        if not image_path:
            logger.warning(f"Image file not found: {filename}")
            continue
        
        try:
            url = upload_picture_to_ebay(image_path)
            urls.append(url)
            uploaded_count += 1
            
            # Update JSON with eBay URL
            img_data['eBay URL'] = url
            updated = True
            
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            continue
    
    # Save updated JSON with eBay URLs
    if updated:
        try:
            product_json["Images"]["eBay Images"] = sorted_ebay_images
            json_path = _sku_json_path(sku)
            full_data = {sku: product_json}
            
            temp_path = json_path.with_suffix(".tmp.json")
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(full_data, f, ensure_ascii=False, indent=2)
            temp_path.replace(json_path)
            
            logger.info(f"Saved {uploaded_count} new eBay URLs to JSON")
        except Exception as e:
            logger.error(f"Failed to save eBay URLs: {e}")
    
    return {
        "success": True,
        "sku": sku,
        "uploaded_count": uploaded_count,
        "cached_count": cached_count,
        "total_count": len(urls),
        "urls": urls,
        "message": f"Uploaded {uploaded_count} new images, used {cached_count} cached URLs"
    }


def get_manufacturer_info(brand: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get manufacturer information for brand
    
    Checks cache first, then uses OpenAI to research if not found
    
    Returns:
        Manufacturer info dict or None if lookup fails
    """
    if not brand or not brand.strip():
        return None
    
    brand = brand.strip()
    
    # Check cache
    if not force_refresh:
        cached = ebay_cache_repo.get_manufacturer_info(brand)
        if cached:
            logger.info(f"Using cached manufacturer info for '{brand}'")
            return cached
    
    # Research using OpenAI
    logger.info(f"Looking up manufacturer info for '{brand}' using AI...")
    
    try:
        client = get_openai_client()
        prompt = MANUFACTURER_LOOKUP_PROMPT.format(brand=brand)
        
        response = client.chat.completions.create(
            model=MANUFACTURER_LOOKUP_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=MANUFACTURER_LOOKUP_TEMP,
            max_tokens=MANUFACTURER_LOOKUP_MAX_TOKENS,
            timeout=30
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Strip markdown code fences if present
        if result_text.startswith('```'):
            lines = result_text.split('\n')
            lines = lines[1:]  # Remove first line with ```json
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]  # Remove last ```
            result_text = '\n'.join(lines).strip()
        
        # Parse JSON
        manufacturer_info = json.loads(result_text)
        
        # Check if valid (not error or placeholder)
        if 'error' in manufacturer_info:
            logger.warning(f"AI returned error for '{brand}': {manufacturer_info.get('error')}")
            return None
        
        # Validate data (not placeholder)
        if 'Muster' in manufacturer_info.get('Street1', '') or 'example' in manufacturer_info.get('Email', '').lower():
            logger.warning(f"AI returned placeholder data for '{brand}', ignoring")
            return None
        
        # Save to cache
        ebay_cache_repo.save_manufacturer_info(brand, manufacturer_info)
        logger.info(f"Manufacturer info extracted and cached for '{brand}'")
        return manufacturer_info
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse manufacturer info for '{brand}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error looking up manufacturer info for '{brand}': {e}")
        return None


def _build_manufacturer_xml(manufacturer_info: Optional[Dict[str, Any]]) -> str:
    """Build Regulatory/Manufacturer XML block"""
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
    
    # Require minimum fields
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


def build_title_from_product(product_json: Dict[str, Any], sku: str) -> str:
    """Build title: Brand + Keywords + Color + Size"""
    product_info = product_json.get("Intern Product Info", {})
    generated_info = product_json.get("Intern Generated Info", {})
    
    brand = product_info.get("Brand", "").strip()
    keywords = generated_info.get("Keywords", "").strip()
    color = product_info.get("Color", "").strip()
    size = product_info.get("Size", "").strip()
    
    if not keywords:
        raise ValueError(f"Keywords missing in JSON for SKU {sku}")
    
    # Build title parts
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
    
    # Optimize length
    if len(title) > 80 and size:
        title = title.replace(f"Größe {size}", size)
    
    if len(title) > 80:
        raise ValueError(f"Title exceeds 80 chars for SKU {sku}: {title}")
    
    return title


def build_description_html(product_json: Dict[str, Any], title: str) -> str:
    """Build HTML description from product data"""
    product_info = product_json.get("Intern Product Info", {})
    generated_info = product_json.get("Intern Generated Info", {})
    condition_section = product_json.get("Product Condition", {})
    
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
    
    # Build banner HTML
    banner = ""
    if LISTING_BANNER_URL:
        banner = f'<img src="{LISTING_BANNER_URL}" style="width:100%; max-width:100%; height:auto; display:block; margin:0 auto;" alt="Header Banner">'
    
    # Build product details HTML
    product_details = description_block
    
    # Use template
    html_desc = LISTING_DESCRIPTION_TEMPLATE.format(
        banner=banner,
        description=f"<h2>{title}</h2>",
        product_details=product_details,
        shipping_info=LISTING_SHIPPING_INFO,
        return_days=LISTING_RETURN_POLICY_DAYS
    )
    
    return html_desc


def create_listing(
    sku: str,
    price: float,
    condition_id: Optional[int] = None,
    schedule_days: int = DEFAULT_SCHEDULE_DAYS,
    payment_policy: Optional[str] = None,
    return_policy: Optional[str] = None,
    shipping_policy: Optional[str] = None,
    custom_description: Optional[str] = None,
    best_offer_enabled: bool = True,
    quantity: int = DEFAULT_QUANTITY
) -> Dict[str, Any]:
    """
    Create eBay listing from product JSON
    
    Returns:
        Dict with creation results
    """
    logger.info(f"Creating eBay listing for SKU {sku} at price {price}€")
    
    token = get_ebay_token()
    endpoint = get_api_endpoint()
    
    # Load product JSON
    product_json = read_sku_json(sku)
    if not product_json:
        raise ValueError(f"No product JSON found for SKU {sku}")
    
    # Extract sections
    product_info = product_json.get("Intern Product Info", {})
    generated_info = product_json.get("Intern Generated Info", {})
    condition_section = product_json.get("Product Condition", {})
    ebay_cat = product_json.get("Ebay Category", {})
    ebay_fields = product_json.get("eBay Fields", {})
    
    # Get category ID
    category_id = ebay_cat.get("eBay Category ID")
    if not category_id:
        raise ValueError(f"Missing eBay Category ID for SKU {sku}")
    
    # Build title
    title = build_title_from_product(product_json, sku)
    
    # Build description
    if custom_description:
        html_desc = custom_description
    else:
        html_desc = build_description_html(product_json, title)
    
    # Get condition ID
    if condition_id is None:
        condition_text = condition_section.get("Condition", "")
        condition_id = map_condition_to_id(condition_text)
    
    # Upload images
    upload_result = upload_images_for_sku(sku, max_images=EBAY_MAX_IMAGES)
    image_urls = upload_result.get("urls", [])
    
    if not image_urls:
        raise ValueError(f"No images uploaded for SKU {sku}")
    
    # Build picture details XML
    picture_lines = ["<PictureDetails>"]
    for url in image_urls:
        picture_lines.append(f"  <PictureURL>{url}</PictureURL>")
    picture_lines.append("</PictureDetails>")
    picture_details_xml = "\n    ".join(picture_lines)
    
    # Build item specifics XML
    item_specifics_lines = ["<ItemSpecifics>"]
    required_fields = ebay_fields.get("required", {})
    optional_fields = ebay_fields.get("optional", {})
    
    for name, value in required_fields.items():
        if value:
            item_specifics_lines.append("  <NameValueList>")
            item_specifics_lines.append(f"    <Name>{html.escape(str(name))}</Name>")
            item_specifics_lines.append(f"    <Value>{html.escape(str(value))}</Value>")
            item_specifics_lines.append("  </NameValueList>")
    
    for name, value in optional_fields.items():
        if value:
            item_specifics_lines.append("  <NameValueList>")
            item_specifics_lines.append(f"    <Name>{html.escape(str(name))}</Name>")
            item_specifics_lines.append(f"    <Value>{html.escape(str(value))}</Value>")
            item_specifics_lines.append("  </NameValueList>")
    
    item_specifics_lines.append("</ItemSpecifics>")
    item_specifics_xml = "\n    ".join(item_specifics_lines)
    
    # Get manufacturer info
    brand = product_info.get("Brand", "").strip()
    manufacturer_info = None
    manufacturer_xml = ""
    
    if brand:
        try:
            manufacturer_info = get_manufacturer_info(brand)
            manufacturer_xml = _build_manufacturer_xml(manufacturer_info)
        except Exception as e:
            logger.warning(f"Manufacturer lookup failed for '{brand}': {e}")
    
    # Business policies
    payment_policy = payment_policy or PAYMENT_POLICY_NAME
    return_policy = return_policy or RETURN_POLICY_NAME
    shipping_policy = shipping_policy or SHIPPING_POLICY_NAME
    
    # Schedule time
    schedule_time = (datetime.utcnow() + timedelta(days=schedule_days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    price_str = f"{price:.2f}"
    
    # Build XML request
    best_offer_xml = ""
    if best_offer_enabled:
        best_offer_xml = """<BestOfferDetails>
        <BestOfferEnabled>true</BestOfferEnabled>
    </BestOfferDetails>"""
    
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<AddFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{token}</eBayAuthToken>
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

    <Country>{LOCATION_COUNTRY}</Country>
    <Location>{LOCATION_CITY}</Location>
    <PostalCode>{LOCATION_POSTALCODE}</PostalCode>

    <DispatchTimeMax>1</DispatchTimeMax>
    <ListingDuration>{DEFAULT_LISTING_DURATION}</ListingDuration>
    <ListingType>FixedPriceItem</ListingType>
    {best_offer_xml}
    <ScheduleTime>{schedule_time}</ScheduleTime>

    <SellerProfiles>
      <SellerPaymentProfile>
        <PaymentProfileName>{payment_policy}</PaymentProfileName>
      </SellerPaymentProfile>
      <SellerReturnProfile>
        <ReturnProfileName>{return_policy}</ReturnProfileName>
      </SellerReturnProfile>
      <SellerShippingProfile>
        <ShippingProfileName>{shipping_policy}</ShippingProfileName>
      </SellerShippingProfile>
    </SellerProfiles>

    <Quantity>{quantity}</Quantity>
    {manufacturer_xml}
    {picture_details_xml}
    {item_specifics_xml}
  </Item>
</AddFixedPriceItemRequest>"""
    
    # Send request
    headers = _build_headers("AddFixedPriceItem")
    response = requests.post(endpoint, headers=headers, data=xml_body.encode("utf-8"), timeout=60)
    response.raise_for_status()
    text = response.text
    
    # Parse response
    ack_m = re.search(r"<Ack>(.*?)</Ack>", text)
    ack = ack_m.group(1).strip() if ack_m else "Failure"
    item_m = re.search(r"<ItemID>(.*?)</ItemID>", text)
    item_id = item_m.group(1).strip() if item_m else None
    
    success = ack in ("Success", "Warning")
    
    warnings = []
    errors = []
    
    # Parse errors/warnings
    if not success or ack == "Warning":
        error_blocks = re.findall(r"<Errors>(.*?)</Errors>", text, flags=re.DOTALL)
        for block in error_blocks:
            severity_m = re.search(r"<SeverityCode>(.*?)</SeverityCode>", block)
            severity = severity_m.group(1).strip() if severity_m else "Error"
            
            sm = re.search(r"<ShortMessage>(.*?)</ShortMessage>", block)
            lm = re.search(r"<LongMessage>(.*?)</LongMessage>", block)
            code_m = re.search(r"<ErrorCode>(.*?)</ErrorCode>", block)
            
            error_msg = f"Code {code_m.group(1) if code_m else '?'}: {lm.group(1) if lm else sm.group(1) if sm else 'Unknown error'}"
            
            if severity == "Warning":
                warnings.append(error_msg)
            else:
                errors.append(error_msg)
    
    if success:
        logger.info(f"Successfully created listing for SKU {sku}, ItemID: {item_id}")
    else:
        logger.error(f"Failed to create listing for SKU {sku}: {errors}")
    
    return {
        "success": success,
        "sku": sku,
        "item_id": item_id,
        "title": title,
        "category_id": str(category_id),
        "price": price,
        "scheduled_time": schedule_time,
        "image_count": len(image_urls),
        "has_manufacturer_info": bool(manufacturer_info),
        "message": f"Listing created successfully (ItemID: {item_id})" if success else f"Listing creation failed: {errors[0] if errors else 'Unknown error'}",
        "warnings": warnings,
        "errors": errors
    }


def preview_listing(sku: str, price: float, condition_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Preview listing without creating it
    
    Returns:
        Dict with preview data
    """
    logger.info(f"Previewing listing for SKU {sku}")
    
    # Load product JSON
    product_json = read_sku_json(sku)
    if not product_json:
        raise ValueError(f"No product JSON found for SKU {sku}")
    
    # Extract sections
    product_info = product_json.get("Intern Product Info", {})
    condition_section = product_json.get("Product Condition", {})
    ebay_cat = product_json.get("Ebay Category", {})
    ebay_fields = product_json.get("eBay Fields", {})
    
    # Get category
    category_id = ebay_cat.get("eBay Category ID")
    category_name = ebay_cat.get("Category", "")
    
    if not category_id:
        raise ValueError(f"Missing eBay Category ID for SKU {sku}")
    
    # Build title
    title = build_title_from_product(product_json, sku)
    
    # Build description
    html_desc = build_description_html(product_json, title)
    
    # Get condition
    if condition_id is None:
        condition_text = condition_section.get("Condition", "")
        condition_id = map_condition_to_id(condition_text)
    else:
        condition_text = condition_section.get("Condition", "")
    
    # Get images (check cached URLs)
    upload_result = upload_images_for_sku(sku, max_images=EBAY_MAX_IMAGES)
    image_urls = upload_result.get("urls", [])
    
    # Check manufacturer info
    brand = product_info.get("Brand", "").strip()
    has_manufacturer_info = False
    if brand:
        manufacturer_info = ebay_cache_repo.get_manufacturer_info(brand)
        has_manufacturer_info = bool(manufacturer_info)
    
    # Build item specifics dict
    required_fields = ebay_fields.get("required", {})
    optional_fields = ebay_fields.get("optional", {})
    item_specifics = {
        "required": required_fields,
        "optional": optional_fields
    }
    
    # Check missing required
    from app.services.ebay_enrichment import validate_ebay_fields
    validation = validate_ebay_fields(sku)
    missing_required = validation.get("missing_required", [])
    
    warnings = []
    if missing_required:
        warnings.append(f"{len(missing_required)} required fields missing: {', '.join(missing_required[:5])}")
    if not image_urls:
        warnings.append("No images available")
    
    return {
        "success": True,
        "sku": sku,
        "title": title,
        "description_html": html_desc,
        "category_id": str(category_id),
        "category_name": category_name,
        "price": price,
        "condition_id": condition_id,
        "condition_text": condition_text,
        "image_count": len(image_urls),
        "image_urls": image_urls,
        "item_specifics": item_specifics,
        "has_manufacturer_info": has_manufacturer_info,
        "missing_required_fields": missing_required,
        "warnings": warnings,
        "message": "Preview generated successfully"
    }

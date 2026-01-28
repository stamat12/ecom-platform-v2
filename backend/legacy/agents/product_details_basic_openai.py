"""
OpenAI-powered product field completion agent for ecommerceAI.

Business rules (German output enforced):
1) Gender -> codes: M, F, U, KB, KG, KU; if not gendered, leave empty.
2) More Details -> 2–5 German sentences.
3) Keywords -> German; order: <Modell (falls erkennbar)> <Produktart> <Damen|Herren|Unisex (optional)>;
   tokens separated by SINGLE SPACES (no commas).

Relies on:
- config.MODEL_FIELD_COMPLETION (e.g., "gpt-4o-mini")
- config.PROJECT_ROOT and .env with OPENAI_API_KEY
"""

import os
import json
import base64
import re
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

import config  # PROJECT_ROOT, MODEL_FIELD_COMPLETION, etc.

# ---------------------------------------------------------
# Environment & client
# ---------------------------------------------------------

load_dotenv(dotenv_path=config.PROJECT_ROOT / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = config.MODEL_FIELD_COMPLETION  # e.g., "gpt-4o-mini"

FIELDS = [
    "Gender",
    "Brand",
    "Color",
    "Size",
    "More Details",
    "Keywords",
    "Materials",
]

# Map the model-facing field names to their positions inside the product JSON
# so we can read/write the correct nested sections instead of dropping values
# at the root level.
FIELD_TARGETS = {
    "Gender": ("Intern Product Info", "Gender"),
    "Brand": ("Intern Product Info", "Brand"),
    "Color": ("Intern Product Info", "Color"),
    "Size": ("Intern Product Info", "Size"),
    "More Details": ("Intern Generated Info", "More details"),
    "Keywords": ("Intern Generated Info", "Keywords"),
    "Materials": ("Intern Generated Info", "Materials"),
}

# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def _image_to_data_uri(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/*;base64,{b64}"


def _atomic_dump(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(".tmp.json")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _only_known_keys(d: Dict[str, str]) -> Dict[str, str]:
    return {k: (d.get(k) or "") for k in FIELDS}


def _extract_existing_fields(record: Dict) -> Dict[str, str]:
    """Pull current values from their nested locations into a flat field dict."""
    extracted = {k: "" for k in FIELDS}
    extracted["Gender"] = record.get("Intern Product Info", {}).get("Gender", "")
    extracted["Brand"] = record.get("Intern Product Info", {}).get("Brand", "")
    extracted["Color"] = record.get("Intern Product Info", {}).get("Color", "")
    extracted["Size"] = record.get("Intern Product Info", {}).get("Size", "")
    extracted["More Details"] = record.get("Intern Generated Info", {}).get("More details", "")
    extracted["Keywords"] = record.get("Intern Generated Info", {}).get("Keywords", "")
    extracted["Materials"] = record.get("Intern Generated Info", {}).get("Materials", "")
    return extracted


def _write_fields_to_record(record: Dict, fields: Dict[str, str]) -> None:
    """Write fields back to their nested locations in the record."""
    if "Intern Product Info" not in record:
        record["Intern Product Info"] = {}
    record["Intern Product Info"]["Gender"] = fields.get("Gender", "")
    record["Intern Product Info"]["Brand"] = fields.get("Brand", "")
    record["Intern Product Info"]["Color"] = fields.get("Color", "")
    record["Intern Product Info"]["Size"] = fields.get("Size", "")
    
    if "Intern Generated Info" not in record:
        record["Intern Generated Info"] = {}
    record["Intern Generated Info"]["More details"] = fields.get("More Details", "")
    record["Intern Generated Info"]["Keywords"] = fields.get("Keywords", "")
    record["Intern Generated Info"]["Materials"] = fields.get("Materials", "")


def _find_images_dir_for_sku(sku: str) -> Path | None:
    """Locate the images directory for a given SKU using config.IMAGE_FOLDER_PATHS."""
    for base in getattr(config, "IMAGE_FOLDER_PATHS", []):
        base_path = base if base.is_absolute() else (config.PROJECT_ROOT / base)
        candidate = base_path / sku
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _collect_main_image_paths(record: Dict, sku: str) -> List[Path]:
    """Resolve all main image file paths for this SKU from the record JSON."""
    images_section = record.get("Images", {}) or {}
    main_images = images_section.get("main_images", []) or []
    if not main_images:
        return []

    images_dir = _find_images_dir_for_sku(sku)
    if not images_dir:
        return []

    filenames: List[str] = []
    for item in main_images:
        if isinstance(item, dict):
            fn = item.get("filename")
            if fn:
                filenames.append(fn)
        elif isinstance(item, str):
            filenames.append(item)

    paths: List[Path] = []
    for fn in filenames:
        p = images_dir / Path(fn).name
        if p.exists():
            paths.append(p)
    return paths


def _merge_fill_only(existing: Dict[str, str], proposed: Dict[str, str]) -> Dict[str, str]:
    """Merge: only fill empty fields from proposed, keep non-empty existing values."""
    out = dict(existing)
    for k in FIELDS:
        if not (out.get(k) or "").strip():  # Only fill if empty
            out[k] = proposed.get(k, "")
    return out


# ---------------------------------------------------------
# Business-rule normalization
# ---------------------------------------------------------

_GENDER_CODE_MAP = {
    "male": "M", "männer": "M", "herren": "M", "man": "M", "men": "M",
    "female": "F", "frauen": "F", "damen": "F", "woman": "F", "women": "F",
    "unisex": "U",
    "boys": "KB", "jungen": "KB", "buben": "KB",
    "girls": "KG", "mädchen": "KG",
    "kids": "KU", "kinder": "KU", "kids unisex": "KU", "kinder unisex": "KU",
}

def normalize_gender_code(value: str) -> str:
    """
    Map free-text to: M, F, U, KB, KG, KU.
    Return "" for clearly non-gendered items or if unrecognized.
    """
    v = (value or "").strip()
    if not v:
        return ""
    vlow = v.lower()

    for token, code in _GENDER_CODE_MAP.items():
        if token in vlow:
            return code

    if v.upper() in {"M", "F", "U", "KB", "KG", "KU"}:
        return v.upper()

    if any(x in vlow for x in ["universal", "neutral", "one size", "größe-unabhängig", "not gendered"]):
        return ""

    return ""


def sentence_split(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def enforce_more_details_sentences(text: str) -> str:
    """
    Ensure 2–5 sentences in German. If >5, truncate; if <2, attempt to split by punctuation.
    """
    text = (text or "").strip()
    if not text:
        return ""

    sents = sentence_split(text)
    if len(sents) >= 2:
        return " ".join(sents[:5])

    # Expand to at least 2 using commas/semicolons/dashes as light splitters
    chunks = re.split(r"[;,\u2013\u2014-]+", text)
    chunks = [c.strip() for c in chunks if c.strip()]
    if len(chunks) >= 2:
        s1 = chunks[0].rstrip(".") + "."
        s2 = chunks[1].rstrip(".") + "."
        extra = chunks[2:5]
        sents2 = [s1, s2] + [c.rstrip(".") + "." for c in extra]
        return " ".join(sents2[:5])

    return sents[0] if sents else ""


def _tokenize_keywords(raw: str) -> List[str]:
    """
    Tokenize keywords from arbitrary separators to clean word tokens.
    Remove commas by design; collapse multiple spaces.
    """
    # Replace separators with spaces, then split
    cleaned = re.sub(r"[,/;|]+", " ", (raw or ""))
    # Also normalize hyphen-like separators to spaces for safety (model names with hyphens are kept via split/join)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return []
    return cleaned.split(" ")


def normalize_keywords(value: str, gender_code: str) -> str:
    """
    Enforce order and spacing ONLY (no commas):
      "<Modell falls erkennbar> <Produktart> <Damen|Herren|Unisex (optional)> [weitere Tokens…]"
    """
    tokens = _tokenize_keywords(value)

    # Heuristic: model-like token = contains at least one digit or a tight alnum code
    def looks_like_model(tok: str) -> bool:
        t = tok.replace("-", "").replace("_", "")
        return any(c.isdigit() for c in t) or (len(t) >= 3 and any(c.isdigit() for c in t))

    model_tok = None
    product_tok = None
    rest: List[str] = []

    for t in tokens:
        if model_tok is None and looks_like_model(t):
            model_tok = t
            continue
        if product_tok is None:
            product_tok = t
            continue
        rest.append(t)

    gender_label = {
        "M": "Herren",
        "F": "Damen",
        "U": "Unisex",
        "KB": "Herren",  # Falls Kinder-Jungen -> Herren oft besser suchbar; ggf. anpassen
        "KG": "Damen",
        "KU": "Unisex",
    }.get(gender_code, "")

    ordered: List[str] = []
    if model_tok:
        ordered.append(model_tok)
    if product_tok:
        ordered.append(product_tok)
    elif not model_tok and tokens:
        ordered.append(tokens[0])  # Fallback

    if gender_label:
        ordered.append(gender_label)

    # Append remaining tokens without duplicates
    for t in rest:
        if t not in ordered:
            ordered.append(t)

    # Return SINGLE-SPACE separated string (no commas)
    return " ".join([t for t in ordered if t]).strip()


# ---------------------------------------------------------
# Core LLM call
# ---------------------------------------------------------

def extract_fields_from_images(image_paths: List[Path], current_fields: Dict[str, str]) -> Dict[str, str]:
    """
    Sends the current fields + ALL provided images to the model and gets strict JSON back,
    with German instructions and our business constraints.
    """
    prompt = (
        "Du vervollständigst Produktattribute AUSSCHLIESSLICH anhand der Hauptfotos (alle gegebenen Bilder).\n"
        f"Gib NUR ein striktes JSON-Objekt mit GENAU diesen Schlüsseln zurück: {FIELDS}.\n"
        "Regeln:\n"
        "1) Gender: Nutze Codes M (Herren), F (Damen), U (Unisex), KB (Boys), KG (Girls), KU (Kids Unisex). "
        "Wenn das Produkt nicht geschlechtsspezifisch ist, lasse Gender leer.\n"
        "2) More Details: Muss 2–5 Sätze auf Deutsch enthalten (kurze, präzise, sichtbare Merkmale).\n"
        "3) Keywords (Deutsch): Beginne mit dem Modell (falls erkennbar), dann die Produktart "
        "(z. B. Sneakers, Fahrradhandschuhe), und optional Damen/Herren/Unisex. "
        "Verwende KEINE Kommata – nur Leerzeichen zwischen Begriffen.\n"
        "Weitere Hinweise:\n"
        "- Lege nur Werte fest, die visuell erkennbar und plausibel sind. Wenn unsicher: leerer String.\n"
        "- Keine zusätzlichen Schlüssel oder Kommentare – nur das JSON.\n"
    )
    # Ensure we have at least one image
    image_paths = [p for p in (image_paths or []) if isinstance(p, Path)]
    if not image_paths:
        return {k: "" for k in FIELDS}

    try:
        content: List[dict] = [
            {
                "type": "text",
                "text": "Aktuelle Felder (fülle nur leere Werte, alles auf Deutsch):\n"
                        + json.dumps(_only_known_keys(current_fields), ensure_ascii=False),
            }
        ]

        # Attach all images
        for img_path in image_paths:
            data_uri = _image_to_data_uri(img_path)
            content.append({"type": "image_url", "image_url": {"url": data_uri}})

        response = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        cleaned = _only_known_keys(parsed)
        return cleaned

    except Exception as ex:
        print(f"[ERROR] Vision extraction failed: {ex}")
        return {k: "" for k in FIELDS}


# ---------------------------------------------------------
# Public: single SKU
# ---------------------------------------------------------

def fill_missing_fields_for_sku(sku: str, product_json_path: Path, main_image_path: Path) -> Dict[str, str]:
    """Fill missing fields for a single SKU using OpenAI vision on ALL main images."""
    # Load existing data
    with product_json_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    record = data[sku]

    # Collect all main image paths for the SKU (preferred)
    image_paths = _collect_main_image_paths(record, sku)

    # Fallback: include provided single main_image_path if collection failed
    if not image_paths and main_image_path and main_image_path.exists():
        image_paths = [main_image_path]

    if not image_paths:
        print(f"[ERROR] No main images found for {sku} (looked in JSON and fallback path: {main_image_path})")
        return {}

    # Extract current fields from their nested locations
    current_fields = _extract_existing_fields(record)

    # Check if there are any empty fields to fill
    empty_fields = {k: v for k, v in current_fields.items() if not (v or '').strip()}
    if not empty_fields:
        print(f"[INFO] No empty fields to fill for {sku}")
        return current_fields

    # Call OpenAI to extract fields from all images
    proposed_fields = extract_fields_from_images(image_paths, current_fields)

    # Merge: only fill missing values
    merged = _merge_fill_only(current_fields, proposed_fields)

    # Write merged fields back to their nested locations
    _write_fields_to_record(record, merged)

    # Save updated JSON
    _atomic_dump(product_json_path, data)

    return merged


# ---------------------------------------------------------
# Public: batch SKUs
# ---------------------------------------------------------

def fill_missing_fields_for_skus(sku_image_json_list: List[Dict[str, Path]]):
    """
    sku_image_json_list format:
        [{"sku": "ABC123", "json": Path(...), "image": Path(...)}, ...]
    Returns: { sku: {fields...} | {"error": "..."} }
    """
    results = {}
    for entry in sku_image_json_list:
        sku = entry["sku"]
        product_json_path = entry["json"]
        main_image_path = entry["image"]
        try:
            results[sku] = fill_missing_fields_for_sku(sku, product_json_path, main_image_path)
        except Exception as e:
            results[sku] = {"error": str(e)}
    return results


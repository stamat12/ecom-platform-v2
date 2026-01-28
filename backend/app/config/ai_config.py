"""
AI enrichment configuration for product details.
Centralized location for prompts, models, and business rules.
"""

# AI Models
OPENAI_MODEL = "gpt-4o-mini"  # Vision-capable model for product field completion
GEMINI_MODEL = "gemini-1.5-pro"  # For EAN/price extraction

# Product fields that can be enriched
ENRICHABLE_FIELDS = [
    "Gender",
    "Brand",
    "Color",
    "Size",
    "More Details",
    "Keywords",
    "Materials",
]

# Map field names to their JSON locations
FIELD_TARGETS = {
    "Gender": ("Intern Product Info", "Gender"),
    "Brand": ("Intern Product Info", "Brand"),
    "Color": ("Intern Product Info", "Color"),
    "Size": ("Intern Product Info", "Size"),
    "More Details": ("Intern Generated Info", "More details"),
    "Keywords": ("Intern Generated Info", "Keywords"),
    "Materials": ("Intern Generated Info", "Materials"),
}

# OpenAI Vision Prompt for field completion
OPENAI_PROMPT = (
    "Du vervollständigst Produktattribute AUSSCHLIESSLICH anhand der Hauptfotos (alle gegebenen Bilder).\n"
    f"Gib NUR ein striktes JSON-Objekt mit GENAU diesen Schlüsseln zurück: {ENRICHABLE_FIELDS}.\n"
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

# Gender code mapping
GENDER_CODE_MAP = {
    "male": "M", "männer": "M", "herren": "M", "man": "M", "men": "M",
    "female": "F", "frauen": "F", "damen": "F", "woman": "F", "women": "F",
    "unisex": "U",
    "boys": "KB", "jungen": "KB", "buben": "KB",
    "girls": "KG", "mädchen": "KG",
    "kids": "KU", "kinder": "KU", "kids unisex": "KU", "kinder unisex": "KU",
}

VALID_GENDER_CODES = {"M", "F", "U", "KB", "KG", "KU"}

# Temperature for AI calls (lower = more consistent)
OPENAI_TEMPERATURE = 0.1
OPENAI_MAX_TOKENS = 500

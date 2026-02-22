import json
from app.services.ebay_listing import build_title_from_product

# Create a sample product with full enrichment
product = {
    "Intern Product Info": {
        "Gender": "F",
        "Brand": "Hunkemöller",
        "Color": "Schwarz",
        "Size": "80B"
    },
    "eBay SEO": {
        "Product Model": "Lotta",
        "Product Type": "Bügel-BH",
        "Keyword 1": "Push-Up-BH",
        "Keyword 2": "Gepolsterter BH",
        "Keyword 3": "Damen BH"
    },
    "Product Condition": {
        "Condition": "Neu mit Etiketten"
    }
}

# Test 1: Full title
print("TEST 1: Full title with all components")
print("=" * 60)
try:
    title = build_title_from_product(product, "TEST001")
    print(f"✓ Title: {title}")
    print(f"✓ Length: {len(title)}/80 chars")
except ValueError as e:
    print(f"✗ Error: {e}")

# Test 2: Truncation scenarios
print("\nTEST 2: Gender code translations")
print("=" * 60)
gender_tests = {
    "M": "Herren",
    "F": "Damen",
    "U": "Unisex",
}
for code, expected in gender_tests.items():
    test_product = {
        "Intern Product Info": {
            "Gender": code,
            "Brand": "Test",
            "Color": "Black",
            "Size": "M"
        },
        "eBay SEO": {
            "Product Model": "Model",
            "Product Type": "Type",
            "Keyword 1": "K1",
        },
        "Product Condition": {"Condition": "New"}
    }
    try:
        title = build_title_from_product(test_product, f"TEST_{code}")
        has_gender = expected in title
        print(f"  {code} → {expected}: {'✓' if has_gender else '✗'}")
    except ValueError as e:
        print(f"  {code}: ✗ {e}")

print("\nTEST 3: Missing Product Type error")
print("=" * 60)
invalid_product = product.copy()
invalid_product["eBay SEO"] = {"Product Type": ""}
try:
    title = build_title_from_product(invalid_product, "TEST_INVALID")
    print(f"✗ Should have raised error")
except ValueError as e:
    print(f"✓ Correctly raised error: {str(e)[:60]}...")

print("\n✓ TESTS COMPLETE")

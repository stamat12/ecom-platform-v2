from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test the new endpoint
print("Testing /api/ebay-cache/de-listings...")
response = client.get("/api/ebay-cache/de-listings?page=1&limit=10")
print(f"Status: {response.status_code}")
data = response.json()
print(f"Total DE listings: {data.get('total')}")
print(f"Listings returned: {len(data.get('listings', []))}")
print(f"Sample listing SKU: {data.get('listings', [{}])[0].get('sku', 'N/A')}")

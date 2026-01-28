import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export default function EbaySyncPage() {
  const [listings, setListings] = useState([]);
  const [skuCounts, setSkuCounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [sortBy, setSortBy] = useState("sku");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");

      // Load both listings and SKU counts
      const [listingsRes, countsRes] = await Promise.all([
        fetch("/api/ebay/sync/listings"),
        fetch("/api/ebay/sync/sku-counts")
      ]);

      if (!listingsRes.ok || !countsRes.ok) throw new Error("Failed to load data");

      const listingsData = await listingsRes.json();
      const countsData = await countsRes.json();

      setListings(listingsData.listings || []);
      setSkuCounts(countsData.sku_counts || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    if (!confirm("Sync active listings from eBay? This will refresh the cache.")) return;

    try {
      setSyncing(true);
      setError("");

      const res = await fetch("/api/ebay/sync/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: true })
      });

      if (!res.ok) throw new Error("Sync failed");

      const data = await res.json();
      alert(`Synced ${data.total_listings} listings from eBay`);
      
      await loadData();
    } catch (e) {
      setError(String(e));
    } finally {
      setSyncing(false);
    }
  };

  // Filter and sort
  const filteredListings = listings.filter(l => 
    filter === "" || 
    l.sku?.toLowerCase().includes(filter.toLowerCase()) ||
    l.title?.toLowerCase().includes(filter.toLowerCase())
  );

  const sortedListings = [...filteredListings].sort((a, b) => {
    if (sortBy === "sku") return (a.sku || "").localeCompare(b.sku || "");
    if (sortBy === "title") return (a.title || "").localeCompare(b.title || "");
    if (sortBy === "price") return parseFloat(b.price || 0) - parseFloat(a.price || 0);
    if (sortBy === "quantity") return parseInt(b.quantity || 0) - parseInt(a.quantity || 0);
    return 0;
  });

  const sortedCounts = [...skuCounts].sort((a, b) => b.count - a.count);

  return (
    <div style={{ padding: 20, maxWidth: 1600, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>Active eBay Listings</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={handleSync}
            disabled={syncing}
            style={{ 
              padding: "8px 16px", 
              background: "#28a745", 
              color: "white", 
              border: "none", 
              borderRadius: 4, 
              cursor: syncing ? "not-allowed" : "pointer" 
            }}
          >
            {syncing ? "Syncing..." : "Sync from eBay"}
          </button>
          <Link to="/ebay/listings" style={{ padding: "8px 16px", background: "#6c757d", color: "white", textDecoration: "none", borderRadius: 4 }}>
            ← Create Listing
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #fcc", borderRadius: 4, marginBottom: 20, color: "#c00" }}>
          Error: {error}
        </div>
      )}

      {loading ? (
        <div>Loading listings...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20 }}>
          {/* SKU Counts Sidebar */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden", maxHeight: 700 }}>
            <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", fontWeight: "bold" }}>
              Listings by SKU ({skuCounts.length} SKUs)
            </div>
            <div style={{ maxHeight: 650, overflow: "auto" }}>
              {sortedCounts.map((item) => (
                <div
                  key={item.sku}
                  onClick={() => setFilter(item.sku)}
                  style={{
                    padding: 10,
                    borderBottom: "1px solid #eee",
                    cursor: "pointer",
                    background: filter === item.sku ? "#e3f2fd" : "white"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontWeight: "bold", fontSize: 13 }}>{item.sku}</div>
                    <div style={{ 
                      background: "#007bff", 
                      color: "white", 
                      padding: "2px 8px", 
                      borderRadius: 12, 
                      fontSize: 12,
                      fontWeight: "bold"
                    }}>
                      {item.count}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
                    {item.total_quantity} total qty
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Listings Table */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: "bold" }}>
                All Listings ({filteredListings.length})
                {filter && (
                  <button
                    onClick={() => setFilter("")}
                    style={{ marginLeft: 10, padding: "4px 8px", fontSize: 12, cursor: "pointer" }}
                  >
                    Clear Filter
                  </button>
                )}
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="text"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Search SKU or title..."
                  style={{ padding: 6, fontSize: 13, border: "1px solid #ddd", borderRadius: 4, width: 200 }}
                />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  style={{ padding: 6, fontSize: 13, border: "1px solid #ddd", borderRadius: 4 }}
                >
                  <option value="sku">Sort by SKU</option>
                  <option value="title">Sort by Title</option>
                  <option value="price">Sort by Price</option>
                  <option value="quantity">Sort by Quantity</option>
                </select>
              </div>
            </div>

            <div style={{ maxHeight: 650, overflow: "auto" }}>
              {sortedListings.length === 0 ? (
                <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
                  No listings found
                </div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead style={{ position: "sticky", top: 0, background: "#fafafa", borderBottom: "2px solid #ddd" }}>
                    <tr>
                      <th style={{ padding: 10, textAlign: "left", fontWeight: "bold" }}>SKU</th>
                      <th style={{ padding: 10, textAlign: "left", fontWeight: "bold" }}>Title</th>
                      <th style={{ padding: 10, textAlign: "right", fontWeight: "bold" }}>Price</th>
                      <th style={{ padding: 10, textAlign: "center", fontWeight: "bold" }}>Qty</th>
                      <th style={{ padding: 10, textAlign: "center", fontWeight: "bold" }}>Condition</th>
                      <th style={{ padding: 10, textAlign: "center", fontWeight: "bold" }}>Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedListings.map((listing) => (
                      <tr key={listing.item_id} style={{ borderBottom: "1px solid #eee" }}>
                        <td style={{ padding: 10 }}>
                          <strong>{listing.sku || "—"}</strong>
                        </td>
                        <td style={{ padding: 10, maxWidth: 400 }}>
                          <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {listing.title || "—"}
                          </div>
                        </td>
                        <td style={{ padding: 10, textAlign: "right" }}>
                          €{parseFloat(listing.price || 0).toFixed(2)}
                        </td>
                        <td style={{ padding: 10, textAlign: "center" }}>
                          {listing.quantity || 0}
                        </td>
                        <td style={{ padding: 10, textAlign: "center" }}>
                          <span style={{ 
                            padding: "2px 8px", 
                            background: "#e3f2fd", 
                            borderRadius: 4, 
                            fontSize: 11 
                          }}>
                            {listing.condition || "—"}
                          </span>
                        </td>
                        <td style={{ padding: 10, textAlign: "center" }}>
                          <a 
                            href={`https://www.ebay.de/itm/${listing.item_id}`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style={{ color: "#007bff", textDecoration: "none" }}
                          >
                            View →
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

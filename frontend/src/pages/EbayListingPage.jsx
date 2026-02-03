import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export default function EbayListingPage() {
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [condition, setCondition] = useState("Neu");
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [batchMode, setBatchMode] = useState(false);
  const [batchData, setBatchData] = useState("");
  const [batchResults, setBatchResults] = useState([]);

  const conditions = ["Neu", "Neu mit Etikett", "Neuwertig", "Gut", "Sehr gut", "Akzeptabel"];

  const handlePreview = async () => {
    if (!sku.trim() || !price.trim()) {
      setError("Please enter SKU and price");
      return;
    }

    try {
      setPreviewing(true);
      setError("");
      setPreview(null);

      const res = await fetch("/api/ebay/listings/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku: sku.trim(),
          price: parseFloat(price),
          quantity: parseInt(quantity),
          condition: condition
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Preview failed");
      }

      const data = await res.json();
      setPreview(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setPreviewing(false);
    }
  };

  const handleCreateListing = async () => {
    if (!sku.trim() || !price.trim()) {
      setError("Please enter SKU and price");
      return;
    }

    if (!confirm(`Create eBay listing for ${sku.trim()} at €${price}?`)) return;

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const res = await fetch("/api/ebay/listings/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku: sku.trim(),
          price: parseFloat(price),
          quantity: parseInt(quantity),
          condition: condition
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Listing creation failed");
      }

      const data = await res.json();
      setResult(data);
      
      // Build detailed message
      let message = `📦 SKU: ${data.sku}\n\n`;
      
      if (data.success) {
        message += `✅ SUCCESS - Listing Created!\n\n`;
        message += `🔗 eBay Item ID: ${data.item_id}\n`;
        message += `📝 Title: ${data.title}\n`;
        message += `💰 Price: €${data.price}\n`;
        message += `📸 Images uploaded: ${data.image_count}\n`;
        message += `📁 Category ID: ${data.category_id}\n`;
        
        if (data.scheduled_time) {
          message += `📅 Scheduled for: ${new Date(data.scheduled_time).toLocaleString('de-DE')}\n`;
        } else {
          message += `📅 Published: Immediately\n`;
        }
        
        if (data.has_manufacturer_info) {
          message += `✅ Manufacturer info included\n`;
        }
        
        // Show warnings if any
        if (data.warnings && data.warnings.length > 0) {
          message += `\n⚠️ WARNINGS (${data.warnings.length}):\n`;
          data.warnings.forEach((warning, idx) => {
            message += `${idx + 1}. ${warning}\n`;
          });
        }
        
        alert(message);
        window.open(`https://www.ebay.de/itm/${data.item_id}`, "_blank");
        
        // Clear form on success
        setSku("");
        setPrice("");
        setQuantity("1");
        setPreview(null);
      } else {
        // Failed
        message += `❌ FAILED - Listing Not Created\n\n`;
        
        if (data.errors && data.errors.length > 0) {
          message += `❌ ERRORS (${data.errors.length}):\n`;
          data.errors.forEach((error, idx) => {
            message += `${idx + 1}. ${error}\n`;
          });
        } else {
          message += `Error: ${data.message || 'Unknown error'}\n`;
        }
        
        // Show warnings if any
        if (data.warnings && data.warnings.length > 0) {
          message += `\n⚠️ WARNINGS (${data.warnings.length}):\n`;
          data.warnings.forEach((warning, idx) => {
            message += `${idx + 1}. ${warning}\n`;
          });
        }
        
        alert(message);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleBatchCreate = async () => {
    const lines = batchData.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length === 0) {
      setError("Please enter batch data (format: SKU,price,quantity,condition)");
      return;
    }

    const items = lines.map(line => {
      const [sku, price, qty, cond] = line.split(",").map(s => s.trim());
      return {
        sku,
        price: parseFloat(price || "0"),
        quantity: parseInt(qty || "1"),
        condition: cond || "Neu"
      };
    });

    if (!confirm(`Create ${items.length} eBay listings?`)) return;

    try {
      setLoading(true);
      setError("");
      setBatchResults([]);

      const res = await fetch("/api/ebay/listings/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Batch creation failed");
      }

      const data = await res.json();
      setBatchResults(data.results || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>Create eBay Listing</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to="/ebay/enrich" style={{ padding: "8px 16px", background: "#6c757d", color: "white", textDecoration: "none", borderRadius: 4 }}>
            ← Enrichment
          </Link>
          <Link to="/ebay/sync" style={{ padding: "8px 16px", background: "#007bff", color: "white", textDecoration: "none", borderRadius: 4 }}>
            Active Listings →
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #fcc", borderRadius: 4, marginBottom: 20, color: "#c00" }}>
          Error: {error}
        </div>
      )}

      {result && (
        <div style={{ 
          padding: 15, 
          background: result.listing_id ? "#f0fff4" : "#fff9e6", 
          border: `2px solid ${result.listing_id ? "#28a745" : "#ffc107"}`, 
          borderRadius: 4, 
          marginBottom: 20 
        }}>
          <div style={{ fontWeight: "bold", fontSize: 16, marginBottom: 8 }}>
            {result.listing_id ? "✓ Listing Created Successfully" : "⚠ Listing Creation Issues"}
          </div>
          {result.listing_id && (
            <div style={{ fontSize: 14 }}>
              Listing ID: <strong>{result.listing_id}</strong><br />
              <a href={`https://www.ebay.de/itm/${result.listing_id}`} target="_blank" rel="noopener noreferrer" style={{ color: "#007bff" }}>
                View on eBay →
              </a>
            </div>
          )}
          {result.warnings && result.warnings.length > 0 && (
            <div style={{ marginTop: 10, fontSize: 13 }}>
              <div style={{ fontWeight: "bold" }}>Warnings:</div>
              {result.warnings.map((w, i) => <div key={i}>• {w}</div>)}
            </div>
          )}
        </div>
      )}

      {/* Mode Toggle */}
      <div style={{ marginBottom: 20, display: "flex", gap: 10 }}>
        <button
          onClick={() => { setBatchMode(false); setBatchResults([]); setResult(null); }}
          style={{
            padding: "8px 16px",
            background: !batchMode ? "#007bff" : "#e9ecef",
            color: !batchMode ? "white" : "#495057",
            border: "1px solid #dee2e6",
            borderRadius: 4,
            cursor: "pointer"
          }}
        >
          Single Listing
        </button>
        <button
          onClick={() => { setBatchMode(true); setResult(null); setPreview(null); }}
          style={{
            padding: "8px 16px",
            background: batchMode ? "#007bff" : "#e9ecef",
            color: batchMode ? "white" : "#495057",
            border: "1px solid #dee2e6",
            borderRadius: 4,
            cursor: "pointer"
          }}
        >
          Batch Mode
        </button>
      </div>

      {/* Single Listing Mode */}
      {!batchMode && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Form */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, padding: 20 }}>
            <h3 style={{ marginTop: 0 }}>Listing Details</h3>
            
            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: "bold" }}>SKU:</label>
              <input
                type="text"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder="e.g., JAL00001"
                style={{ width: "100%", padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4 }}
              />
            </div>

            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: "bold" }}>Price (€):</label>
              <input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="e.g., 29.99"
                style={{ width: "100%", padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4 }}
              />
            </div>

            <div style={{ marginBottom: 15 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: "bold" }}>Quantity:</label>
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                style={{ width: "100%", padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4 }}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", marginBottom: 6, fontWeight: "bold" }}>Condition:</label>
              <select
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                style={{ width: "100%", padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4 }}
              >
                {conditions.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={handlePreview}
                disabled={previewing}
                style={{ 
                  flex: 1, 
                  padding: "10px", 
                  background: "#17a2b8", 
                  color: "white", 
                  border: "none", 
                  borderRadius: 4, 
                  cursor: previewing ? "not-allowed" : "pointer",
                  fontSize: 14,
                  fontWeight: "bold"
                }}
              >
                {previewing ? "Loading..." : "Preview"}
              </button>
              <button
                onClick={handleCreateListing}
                disabled={loading}
                style={{ 
                  flex: 1, 
                  padding: "10px", 
                  background: "#28a745", 
                  color: "white", 
                  border: "none", 
                  borderRadius: 4, 
                  cursor: loading ? "not-allowed" : "pointer",
                  fontSize: 14,
                  fontWeight: "bold"
                }}
              >
                {loading ? "Creating..." : "Create Listing"}
              </button>
            </div>
          </div>

          {/* Preview */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, padding: 20, maxHeight: 600, overflow: "auto" }}>
            {preview ? (
              <>
                <h3 style={{ marginTop: 0 }}>Preview</h3>
                <div style={{ marginBottom: 15 }}>
                  <strong>Title:</strong><br />
                  {preview.title || <em style={{ color: "#999" }}>No title</em>}
                </div>
                <div style={{ marginBottom: 15 }}>
                  <strong>Price:</strong> €{preview.price}<br />
                  <strong>Quantity:</strong> {preview.quantity}<br />
                  <strong>Condition:</strong> {preview.condition}
                </div>
                {preview.description && (
                  <div style={{ marginBottom: 15 }}>
                    <strong>Description:</strong>
                    <div 
                      style={{ 
                        marginTop: 8, 
                        padding: 10, 
                        background: "#f9f9f9", 
                        border: "1px solid #e0e0e0", 
                        borderRadius: 4,
                        fontSize: 13,
                        maxHeight: 200,
                        overflow: "auto"
                      }}
                      dangerouslySetInnerHTML={{ __html: preview.description }}
                    />
                  </div>
                )}
                {preview.images && preview.images.length > 0 && (
                  <div>
                    <strong>Images ({preview.images.length}):</strong>
                    <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
                      {preview.images.slice(0, 6).map((img, i) => (
                        <div key={i} style={{ 
                          width: "100%", 
                          paddingBottom: "100%", 
                          background: "#f0f0f0", 
                          borderRadius: 4,
                          position: "relative"
                        }}>
                          <div style={{ 
                            position: "absolute", 
                            top: 0, 
                            left: 0, 
                            right: 0, 
                            bottom: 0,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 11,
                            color: "#666"
                          }}>
                            Image {i + 1}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: "center", color: "#999", paddingTop: 100 }}>
                Click "Preview" to see listing details
              </div>
            )}
          </div>
        </div>
      )}

      {/* Batch Mode */}
      {batchMode && (
        <div>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 8, fontWeight: "bold" }}>
              Batch Data (format: SKU,price,quantity,condition):
            </div>
            <textarea
              value={batchData}
              onChange={(e) => setBatchData(e.target.value)}
              placeholder="JAL00001,29.99,1,Neu&#10;JAL00002,39.99,2,Neuwertig&#10;JAL00003,19.99,1,Gut"
              rows={12}
              style={{ width: "100%", padding: 8, fontSize: 13, border: "1px solid #ddd", borderRadius: 4, fontFamily: "monospace" }}
            />
            <button
              onClick={handleBatchCreate}
              disabled={loading}
              style={{ marginTop: 10, padding: "8px 24px", background: "#28a745", color: "white", border: "none", borderRadius: 4, cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "Creating..." : `Create ${batchData.split("\n").filter(Boolean).length} Listings`}
            </button>
          </div>

          {/* Batch Results */}
          {batchResults.length > 0 && (
            <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", fontWeight: "bold" }}>
                Batch Results ({batchResults.filter(r => r.success).length}/{batchResults.length} successful)
              </div>
              <div style={{ maxHeight: 500, overflow: "auto" }}>
                {batchResults.map((r, idx) => (
                  <div key={idx} style={{ padding: 12, borderBottom: "1px solid #eee", background: r.success ? "white" : "#fff8f8" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong>{r.sku}</strong>
                        <span style={{ marginLeft: 10, fontSize: 13, color: r.success ? "#28a745" : "#dc3545" }}>
                          {r.success ? "✓" : "✗"}
                        </span>
                      </div>
                      {r.listing_id && (
                        <a href={`https://www.ebay.de/itm/${r.listing_id}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "#007bff" }}>
                          View →
                        </a>
                      )}
                    </div>
                    {!r.success && r.message && (
                      <div style={{ marginTop: 6, fontSize: 12, color: "#dc3545" }}>
                        {r.message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

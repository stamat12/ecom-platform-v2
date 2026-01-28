import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export default function EbayEnrichPage() {
  const [sku, setSku] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState(null);
  const [validation, setValidation] = useState(null);
  const [error, setError] = useState("");
  const [batchMode, setBatchMode] = useState(false);
  const [batchSkus, setBatchSkus] = useState("");
  const [batchResults, setBatchResults] = useState([]);

  const handleEnrichSingle = async () => {
    if (!sku.trim()) {
      setError("Please enter a SKU");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);
      
      const res = await fetch("/api/ebay/enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku: sku.trim(), force: false })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Enrichment failed");
      }

      const data = await res.json();
      setResult(data);

      // Auto-validate after enrichment
      await handleValidate(sku.trim());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (skuToValidate = null) => {
    const targetSku = skuToValidate || sku.trim();
    if (!targetSku) return;

    try {
      setValidating(true);
      const res = await fetch(`/api/ebay/validate/${encodeURIComponent(targetSku)}`);
      if (!res.ok) throw new Error("Validation failed");
      const data = await res.json();
      setValidation(data);
    } catch (e) {
      console.error("Validation error:", e);
    } finally {
      setValidating(false);
    }
  };

  const handleEnrichBatch = async () => {
    const skus = batchSkus.split("\n").map(s => s.trim()).filter(Boolean);
    if (skus.length === 0) {
      setError("Please enter at least one SKU");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setBatchResults([]);

      const res = await fetch("/api/ebay/enrich/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skus, force: false })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Batch enrichment failed");
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
        <h1 style={{ margin: 0 }}>eBay Field Enrichment</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to="/ebay/schemas" style={{ padding: "8px 16px", background: "#6c757d", color: "white", textDecoration: "none", borderRadius: 4 }}>
            ← Schemas
          </Link>
          <Link to="/ebay/listings" style={{ padding: "8px 16px", background: "#007bff", color: "white", textDecoration: "none", borderRadius: 4 }}>
            Listings →
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #fcc", borderRadius: 4, marginBottom: 20, color: "#c00" }}>
          Error: {error}
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
          Single SKU
        </button>
        <button
          onClick={() => { setBatchMode(true); setResult(null); setValidation(null); }}
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

      {/* Single SKU Mode */}
      {!batchMode && (
        <div>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 8, fontWeight: "bold" }}>SKU:</div>
            <div style={{ display: "flex", gap: 10 }}>
              <input
                type="text"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder="Enter SKU (e.g., JAL00001)"
                style={{ flex: 1, padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4 }}
                onKeyDown={(e) => e.key === "Enter" && handleEnrichSingle()}
              />
              <button
                onClick={handleEnrichSingle}
                disabled={loading}
                style={{ padding: "8px 24px", background: "#28a745", color: "white", border: "none", borderRadius: 4, cursor: loading ? "not-allowed" : "pointer" }}
              >
                {loading ? "Enriching..." : "Enrich Fields"}
              </button>
              <button
                onClick={() => handleValidate()}
                disabled={validating || !sku.trim()}
                style={{ padding: "8px 16px", background: "#17a2b8", color: "white", border: "none", borderRadius: 4, cursor: (validating || !sku.trim()) ? "not-allowed" : "pointer" }}
              >
                {validating ? "Validating..." : "Validate"}
              </button>
            </div>
          </div>

          {/* Validation Results */}
          {validation && (
            <div style={{ 
              marginBottom: 20, 
              padding: 15, 
              border: `2px solid ${validation.valid ? "#28a745" : "#ffc107"}`, 
              borderRadius: 4,
              background: validation.valid ? "#f0fff4" : "#fff9e6"
            }}>
              <div style={{ fontWeight: "bold", fontSize: 16, marginBottom: 10 }}>
                {validation.valid ? "✓ All Required Fields Filled" : "⚠ Missing Required Fields"}
              </div>
              <div style={{ fontSize: 13, color: "#666" }}>
                Category: {validation.category_name} (ID: {validation.category_id})
              </div>
              <div style={{ fontSize: 13, marginTop: 6 }}>
                Required: {validation.filled_required}/{validation.total_required} filled | 
                Optional: {validation.filled_optional}/{validation.total_optional} filled
              </div>
              {validation.missing_required && validation.missing_required.length > 0 && (
                <div style={{ marginTop: 10, padding: 10, background: "#fff", borderRadius: 4 }}>
                  <div style={{ fontWeight: "bold", color: "#d32f2f", marginBottom: 6 }}>Missing Required:</div>
                  <div style={{ fontSize: 13 }}>{validation.missing_required.join(", ")}</div>
                </div>
              )}
            </div>
          )}

          {/* Enrichment Results */}
          {result && (
            <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", fontWeight: "bold" }}>
                Enrichment Results
              </div>
              <div style={{ padding: 15 }}>
                <div style={{ marginBottom: 15 }}>
                  <div style={{ fontSize: 13, color: "#666" }}>Updated {result.updated_fields} fields using {result.used_images} images</div>
                  {result.missing_required && result.missing_required.length > 0 && (
                    <div style={{ marginTop: 6, color: "#ffc107" }}>
                      ⚠ {result.missing_required.length} required fields still missing
                    </div>
                  )}
                </div>

                {/* Required Fields */}
                {result.required_fields && Object.keys(result.required_fields).length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <h3 style={{ fontSize: 15, margin: "0 0 10px 0", color: "#d32f2f" }}>Required Fields</h3>
                    {Object.entries(result.required_fields).map(([name, value]) => (
                      <div key={name} style={{ marginBottom: 8, padding: 8, background: "#fff8f8", border: "1px solid #ffe0e0", borderRadius: 4 }}>
                        <strong>{name}:</strong> {value || <em style={{ color: "#999" }}>empty</em>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Optional Fields */}
                {result.optional_fields && Object.keys(result.optional_fields).length > 0 && (
                  <div>
                    <h3 style={{ fontSize: 15, margin: "0 0 10px 0", color: "#1976d2" }}>Optional Fields</h3>
                    {Object.entries(result.optional_fields).map(([name, value]) => (
                      <div key={name} style={{ marginBottom: 8, padding: 8, background: "#f8f8ff", border: "1px solid #e0e0ff", borderRadius: 4 }}>
                        <strong>{name}:</strong> {value || <em style={{ color: "#999" }}>empty</em>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Batch Mode */}
      {batchMode && (
        <div>
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 8, fontWeight: "bold" }}>SKUs (one per line):</div>
            <textarea
              value={batchSkus}
              onChange={(e) => setBatchSkus(e.target.value)}
              placeholder="JAL00001&#10;JAL00002&#10;JAL00003"
              rows={10}
              style={{ width: "100%", padding: 8, fontSize: 14, border: "1px solid #ddd", borderRadius: 4, fontFamily: "monospace" }}
            />
            <button
              onClick={handleEnrichBatch}
              disabled={loading}
              style={{ marginTop: 10, padding: "8px 24px", background: "#28a745", color: "white", border: "none", borderRadius: 4, cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "Enriching..." : `Enrich ${batchSkus.split("\n").filter(Boolean).length} SKUs`}
            </button>
          </div>

          {/* Batch Results */}
          {batchResults.length > 0 && (
            <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", fontWeight: "bold" }}>
                Batch Results ({batchResults.length} SKUs)
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
                      <div style={{ fontSize: 13, color: "#666" }}>
                        {r.updated_fields} fields updated
                      </div>
                    </div>
                    {r.missing_required && r.missing_required.length > 0 && (
                      <div style={{ marginTop: 6, fontSize: 12, color: "#ffc107" }}>
                        ⚠ Missing: {r.missing_required.join(", ")}
                      </div>
                    )}
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

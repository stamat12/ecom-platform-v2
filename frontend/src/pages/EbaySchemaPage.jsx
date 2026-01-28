import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

export default function EbaySchemaPage() {
  const [schemas, setSchemas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadSchemas();
  }, []);

  const loadSchemas = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/ebay/schemas/list");
      if (!res.ok) throw new Error("Failed to load schemas");
      const data = await res.json();
      setSchemas(data.schemas || []);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const loadSchemaDetail = async (categoryId) => {
    try {
      const res = await fetch(`/api/ebay/schemas/${categoryId}`);
      if (!res.ok) throw new Error("Failed to load schema detail");
      const data = await res.json();
      setSelectedSchema(data);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleRefreshAll = async () => {
    if (!confirm("Refresh all schemas from eBay API? This may take a few minutes.")) return;
    
    try {
      setRefreshing(true);
      setError("");
      const res = await fetch("/api/ebay/schemas/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force: true })
      });
      
      if (!res.ok) throw new Error("Failed to refresh schemas");
      const data = await res.json();
      
      alert(`Refreshed ${data.refreshed_count} schemas. ${data.failed_count} failed.`);
      await loadSchemas();
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 style={{ margin: 0 }}>eBay Category Schemas</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <button 
            onClick={handleRefreshAll} 
            disabled={refreshing}
            style={{ padding: "8px 16px", cursor: refreshing ? "not-allowed" : "pointer" }}
          >
            {refreshing ? "Refreshing..." : "Refresh All Schemas"}
          </button>
          <Link to="/ebay/enrich" style={{ padding: "8px 16px", background: "#007bff", color: "white", textDecoration: "none", borderRadius: 4 }}>
            Field Enrichment →
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #fcc", borderRadius: 4, marginBottom: 20, color: "#c00" }}>
          Error: {error}
        </div>
      )}

      {loading ? (
        <div>Loading schemas...</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 20 }}>
          {/* Schema List */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd", fontWeight: "bold" }}>
              Categories ({schemas.length})
            </div>
            <div style={{ maxHeight: 600, overflow: "auto" }}>
              {schemas.map((schema) => (
                <div
                  key={schema.category_id}
                  onClick={() => loadSchemaDetail(schema.category_id)}
                  style={{
                    padding: 12,
                    borderBottom: "1px solid #eee",
                    cursor: "pointer",
                    background: selectedSchema?.category_id === schema.category_id ? "#e3f2fd" : "white"
                  }}
                >
                  <div style={{ fontWeight: "bold", fontSize: 14 }}>{schema.category_id}</div>
                  <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{schema.category_name}</div>
                  {schema.has_fees && (
                    <div style={{ fontSize: 11, color: "#28a745", marginTop: 4 }}>✓ Fees data</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Schema Detail */}
          <div style={{ border: "1px solid #ddd", borderRadius: 4, overflow: "hidden" }}>
            {selectedSchema ? (
              <>
                <div style={{ padding: 12, background: "#f5f5f5", borderBottom: "1px solid #ddd" }}>
                  <div style={{ fontWeight: "bold", fontSize: 16 }}>{selectedSchema.category_name || "Schema Details"}</div>
                  <div style={{ fontSize: 13, color: "#666", marginTop: 4 }}>Category ID: {selectedSchema.category_id}</div>
                  {selectedSchema.metadata?.fees && (
                    <div style={{ fontSize: 12, color: "#666", marginTop: 8 }}>
                      <strong>Fees:</strong> Payment €{selectedSchema.metadata.fees.payment_fee || 0}, Commission {((selectedSchema.metadata.fees.sales_commission_percentage || 0) * 100).toFixed(1)}%
                    </div>
                  )}
                </div>

                <div style={{ padding: 12, maxHeight: 600, overflow: "auto" }}>
                  {/* Required Fields */}
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ margin: "0 0 12px 0", fontSize: 15, color: "#d32f2f" }}>
                      Required Fields ({selectedSchema.schema?.required?.length || 0})
                    </h3>
                    {(selectedSchema.schema?.required || []).map((field, idx) => (
                      <div key={idx} style={{ marginBottom: 12, padding: 10, background: "#fff8f8", border: "1px solid #ffe0e0", borderRadius: 4 }}>
                        <div style={{ fontWeight: "bold", color: "#d32f2f" }}>{field.name}</div>
                        {field.values && field.values.length > 0 && (
                          <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
                            Allowed values ({field.values.length}): {field.values.slice(0, 10).join(", ")}
                            {field.values.length > 10 && "..."}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Optional Fields */}
                  <div>
                    <h3 style={{ margin: "0 0 12px 0", fontSize: 15, color: "#1976d2" }}>
                      Optional Fields ({selectedSchema.schema?.optional?.length || 0})
                    </h3>
                    {(selectedSchema.schema?.optional || []).map((field, idx) => (
                      <div key={idx} style={{ marginBottom: 12, padding: 10, background: "#f8f8ff", border: "1px solid #e0e0ff", borderRadius: 4 }}>
                        <div style={{ fontWeight: "bold", color: "#1976d2" }}>{field.name}</div>
                        {field.values && field.values.length > 0 && (
                          <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
                            Allowed values ({field.values.length}): {field.values.slice(0, 10).join(", ")}
                            {field.values.length > 10 && "..."}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div style={{ padding: 40, textAlign: "center", color: "#999" }}>
                Select a category to view schema details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

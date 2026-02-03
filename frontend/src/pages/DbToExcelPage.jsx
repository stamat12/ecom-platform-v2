import { useState } from "react";
import { Link } from "react-router-dom";

export default function DbToExcelPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [syncResult, setSyncResult] = useState(null);

  const handleSyncDbToExcel = async () => {
    if (!confirm("Sync JSON data to Excel? This will update cells where there are changes.\n\nColumns updated:\n- Ebay Category\n- EAN\n- Product Condition\n- Intern Product Info\n- Intern Generated Info\n- OP\n- Status\n- Warehouse\n- Json Phone stock\n- Json Enhanced")) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");
      setSyncResult(null);

      const res = await fetch("/api/excel/sync-from-db", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Sync failed");
      }

      const data = await res.json();
      setSuccess(data.message);
      setSyncResult(data.stats);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px", maxWidth: "900px", margin: "0 auto" }}>
      <Link to="/" style={{ marginBottom: "20px", display: "inline-block" }}>
        ← Back to SKU List
      </Link>

      <h1>📊 DB to Excel Sync</h1>

      <div style={{ marginBottom: "20px", padding: "20px", backgroundColor: "#f0f0f0", borderRadius: "8px" }}>
        <h2>Sync JSON Data to Excel</h2>
        <p>This will update your Excel file with the latest data from the JSON files.</p>
        
        <h3>Columns that will be updated:</h3>
        <ul>
          <li>✅ Ebay Category</li>
          <li>✅ EAN</li>
          <li>✅ Product Condition</li>
          <li>✅ Intern Product Info</li>
          <li>✅ Intern Generated Info</li>
          <li>✅ OP</li>
          <li>✅ Status</li>
          <li>✅ Warehouse</li>
          <li>✅ Json Phone stock (image counts)</li>
          <li>✅ Json Enhanced (image counts)</li>
        </ul>

        <p><strong>Note:</strong> Only cells with changes will be updated. Excel table format is preserved.</p>

        <button
          onClick={handleSyncDbToExcel}
          disabled={loading}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Syncing..." : "🔄 Start Sync"}
        </button>
      </div>

      {error && (
        <div style={{ 
          padding: "15px", 
          backgroundColor: "#f8d7da", 
          color: "#721c24", 
          borderRadius: "4px",
          marginBottom: "20px"
        }}>
          <strong>❌ Error:</strong> {error}
        </div>
      )}

      {success && (
        <div style={{ 
          padding: "15px", 
          backgroundColor: "#d4edda", 
          color: "#155724", 
          borderRadius: "4px",
          marginBottom: "20px"
        }}>
          <strong>✅ Success:</strong> {success}
        </div>
      )}

      {syncResult && (
        <div style={{
          padding: "20px",
          backgroundColor: "#e7f3ff",
          borderRadius: "8px",
          marginTop: "20px"
        }}>
          <h3>📈 Sync Statistics</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            <div>
              <p><strong>Rows Processed:</strong> {syncResult.rows_processed}</p>
              <p><strong>Changes Made:</strong> {syncResult.changes_made}</p>
            </div>
            <div>
              <p><strong>Columns Updated:</strong></p>
              <ul style={{ marginTop: "5px" }}>
                {syncResult.columns_updated && syncResult.columns_updated.map(col => (
                  <li key={col}>{col}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";

export default function DbToExcelPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [syncResult, setSyncResult] = useState(null);

  const handleSyncDbToExcel = async () => {
    if (!confirm("Sync JSON data to Excel? This will update cells where there are changes.\n\nColumns updated:\n- Category (eBay path)\n- EAN\n- Condition\n- Gender, Brand, Color, Size\n- More details, Materials, Keywords\n- OP\n- Status\n- Lager\n- Images JSON Phone, Stock, Enhanced\n- JSON (Yes/empty)\n- Images (folder count)")) {
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
          <li>✅ <strong>Category</strong> (from Ebay Category section)</li>
          <li>✅ <strong>EAN</strong> (from EAN section)</li>
          <li>✅ <strong>Condition</strong> (from Product Condition section)</li>
          <li>✅ <strong>Gender</strong> (from Intern Product Info section)</li>
          <li>✅ <strong>Brand</strong> (from Intern Product Info section)</li>
          <li>✅ <strong>Color</strong> (from Intern Product Info section)</li>
          <li>✅ <strong>Size</strong> (from Intern Product Info section)</li>
          <li>✅ <strong>More details</strong> (from Intern Generated Info section)</li>
          <li>✅ <strong>Materials</strong> (from Intern Generated Info section)</li>
          <li>✅ <strong>Keywords</strong> (from Intern Generated Info section)</li>
          <li>✅ <strong>OP</strong> (from OP section)</li>
          <li>✅ <strong>Status</strong> (from Status section)</li>
          <li>✅ <strong>Lager</strong> (from Warehouse section)</li>
          <li>✅ <strong>Images JSON Phone</strong> (phone image count)</li>
          <li>✅ <strong>Images JSON Stock</strong> (stock image count)</li>
          <li>✅ <strong>Images JSON Enhanced</strong> (enhanced image count)</li>
          <li>✅ <strong>JSON</strong> ("Yes" if JSON file exists, empty otherwise)</li>
          <li>✅ <strong>Images</strong> (folder images count from cache)</li>
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

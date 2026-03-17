import { useState } from "react";
import { Link } from "react-router-dom";

const SYNCABLE_COLUMNS = [
  "Category",
  "EAN",
  "Condition",
  "Gender",
  "Brand",
  "Color",
  "Size",
  "More details",
  "Materials",
  "Keywords",
  "OP",
  "Status",
  "Lager",
  "Images JSON Phone",
  "Images JSON Stock",
  "Images JSON Enhanced",
  "JSON",
  "Images",
];

export default function DbToExcelPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [syncResult, setSyncResult] = useState(null);
  const [selectedColumns, setSelectedColumns] = useState(new Set(SYNCABLE_COLUMNS));

  const toggleColumn = (column) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(column)) {
        next.delete(column);
      } else {
        next.add(column);
      }
      return next;
    });
  };

  const handleSyncDbToExcel = async () => {
    const chosenColumns = Array.from(selectedColumns);
    if (chosenColumns.length === 0) {
      alert("Select at least one column to sync.");
      return;
    }

    if (!confirm(`Sync inventory.db data to Excel? This will update cells where there are changes.\n\nSelected columns (${chosenColumns.length}):\n- ${chosenColumns.join("\n- ")}`)) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");
      setSyncResult(null);

      const res = await fetch("/api/excel/sync-from-db", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sheet_name: "Inventory",
          columns: chosenColumns,
        }),
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
        <h2>Sync inventory.db Data to Excel</h2>
        <p>This will update your Excel file with the latest data from the inventory database.</p>
        
        <h3>Choose columns to update:</h3>
        <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => setSelectedColumns(new Set(SYNCABLE_COLUMNS))}
            style={{ padding: "6px 10px", border: "1px solid #bbb", borderRadius: "4px", backgroundColor: "white", cursor: "pointer" }}
          >
            Select all
          </button>
          <button
            type="button"
            onClick={() => setSelectedColumns(new Set())}
            style={{ padding: "6px 10px", border: "1px solid #bbb", borderRadius: "4px", backgroundColor: "white", cursor: "pointer" }}
          >
            Clear all
          </button>
          <span style={{ fontSize: "13px", color: "#555", alignSelf: "center" }}>
            {selectedColumns.size} selected
          </span>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "8px",
          marginBottom: "14px",
        }}>
          {SYNCABLE_COLUMNS.map((col) => (
            <label key={col} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "14px", backgroundColor: "#fff", border: "1px solid #ddd", borderRadius: "4px", padding: "8px 10px" }}>
              <input
                type="checkbox"
                checked={selectedColumns.has(col)}
                onChange={() => toggleColumn(col)}
              />
              <span>{col}</span>
            </label>
          ))}
        </div>

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
              <p><strong>Rows Changed:</strong> {syncResult.rows_changed ?? syncResult.row_updates_total ?? 0}</p>
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

          {syncResult.changes_by_column && Object.keys(syncResult.changes_by_column).length > 0 && (
            <div style={{ marginTop: "16px" }}>
              <h4 style={{ margin: "0 0 8px 0" }}>Changes by Column</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "8px" }}>
                {Object.entries(syncResult.changes_by_column).map(([col, count]) => (
                  <div key={col} style={{ backgroundColor: "#fff", border: "1px solid #cfe2ff", borderRadius: "6px", padding: "8px 10px", fontSize: "13px" }}>
                    <strong>{col}:</strong> {count}
                  </div>
                ))}
              </div>
            </div>
          )}

          {syncResult.row_updates_preview && syncResult.row_updates_preview.length > 0 && (
            <div style={{ marginTop: "16px" }}>
              <h4 style={{ margin: "0 0 8px 0" }}>Changed SKUs (Preview)</h4>
              <div style={{ maxHeight: "260px", overflowY: "auto", backgroundColor: "#fff", border: "1px solid #cfe2ff", borderRadius: "6px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f8fbff" }}>
                      <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e3eefc" }}>SKU</th>
                      <th style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e3eefc" }}>Updated Columns</th>
                      <th style={{ textAlign: "right", padding: "8px", borderBottom: "1px solid #e3eefc" }}>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncResult.row_updates_preview.map((row) => (
                      <tr key={row.sku}>
                        <td style={{ padding: "8px", borderBottom: "1px solid #f0f4fa", whiteSpace: "nowrap" }}>{row.sku}</td>
                        <td style={{ padding: "8px", borderBottom: "1px solid #f0f4fa" }}>{(row.updated_columns || []).join(", ")}</td>
                        <td style={{ padding: "8px", borderBottom: "1px solid #f0f4fa", textAlign: "right" }}>{row.updated_count || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {typeof syncResult.row_updates_total === "number" && syncResult.row_updates_total > syncResult.row_updates_preview.length && (
                <p style={{ marginTop: "8px", fontSize: "12px", color: "#555" }}>
                  Showing first {syncResult.row_updates_preview.length} of {syncResult.row_updates_total} changed SKUs.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

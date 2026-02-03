import { useState } from "react";
import { Link } from "react-router-dom";

export default function CleanupDatabasePage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cleanupResult, setCleanupResult] = useState(null);

  const handleCleanupDatabase = async () => {
    if (!confirm("Clean up duplicate SKUs in the inventory database?\n\nThis will:\n- Find all SKUs that appear more than once\n- Keep the first occurrence of each SKU\n- Delete all duplicate rows\n\nThis action cannot be undone. Make sure you have a backup!")) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccess("");
      setCleanupResult(null);

      const res = await fetch("/api/database/cleanup-duplicates", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Cleanup failed");
      }

      const data = await res.json();
      setSuccess(data.message);
      setCleanupResult(data.stats);
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

      <h1>🧹 Database Cleanup</h1>

      <div style={{ marginBottom: "20px", padding: "20px", backgroundColor: "#f0f0f0", borderRadius: "8px" }}>
        <h2>Remove Duplicate SKUs</h2>
        <p>The inventory database can accumulate duplicate entries for the same SKU. This tool will clean them up.</p>
        
        <h3>What this does:</h3>
        <ul>
          <li>✓ Scans the inventory table for duplicate SKUs</li>
          <li>✓ Keeps the first occurrence of each SKU (earliest row)</li>
          <li>✓ Deletes all duplicate rows</li>
          <li>✓ Shows how many rows were removed</li>
        </ul>

        <div style={{
          padding: "15px",
          backgroundColor: "#fff3cd",
          borderRadius: "4px",
          marginBottom: "20px",
          borderLeft: "4px solid #ff9800"
        }}>
          <strong>⚠️ Warning:</strong> This operation modifies the database directly. Make sure you have a backup before proceeding!
        </div>

        <button
          onClick={handleCleanupDatabase}
          disabled={loading}
          style={{
            padding: "12px 24px",
            fontSize: "16px",
            backgroundColor: loading ? "#ccc" : "#dc3545",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Cleaning up..." : "🧹 Start Cleanup"}
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

      {cleanupResult && (
        <div style={{
          padding: "20px",
          backgroundColor: "#e7f3ff",
          borderRadius: "8px",
          marginTop: "20px"
        }}>
          <h3>📊 Cleanup Results</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            <div>
              <p><strong>Rows Before:</strong> {cleanupResult.rows_before}</p>
              <p><strong>Rows After:</strong> {cleanupResult.rows_after}</p>
              <p style={{ color: "#dc3545", fontSize: "18px" }}>
                <strong>Rows Deleted:</strong> {cleanupResult.rows_deleted}
              </p>
            </div>
            <div>
              <p><strong>Duplicate SKUs Found:</strong> {cleanupResult.duplicate_skus_found}</p>
              {cleanupResult.sample_duplicates && cleanupResult.sample_duplicates.length > 0 && (
                <div>
                  <p><strong>Sample duplicates:</strong></p>
                  <ul style={{ marginTop: "5px", fontSize: "14px" }}>
                    {cleanupResult.sample_duplicates.map(sku => (
                      <li key={sku}>{sku}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

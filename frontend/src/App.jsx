import React, { useState } from "react";
import { Routes, Route, Navigate, Link } from "react-router-dom";
import SkuListPage from "./pages/SkuListPage.jsx";
import SkuDetailPage from "./pages/SkuDetailPage.jsx";
import SkuBatchPage from "./pages/SkuBatchPage.jsx";
import DbToExcelPage from "./pages/DbToExcelPage.jsx";
import CleanupDatabasePage from "./pages/CleanupDatabasePage.jsx";
import PromptManagerPage from "./pages/PromptManagerPage.jsx";
import EbayListingsCachePage from "./pages/EbayListingsCachePage.jsx";

export default function App() {
  const [ebayListingsComputing, setEbayListingsComputing] = useState(false);
  const [ebayListingsMode, setEbayListingsMode] = useState("");
  const [ebayListingsProgress, setEbayListingsProgress] = useState({
    page: 0,
    total_pages: 0,
    count: 0,
    detail_lookups: 0,
  });

  const computeEbayListingsFast = async () => {
    setEbayListingsComputing(true);
    setEbayListingsMode("fast");
    setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
    try {
      const eventSource = new EventSource("/api/skus/ebay-listings/compute-fast");

      eventSource.onmessage = (event) => {
        try {
          const progress = JSON.parse(event.data);
          if (progress.status === "progress") {
            setEbayListingsProgress({
              page: Number(progress.page || 0),
              total_pages: Number(progress.total_pages || 0),
              count: Number(progress.count || 0),
              detail_lookups: Number(progress.detail_lookups || 0),
            });
          } else if (progress.status === "complete") {
            eventSource.close();
            alert(`✅ Fast fetch completed: ${progress.count} eBay listings synced (${progress.total_pages} pages)`);
            setEbayListingsComputing(false);
            setEbayListingsMode("");
            setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
          } else if (progress.status === "error") {
            eventSource.close();
            alert(`❌ Fast fetch failed: ${progress.message || "Unknown error"}`);
            setEbayListingsComputing(false);
            setEbayListingsMode("");
            setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
          }
        } catch {
          eventSource.close();
          setEbayListingsComputing(false);
          setEbayListingsMode("");
          setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setEbayListingsComputing(false);
        setEbayListingsMode("");
        setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
      };
    } catch (error) {
      alert(`❌ Failed to start fast fetch: ${error.message}`);
      setEbayListingsComputing(false);
      setEbayListingsMode("");
      setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
    }
  };

  const computeEbayListingsDetailed = async () => {
    setEbayListingsComputing(true);
    setEbayListingsMode("detailed");
    setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
    try {
      const eventSource = new EventSource("/api/skus/ebay-listings/compute-detailed");

      eventSource.onmessage = (event) => {
        try {
          const progress = JSON.parse(event.data);
          if (progress.status === "progress") {
            setEbayListingsProgress({
              page: Number(progress.page || 0),
              total_pages: Number(progress.total_pages || 0),
              count: Number(progress.count || 0),
              detail_lookups: Number(progress.detail_lookups || 0),
            });
          } else if (progress.status === "complete") {
            eventSource.close();
            alert(`✅ Detailed fetch completed: ${progress.count} eBay listings synced with ${progress.detail_lookups || 0} enrichments (${progress.total_pages} pages)`);
            setEbayListingsComputing(false);
            setEbayListingsMode("");
            setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
          } else if (progress.status === "error") {
            eventSource.close();
            alert(`❌ Detailed fetch failed: ${progress.message || "Unknown error"}`);
            setEbayListingsComputing(false);
            setEbayListingsMode("");
            setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
          }
        } catch {
          eventSource.close();
          setEbayListingsComputing(false);
          setEbayListingsMode("");
          setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setEbayListingsComputing(false);
        setEbayListingsMode("");
        setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
      };
    } catch (error) {
      alert(`❌ Failed to start detailed fetch: ${error.message}`);
      setEbayListingsComputing(false);
      setEbayListingsMode("");
      setEbayListingsProgress({ page: 0, total_pages: 0, count: 0, detail_lookups: 0 });
    }
  };

  return (
    <div style={{ fontFamily: "system-ui, Arial", padding: 16 }}>
      <header style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <Link to="/skus" style={{ textDecoration: "none" }}>
          <h2 style={{ margin: 0 }}>SKU Manager</h2>
        </Link>
        <Link to="/db-to-excel" style={{ textDecoration: "none", marginLeft: "20px" }}>
          <span style={{ padding: "8px 16px", backgroundColor: "#28a745", color: "white", borderRadius: "4px", fontSize: "14px" }}>
            📊 DB to Excel
          </span>
        </Link>
        <Link to="/cleanup-db" style={{ textDecoration: "none" }}>
          <span style={{ padding: "8px 16px", backgroundColor: "#dc3545", color: "white", borderRadius: "4px", fontSize: "14px" }}>
            🧹 Cleanup DB
          </span>
        </Link>
        <Link to="/ebay-cache" style={{ textDecoration: "none" }}>
          <span style={{ padding: "8px 16px", backgroundColor: "#17a2b8", color: "white", borderRadius: "4px", fontSize: "14px" }}>
            🛒 eBay Cache
          </span>
        </Link>
        <Link to="/prompts" style={{ textDecoration: "none" }}>
          <span style={{ padding: "8px 16px", backgroundColor: "#6c757d", color: "white", borderRadius: "4px", fontSize: "14px" }}>
            Prompts
          </span>
        </Link>
        <button
          onClick={computeEbayListingsFast}
          disabled={ebayListingsComputing}
          style={{
            padding: "8px 16px",
            backgroundColor: ebayListingsComputing ? "#ccc" : "#17a2b8",
            color: "white",
            border: "none",
            borderRadius: "4px",
            fontSize: "14px",
            cursor: ebayListingsComputing ? "default" : "pointer"
          }}
        >
          {ebayListingsComputing && ebayListingsMode === "fast" ? "⏳ Fast Fetch..." : "⚡ eBay Fetch Fast"}
        </button>
        <button
          onClick={computeEbayListingsDetailed}
          disabled={ebayListingsComputing}
          style={{
            padding: "8px 16px",
            backgroundColor: ebayListingsComputing ? "#ccc" : "#6f42c1",
            color: "white",
            border: "none",
            borderRadius: "4px",
            fontSize: "14px",
            cursor: ebayListingsComputing ? "default" : "pointer"
          }}
        >
          {ebayListingsComputing && ebayListingsMode === "detailed" ? "⏳ Detailed Fetch..." : "🔎 eBay Fetch Detailed"}
        </button>
        <div style={{ marginLeft: "auto", color: "#666" }}>FastAPI + React (Vite) + eBay Integration</div>
      </header>

      {ebayListingsComputing && ebayListingsProgress.total_pages > 0 && (
        <div style={{ marginBottom: 16, background: "#f8f9fa", border: "1px solid #dee2e6", borderRadius: 6, padding: 10 }}>
          <div style={{ fontSize: "13px", marginBottom: 6, color: "#333" }}>
            {ebayListingsMode === "detailed" ? "🔎 Detailed Fetch" : "⚡ Fast Fetch"} • Page {ebayListingsProgress.page} / {ebayListingsProgress.total_pages} • Listings: {ebayListingsProgress.count}
            {ebayListingsMode === "detailed" ? ` • Enrichments: ${ebayListingsProgress.detail_lookups}` : ""}
          </div>
          <div style={{ width: "100%", height: 14, background: "#e0e0e0", borderRadius: 4, overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                background: ebayListingsMode === "detailed" ? "#6f42c1" : "#17a2b8",
                width: `${Math.min(100, (ebayListingsProgress.page / ebayListingsProgress.total_pages) * 100)}%`,
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      )}

      <Routes>
        <Route path="/" element={<Navigate to="/skus" replace />} />
        <Route path="/skus" element={<SkuListPage />} />
        <Route path="/skus/batch" element={<SkuBatchPage />} />
        <Route path="/skus/:sku" element={<SkuDetailPage />} />
        <Route path="/db-to-excel" element={<DbToExcelPage />} />
        <Route path="/cleanup-db" element={<CleanupDatabasePage />} />
        <Route path="/prompts" element={<PromptManagerPage />} />
        <Route path="/ebay-cache" element={<EbayListingsCachePage />} />
      </Routes>
    </div>
  );
}


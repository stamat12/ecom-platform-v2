import React from "react";
import { Routes, Route, Navigate, Link } from "react-router-dom";
import SkuListPage from "./pages/SkuListPage.jsx";
import SkuDetailPage from "./pages/SkuDetailPage.jsx";
import SkuBatchPage from "./pages/SkuBatchPage.jsx";
import EbaySchemaPage from "./pages/EbaySchemaPage.jsx";
import EbayEnrichPage from "./pages/EbayEnrichPage.jsx";
import EbayListingPage from "./pages/EbayListingPage.jsx";
import EbaySyncPage from "./pages/EbaySyncPage.jsx";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui, Arial", padding: 16 }}>
      <header style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <Link to="/skus" style={{ textDecoration: "none" }}>
          <h2 style={{ margin: 0 }}>SKU Manager</h2>
        </Link>
        <div style={{ color: "#666" }}>•</div>
        <Link to="/ebay/schemas" style={{ textDecoration: "none", color: "#007bff" }}>
          eBay Integration
        </Link>
        <div style={{ marginLeft: "auto", color: "#666" }}>FastAPI + React (Vite)</div>
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/skus" replace />} />
        <Route path="/skus" element={<SkuListPage />} />
        <Route path="/skus/batch" element={<SkuBatchPage />} />
        <Route path="/skus/:sku" element={<SkuDetailPage />} />
        
        {/* eBay Routes */}
        <Route path="/ebay/schemas" element={<EbaySchemaPage />} />
        <Route path="/ebay/enrich" element={<EbayEnrichPage />} />
        <Route path="/ebay/listings" element={<EbayListingPage />} />
        <Route path="/ebay/sync" element={<EbaySyncPage />} />
      </Routes>
    </div>
  );
}


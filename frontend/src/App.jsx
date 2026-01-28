import React from "react";
import { Routes, Route, Navigate, Link } from "react-router-dom";
import SkuListPage from "./pages/SkuListPage.jsx";
import SkuDetailPage from "./pages/SkuDetailPage.jsx";
import SkuBatchPage from "./pages/SkuBatchPage.jsx";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui, Arial", padding: 16 }}>
      <header style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <Link to="/skus" style={{ textDecoration: "none" }}>
          <h2 style={{ margin: 0 }}>SKU Manager</h2>
        </Link>
        <div style={{ marginLeft: "auto", color: "#666" }}>FastAPI + React (Vite) + eBay Integration</div>
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/skus" replace />} />
        <Route path="/skus" element={<SkuListPage />} />
        <Route path="/skus/batch" element={<SkuBatchPage />} />
        <Route path="/skus/:sku" element={<SkuDetailPage />} />
      </Routes>
    </div>
  );
}


import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = "http://localhost:8000";

const ImagePlaceholder = ({ src, alt, onClick, style }) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const ref = useRef();

  useEffect(() => {
    if (!ref.current) return;
    
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        const img = new Image();
        img.onload = () => setLoaded(true);
        img.onerror = () => setError(true);
        img.src = src;
      }
    });
    
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [src]);

  return (
    <div
      ref={ref}
      onClick={onClick}
      style={{
        width: "60px",
        height: "60px",
        backgroundColor: "#f0f0f0",
        borderRadius: "4px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        cursor: "pointer",
        ...style,
      }}
    >
      {loaded && !error ? (
        <img src={src} alt={alt} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : error ? (
        <span style={{ fontSize: "12px", color: "#999" }}>❌</span>
      ) : (
        <span style={{ fontSize: "12px", color: "#ccc" }}>📷</span>
      )}
    </div>
  );
};

export default function EbayListingsCachePage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedImage, setSelectedImage] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const LIMIT = 200;

  // Filters
  const [filters, setFilters] = useState({
    search_sku: "",
    search_title: "",
    min_price: "",
    max_price: "",
    min_profit_margin: "",
    max_profit_margin: "",
    listing_status: "",
    condition: "",
    sort_by: "sku",
    sort_order: "asc",
  });

  const fetchListings = async (pageNum = 1) => {
    console.log("fetchListings called with pageNum:", pageNum);
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: pageNum,
        limit: LIMIT,
        search_sku: filters.search_sku || "",
        search_title: filters.search_title || "",
        min_price: filters.min_price || "0",
        max_price: filters.max_price || "999999",
        min_profit_margin: filters.min_profit_margin || "-999999",
        max_profit_margin: filters.max_profit_margin || "999999",
        listing_status: filters.listing_status || "",
        condition: filters.condition || "",
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      });

      const url = `${API_BASE}/api/ebay-cache/de-listings?${params}`;
      console.log("Fetching from URL:", url);
      
      const response = await fetch(url);
      console.log("Response status:", response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Response error:", errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}\n${errorText}`);
      }
      
      const data = await response.json();
      console.log("Received data - Total:", data.total, "Listings count:", data.listings?.length);
      
      if (!data || typeof data.total === "undefined") {
        throw new Error("Invalid response format: missing total field");
      }
      
      setListings(data.listings || []);
      setTotal(data.total || 0);
      setPage(pageNum);
    } catch (error) {
      console.error("Error fetching listings:", error);
      console.error("Error type:", error.name);
      console.error("Error message:", error.message);
      setError(`Failed to load listings: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Test backend connectivity on mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        console.log("Testing backend connection...");
        const response = await fetch(`${API_BASE}/health`);
        console.log("Health check status:", response.status);
        if (response.ok) {
          console.log("✓ Backend is reachable - fetching listings");
          // Backend is reachable, now trigger initial fetch by setting page to 1 if it's 0
          if (page === 0) {
            setPage(1);
          } else {
            // If page is already set, fetch directly
            fetchListings(page);
          }
        }
      } catch (err) {
        console.error("✗ Cannot reach backend at", API_BASE, err);
        setError(`Cannot reach backend at ${API_BASE}. Make sure Uvicorn is running on port 8000 and CORS is enabled.`);
      }
    };
    testConnection();
  }, []);

  // Fetch listings when page changes
  useEffect(() => {
    if (page > 0) {
      console.log("Page changed to", page, "fetching...");
      fetchListings(page);
    }
  }, [page]);

  // When filters change, reset to page 1 and fetch immediately
  useEffect(() => {
    console.log("Filters changed, resetting to page 1 and fetching...");
    setPage(1);
    fetchListings(1);  // Fetch immediately with filters instead of waiting for page state change
  }, [
    filters.search_sku,
    filters.search_title,
    filters.min_price,
    filters.max_price,
    filters.min_profit_margin,
    filters.max_profit_margin,
    filters.listing_status,
    filters.condition,
    filters.sort_by,
    filters.sort_order,
  ]);

  const totalPages = Math.ceil(total / LIMIT);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => {
      const updated = { ...prev, [key]: value };
      setPage(1);  // Reset to page 1 when filter changes
      return updated;
    });
  };

  const resetFilters = () => {
    setFilters({
      search_sku: "",
      search_title: "",
      min_price: "",
      max_price: "",
      min_profit_margin: "",
      max_profit_margin: "",
      listing_status: "",
      condition: "",
      sort_by: "sku",
      sort_order: "asc",
    });
  };

  return (
    <div style={{ padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: "8px 12px",
            backgroundColor: "#6c757d",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "14px",
          }}
        >
          ← Back
        </button>
        <h1 style={{ margin: 0 }}>📊 eBay DE Listings Cache</h1>
      </div>

      {error && (
        <div style={{
          padding: "12px",
          backgroundColor: "#f8d7da",
          color: "#721c24",
          borderRadius: "4px",
          marginBottom: "20px",
          border: "1px solid #f5c6cb",
        }}>
          ❌ {error}
        </div>
      )}

      {loading && listings.length === 0 && (
        <div style={{
          padding: "20px",
          backgroundColor: "#d1ecf1",
          color: "#0c5460",
          borderRadius: "4px",
          marginBottom: "20px",
          border: "1px solid #bee5eb",
        }}>
          ⏳ Loading listings from cache... (Check browser console for details)
        </div>
      )}

      <p style={{ color: "#666", marginBottom: "20px" }}>
        Total: <strong>{total.toLocaleString()}</strong> DE marketplace listings | Showing page <strong>{page}</strong> of{" "}
        <strong>{totalPages}</strong> ({LIMIT} per page)
      </p>

      {/* Filters Section */}
      <div style={{
        backgroundColor: "#f8f9fa",
        padding: "20px",
        borderRadius: "8px",
        marginBottom: "20px",
        border: "1px solid #dee2e6",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
          <h3 style={{ margin: 0 }}>🔍 Filters</h3>
          <button
            onClick={resetFilters}
            style={{
              padding: "8px 12px",
              backgroundColor: "#6c757d",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Reset All
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
          {/* SKU Search */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>SKU</label>
            <input
              type="text"
              placeholder="Search SKU..."
              value={filters.search_sku}
              onChange={(e) => handleFilterChange("search_sku", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Title Search */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Title
            </label>
            <input
              type="text"
              placeholder="Search title..."
              value={filters.search_title}
              onChange={(e) => handleFilterChange("search_title", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Price Range */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Min Price (€)
            </label>
            <input
              type="number"
              placeholder="0"
              value={filters.min_price}
              onChange={(e) => handleFilterChange("min_price", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Max Price (€)
            </label>
            <input
              type="number"
              placeholder="999999"
              value={filters.max_price}
              onChange={(e) => handleFilterChange("max_price", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Profit Margin Range */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Min Profit % 
            </label>
            <input
              type="number"
              placeholder="-999999"
              value={filters.min_profit_margin}
              onChange={(e) => handleFilterChange("min_profit_margin", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Max Profit %
            </label>
            <input
              type="number"
              placeholder="999999"
              value={filters.max_profit_margin}
              onChange={(e) => handleFilterChange("max_profit_margin", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Status Filter */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Status
            </label>
            <select
              value={filters.listing_status}
              onChange={(e) => handleFilterChange("listing_status", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            >
              <option value="">All</option>
              <option value="Active">Active</option>
              <option value="Ended">Ended</option>
              <option value="Unsold">Unsold</option>
            </select>
          </div>

          {/* Condition Filter */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Condition
            </label>
            <input
              type="text"
              placeholder="e.g., Neu, Gebraucht..."
              value={filters.condition}
              onChange={(e) => handleFilterChange("condition", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Sort By */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Sort By
            </label>
            <select
              value={filters.sort_by}
              onChange={(e) => handleFilterChange("sort_by", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            >
              <option value="sku">SKU</option>
              <option value="price">Price</option>
              <option value="profit_margin">Profit Margin %</option>
              <option value="date">Date</option>
            </select>
          </div>

          {/* Sort Order */}
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>
              Order
            </label>
            <select
              value={filters.sort_order}
              onChange={(e) => handleFilterChange("sort_order", e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ccc",
                borderRadius: "4px",
                boxSizing: "border-box",
              }}
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#999" }}>⏳ Loading...</div>
      ) : (
        <>
          <div style={{ overflowX: "auto", marginBottom: "20px" }}>
            <table style={{
              width: "100%",
              borderCollapse: "collapse",
              backgroundColor: "white",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            }}>
              <thead>
                <tr style={{ backgroundColor: "#f8f9fa", borderBottom: "2px solid #dee2e6" }}>
                  <th style={{ padding: "12px", textAlign: "left", fontSize: "12px", fontWeight: "bold" }}>Image</th>
                  <th style={{ padding: "12px", textAlign: "left", fontSize: "12px", fontWeight: "bold" }}>SKU</th>
                  <th style={{ padding: "12px", textAlign: "left", fontSize: "12px", fontWeight: "bold" }}>Title</th>
                  <th style={{ padding: "12px", textAlign: "center", fontSize: "12px", fontWeight: "bold" }}>Price</th>
                  <th style={{ padding: "12px", textAlign: "center", fontSize: "12px", fontWeight: "bold" }}>Net Profit €</th>
                  <th style={{ padding: "12px", textAlign: "center", fontSize: "12px", fontWeight: "bold" }}>Profit %</th>
                  <th style={{ padding: "12px", textAlign: "center", fontSize: "12px", fontWeight: "bold" }}>Status</th>
                  <th style={{ padding: "12px", textAlign: "left", fontSize: "12px", fontWeight: "bold" }}>Condition</th>
                  <th style={{ padding: "12px", textAlign: "left", fontSize: "12px", fontWeight: "bold" }}>Link</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing, idx) => (
                  <tr key={idx} style={{
                    borderBottom: "1px solid #eee",
                    backgroundColor: idx % 2 === 0 ? "#ffffff" : "#f9f9f9",
                  }}>
                    <td style={{ padding: "10px" }}>
                      <ImagePlaceholder
                        src={listing.primary_image_url}
                        alt={listing.title}
                        onClick={() => setSelectedImage(listing.primary_image_url)}
                      />
                    </td>
                    <td style={{ padding: "10px", fontSize: "12px", fontWeight: "bold", whiteSpace: "nowrap" }}>
                      {listing.sku}
                    </td>
                    <td style={{ padding: "10px", fontSize: "12px", maxWidth: "300px", whiteSpace: "normal" }}>
                      <a href={listing.view_url} target="_blank" rel="noopener noreferrer" style={{ color: "#0066cc", textDecoration: "none" }}>
                        {listing.title}
                      </a>
                    </td>
                    <td style={{ padding: "10px", textAlign: "center", fontSize: "12px", fontWeight: "bold" }}>
                      €{listing.price?.toFixed(2)}
                    </td>
                    <td style={{ padding: "10px", textAlign: "center", fontSize: "12px", fontWeight: "bold", color: listing.profit_analysis?.net_profit > 0 ? "#28a745" : "#dc3545" }}>
                      €{listing.profit_analysis?.net_profit?.toFixed(2) || "N/A"}
                    </td>
                    <td style={{ padding: "10px", textAlign: "center", fontSize: "12px", fontWeight: "bold", color: listing.profit_analysis?.net_profit_margin_percent > 100 ? "#28a745" : listing.profit_analysis?.net_profit_margin_percent > 0 ? "#ffc107" : "#dc3545" }}>
                      {listing.profit_analysis?.net_profit_margin_percent?.toFixed(1)}%
                    </td>
                    <td style={{ padding: "10px", textAlign: "center", fontSize: "12px" }}>
                      <span style={{
                        padding: "4px 8px",
                        backgroundColor: listing.listing_status === "Active" ? "#d4edda" : "#f8d7da",
                        color: listing.listing_status === "Active" ? "#155724" : "#721c24",
                        borderRadius: "4px",
                        fontSize: "11px",
                      }}>
                        {listing.listing_status}
                      </span>
                    </td>
                    <td style={{ padding: "10px", fontSize: "11px", color: "#666" }}>
                      {listing.condition_name}
                    </td>
                    <td style={{ padding: "10px" }}>
                      <a href={listing.view_url} target="_blank" rel="noopener noreferrer" style={{ color: "#0066cc", fontSize: "12px" }}>
                        ↗️ eBay
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {listings.length === 0 && !loading && (
            <div style={{ textAlign: "center", padding: "40px", color: "#999" }}>
              No listings found matching your filters.
            </div>
          )}

          {/* Pagination Controls */}
          <div style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "10px",
            marginTop: "20px",
          }}>
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              style={{
                padding: "8px 12px",
                backgroundColor: page === 1 ? "#ccc" : "#007bff",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: page === 1 ? "default" : "pointer",
              }}
            >
              ← Previous
            </button>

            <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                const pageNum = page <= 3 ? i + 1 : page + i - 2;
                if (pageNum > totalPages) return null;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    style={{
                      padding: "6px 10px",
                      backgroundColor: pageNum === page ? "#007bff" : "#f0f0f0",
                      color: pageNum === page ? "white" : "#333",
                      border: "1px solid #ddd",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              style={{
                padding: "8px 12px",
                backgroundColor: page === totalPages ? "#ccc" : "#007bff",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: page === totalPages ? "default" : "pointer",
              }}
            >
              Next →
            </button>

            <span style={{ marginLeft: "20px", fontSize: "12px", color: "#666" }}>
              Page {page} of {totalPages}
            </span>
          </div>
        </>
      )}

      {/* Image Modal */}
      {selectedImage && (
        <div
          onClick={() => setSelectedImage(null)}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div style={{
            maxWidth: "90vw",
            maxHeight: "90vh",
            backgroundColor: "white",
            borderRadius: "8px",
            overflow: "auto",
            position: "relative",
          }}>
            <button
              onClick={() => setSelectedImage(null)}
              style={{
                position: "absolute",
                top: "10px",
                right: "10px",
                padding: "8px 12px",
                backgroundColor: "#dc3545",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                zIndex: 1001,
              }}
            >
              ✕ Close
            </button>
            <img src={selectedImage} alt="Enlarged" style={{ width: "100%", display: "block" }} />
          </div>
        </div>
      )}
    </div>
  );
}

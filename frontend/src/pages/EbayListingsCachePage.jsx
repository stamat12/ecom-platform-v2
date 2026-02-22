import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { AdvancedFilters } from "../components/AdvancedFilters";

const API_BASE = "http://localhost:8000";

// Available columns configuration
const ALL_COLUMNS = [
  // Main columns
  { id: "image", label: "Image", type: "special", default: true },
  { id: "sku", label: "SKU", default: true },
  { id: "title", label: "Title", default: true },
  { id: "price", label: "Price €", default: true },
  { id: "listing_status", label: "Status", default: true },
  { id: "condition_name", label: "Condition", default: true },
  { id: "quantity_total", label: "Qty Total", default: false },
  { id: "quantity_available", label: "Qty Available", default: false },
  { id: "quantity_sold", label: "Qty Sold", default: false },
  { id: "start_time", label: "Start Time", default: false },
  { id: "end_time", label: "End Time", default: false },
  { id: "best_offer_enabled", label: "Best Offer", default: false },
  { id: "listing_type", label: "Listing Type", default: false },
  { id: "category_id", label: "Category ID", default: false },
  { id: "category_name", label: "Category", default: false },
  { id: "condition_id", label: "Condition ID", default: false },
  { id: "currency", label: "Currency", default: false },
  { id: "item_id", label: "Item ID", default: false },
  { id: "marketplace", label: "Marketplace", default: false },
  { id: "site", label: "Site", default: false },
  { id: "view_url", label: "Link", default: false },
  { id: "count_main_images", label: "Count Main Images", default: false },
  { id: "ebay_seo_product_type", label: "eBay SEO Product Type", default: false },
  { id: "ebay_seo_product_model", label: "eBay SEO Product Model", default: false },
  { id: "ebay_seo_keyword_1", label: "eBay SEO Keyword 1", default: false },
  { id: "ebay_seo_keyword_2", label: "eBay SEO Keyword 2", default: false },
  { id: "ebay_seo_keyword_3", label: "eBay SEO Keyword 3", default: false },

  // Profit analysis columns
  { id: "profit.selling_price_brutto", label: "Price Brutto €", profitCol: true, default: true },
  { id: "profit.selling_price_netto", label: "Price Netto €", profitCol: true, default: true },
  { id: "profit.total_cost_net", label: "Cost Net €", profitCol: true, default: true },
  { id: "profit.net_profit", label: "Net Profit €", profitCol: true, default: true },
  { id: "profit.net_profit_margin_percent", label: "Profit %", profitCol: true, default: true },
  { id: "profit.sales_commission", label: "Commission €", profitCol: true, default: false },
  { id: "profit.sales_commission_percentage", label: "Commission %", profitCol: true, default: false },
  { id: "profit.payment_fee", label: "Payment Fee €", profitCol: true, default: false },
  { id: "profit.shipping_costs_net", label: "Shipping €", profitCol: true, default: false },
];

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

const ColumnSelector = ({ visibleColumns, onColumnsChange, onClose }) => {
  const groups = {
    Main: ALL_COLUMNS.filter(c => !c.profitCol),
    "Profit Analysis": ALL_COLUMNS.filter(c => c.profitCol),
  };

  const handleToggle = (colId) => {
    if (visibleColumns.includes(colId)) {
      onColumnsChange(visibleColumns.filter(id => id !== colId));
    } else {
      onColumnsChange([...visibleColumns, colId]);
    }
  };

  const moveColumn = (colId, direction) => {
    const idx = visibleColumns.indexOf(colId);
    if (idx === -1) return;

    if (direction === "left" && idx > 0) {
      const newOrder = [...visibleColumns];
      [newOrder[idx - 1], newOrder[idx]] = [newOrder[idx], newOrder[idx - 1]];
      onColumnsChange(newOrder);
    } else if (direction === "right" && idx < visibleColumns.length - 1) {
      const newOrder = [...visibleColumns];
      [newOrder[idx], newOrder[idx + 1]] = [newOrder[idx + 1], newOrder[idx]];
      onColumnsChange(newOrder);
    }
  };

  const selectAll = () => {
    onColumnsChange(ALL_COLUMNS.map(c => c.id));
  };

  const deselectAll = () => {
    onColumnsChange([]);
  };

  const resetDefaults = () => {
    onColumnsChange(ALL_COLUMNS.filter(c => c.default).map(c => c.id));
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 999,
      }}
    >
      <div
        style={{
          backgroundColor: "white",
          borderRadius: "8px",
          padding: "20px",
          maxWidth: "700px",
          maxHeight: "80vh",
          overflow: "auto",
          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h2 style={{ margin: 0 }}>Select & Order Columns</h2>
          <button
            onClick={onClose}
            style={{
              padding: "6px 12px",
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            ✕ Close
          </button>
        </div>

        <div style={{ marginBottom: "15px" }}>
          <button onClick={selectAll} style={{ marginRight: "10px", padding: "6px 12px", cursor: "pointer" }}>
            Select All
          </button>
          <button onClick={deselectAll} style={{ marginRight: "10px", padding: "6px 12px", cursor: "pointer" }}>
            Deselect All
          </button>
          <button onClick={resetDefaults} style={{ padding: "6px 12px", cursor: "pointer" }}>
            Reset to Defaults
          </button>
        </div>

        <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#f0f8ff", borderRadius: "4px", fontSize: "12px", color: "#666" }}>
          💡 Use the arrow buttons to reorder columns. They appear only for selected columns.
        </div>

        {/* Selected Columns Order Preview */}
        {visibleColumns.length > 0 && (
          <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#f9f9f9", borderRadius: "4px", borderLeft: "4px solid #007bff" }}>
            <h4 style={{ margin: "0 0 10px 0", fontSize: "12px", fontWeight: "bold" }}>Column Order:</h4>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {visibleColumns.map((colId, idx) => {
                const col = ALL_COLUMNS.find(c => c.id === colId);
                return (
                  <div
                    key={colId}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      backgroundColor: "white",
                      padding: "6px 10px",
                      borderRadius: "4px",
                      border: "1px solid #ddd",
                      fontSize: "11px",
                    }}
                  >
                    <span>{col?.label}</span>
                    <div style={{ display: "flex", gap: "2px" }}>
                      <button
                        onClick={() => moveColumn(colId, "left")}
                        disabled={idx === 0}
                        style={{
                          padding: "2px 4px",
                          backgroundColor: idx === 0 ? "#e0e0e0" : "#007bff",
                          color: "#fff",
                          border: "none",
                          borderRadius: "2px",
                          cursor: idx === 0 ? "default" : "pointer",
                          fontSize: "10px",
                        }}
                      >
                        ←
                      </button>
                      <button
                        onClick={() => moveColumn(colId, "right")}
                        disabled={idx === visibleColumns.length - 1}
                        style={{
                          padding: "2px 4px",
                          backgroundColor: idx === visibleColumns.length - 1 ? "#e0e0e0" : "#007bff",
                          color: "#fff",
                          border: "none",
                          borderRadius: "2px",
                          cursor: idx === visibleColumns.length - 1 ? "default" : "pointer",
                          fontSize: "10px",
                        }}
                      >
                        →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {Object.entries(groups).map(([groupName, columns]) => (
          <div key={groupName} style={{ marginBottom: "20px" }}>
            <h3 style={{ margin: "10px 0", fontSize: "14px", fontWeight: "bold", color: "#333" }}>{groupName}</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px" }}>
              {columns.map(col => {
                const isSelected = visibleColumns.includes(col.id);
                const idx = visibleColumns.indexOf(col.id);
                
                return (
                  <div
                    key={col.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px",
                      borderRadius: "4px",
                      backgroundColor: isSelected ? "#e7f3ff" : "#f9f9f9",
                      border: isSelected ? "1px solid #007bff" : "1px solid #eee",
                    }}
                  >
                    <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        cursor: "pointer",
                        flex: 1,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggle(col.id)}
                        style={{ cursor: "pointer" }}
                      />
                      <span style={{ fontSize: "13px" }}>{col.label}</span>
                    </label>
                    
                    {isSelected && (
                      <div style={{ display: "flex", gap: "4px" }}>
                        <button
                          onClick={() => moveColumn(col.id, "left")}
                          disabled={idx === 0}
                          title="Move left"
                          style={{
                            padding: "4px 8px",
                            backgroundColor: idx === 0 ? "#e0e0e0" : "#28a745",
                            color: "white",
                            border: "none",
                            borderRadius: "3px",
                            cursor: idx === 0 ? "default" : "pointer",
                            fontSize: "12px",
                            fontWeight: "bold",
                          }}
                        >
                          ←
                        </button>
                        <button
                          onClick={() => moveColumn(col.id, "right")}
                          disabled={idx === visibleColumns.length - 1}
                          title="Move right"
                          style={{
                            padding: "4px 8px",
                            backgroundColor: idx === visibleColumns.length - 1 ? "#e0e0e0" : "#28a745",
                            color: "white",
                            border: "none",
                            borderRadius: "3px",
                            cursor: idx === visibleColumns.length - 1 ? "default" : "pointer",
                            fontSize: "12px",
                            fontWeight: "bold",
                          }}
                        >
                          →
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const formatCellValue = (value, columnId) => {
  if (value === null || value === undefined || value === "") return "—";
  
  if (columnId.startsWith("profit.") || columnId === "price") {
    const num = parseFloat(value);
    if (!isNaN(num)) return `€${num.toFixed(2)}`;
    return value;
  }
  
  if (columnId.includes("_percent") || columnId === "profit.net_profit_margin_percent") {
    const num = parseFloat(value);
    if (!isNaN(num)) return `${num.toFixed(1)}%`;
    return value;
  }
  
  if (columnId === "start_time" || columnId === "end_time") {
    // Format as YYYY-MM-DD for better sorting
    const date = new Date(value);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  if (columnId === "best_offer_enabled") {
    return value ? "Yes" : "No";
  }
  
  if (typeof value === "string" && value.length > 50) {
    return value.substring(0, 47) + "...";
  }
  
  return String(value);
};

const getCellStyle = (columnId, value) => {
  const baseStyle = { padding: "10px", fontSize: "12px" };
  
  if (columnId === "profit.net_profit") {
    return {
      ...baseStyle,
      fontWeight: "bold",
      color: value > 0 ? "#28a745" : "#dc3545",
    };
  }
  
  if (columnId === "profit.net_profit_margin_percent") {
    const num = parseFloat(value);
    return {
      ...baseStyle,
      fontWeight: "bold",
      color: num > 100 ? "#28a745" : num > 0 ? "#ffc107" : "#dc3545",
    };
  }
  
  if (columnId === "listing_status") {
    const isActive = String(value) === "Active";
    return {
      ...baseStyle,
      padding: "4px 8px",
      backgroundColor: isActive ? "#d4edda" : "#f8d7da",
      color: isActive ? "#155724" : "#721c24",
      borderRadius: "4px",
      fontSize: "11px",
      display: "inline-block",
    };
  }
  
  return baseStyle;
};

export default function EbayListingsCachePage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedImage, setSelectedImage] = useState(null);
  const [error, setError] = useState(null);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const navigate = useNavigate();
  const LIMIT = 200;

  // Column visibility - load from localStorage
  const [visibleColumns, setVisibleColumns] = useState(() => {
    const saved = localStorage.getItem("ebayListingsColumns");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return ALL_COLUMNS.filter(c => c.default).map(c => c.id);
      }
    }
    return ALL_COLUMNS.filter(c => c.default).map(c => c.id);
  });

  // Save visible columns to localStorage
  useEffect(() => {
    localStorage.setItem("ebayListingsColumns", JSON.stringify(visibleColumns));
  }, [visibleColumns]);

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

  // Per-column filters (stored in localStorage)
  const [columnFilters, setColumnFilters] = useState(() => {
    const saved = localStorage.getItem("ebayListingsColumnFilters");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return {};
      }
    }
    return {};
  });

  // Save column filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("ebayListingsColumnFilters", JSON.stringify(columnFilters));
  }, [columnFilters]);

  // Selected SKUs for bulk operations
  const [selectedSkus, setSelectedSkus] = useState(new Set());
  const [seoGenerating, setSeoGenerating] = useState(false);

  // Toggle SKU selection
  const toggleSkuSelection = (sku) => {
    setSelectedSkus(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sku)) {
        newSet.delete(sku);
      } else {
        newSet.add(sku);
      }
      return newSet;
    });
  };

  // Select/deselect all visible SKUs
  const toggleSelectAll = () => {
    if (selectedSkus.size === listings.length && listings.length > 0) {
      setSelectedSkus(new Set());
    } else {
      setSelectedSkus(new Set(listings.map(l => l.sku)));
    }
  };

  // Bulk generate SEO fields
  const bulkGenerateSeo = async () => {
    if (selectedSkus.size === 0) {
      alert("Please select at least one SKU");
      return;
    }

    setSeoGenerating(true);
    setError(null);
    
    try {
      const skusArray = Array.from(selectedSkus);
      
      // Call the batch SEO endpoint if it exists, otherwise call individual endpoints
      const results = await Promise.all(
        skusArray.map(sku =>
          fetch(`${API_BASE}/api/ebay/enrich-seo`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sku, force: false }),
          })
            .then(r => r.json())
            .then(data => ({ sku, ...data }))
            .catch(err => ({ sku, success: false, message: err.message }))
        )
      );

      const successful = results.filter(r => r.success).length;
      const failed = results.filter(r => !r.success).length;

      let message = `SEO generation complete: ${successful} successful`;
      if (failed > 0) {
        message += `, ${failed} failed`;
      }
      
      alert(message);

      // Refresh listings to show updated SEO fields
      fetchListings(page);
      setSelectedSkus(new Set());
    } catch (err) {
      setError(`Failed to generate SEO: ${err.message}`);
    } finally {
      setSeoGenerating(false);
    }
  };

  const fetchListings = async (pageNum = 1) => {
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
        column_filters: JSON.stringify(columnFilters),
      });

      const url = `${API_BASE}/api/ebay-cache/de-listings?${params}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      setListings(data.listings || []);
      setTotal(data.total || 0);
      setPage(pageNum);
    } catch (error) {
      setError(`Failed to load listings: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Test backend connectivity on mount
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
          fetchListings(1);
        }
      } catch (err) {
        setError(`Cannot reach backend at ${API_BASE}`);
      }
    };
    testConnection();
  }, []);

  // Fetch listings when page changes
  useEffect(() => {
    if (page > 0) {
      fetchListings(page);
    }
  }, [page]);

  // When filters change, reset to page 1
  useEffect(() => {
    setPage(1);
    fetchListings(1);
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
    setFilters(prev => ({ ...prev, [key]: value }));
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

  const getColumnLabel = (colId) => {
    return ALL_COLUMNS.find(c => c.id === colId)?.label || colId;
  };

  const getCellValue = (listing, columnId) => {
    if (columnId === "image") return listing.primary_image_url;
    if (columnId.startsWith("profit.")) {
      const profitKey = columnId.replace("profit.", "");
      return listing.profit_analysis?.[profitKey];
    }
    return listing[columnId];
  };

  return (
    <div style={{ padding: "20px", backgroundColor: "#f5f5f5", minHeight: "100vh" }}>
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h1 style={{ margin: 0 }}>eBay Listings Cache (DE)</h1>
          <button
            onClick={() => navigate("/prompts")}
            style={{
              padding: "10px 16px",
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
        </div>

        {error && (
          <div style={{
            backgroundColor: "#f8d7da",
            color: "#721c24",
            padding: "12px",
            borderRadius: "4px",
            marginBottom: "20px",
            border: "1px solid #f5c6cb",
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Filters */}
        <div style={{
          backgroundColor: "white",
          padding: "15px",
          borderRadius: "4px",
          marginBottom: "20px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "12px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        }}>
          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>SKU</label>
            <input
              type="text"
              placeholder="Search SKU..."
              value={filters.search_sku}
              onChange={(e) => handleFilterChange("search_sku", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Title</label>
            <input
              type="text"
              placeholder="Search title..."
              value={filters.search_title}
              onChange={(e) => handleFilterChange("search_title", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Min Price €</label>
            <input
              type="number"
              placeholder="0"
              value={filters.min_price}
              onChange={(e) => handleFilterChange("min_price", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Max Price €</label>
            <input
              type="number"
              placeholder="999999"
              value={filters.max_price}
              onChange={(e) => handleFilterChange("max_price", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Min Profit %</label>
            <input
              type="number"
              placeholder="-999999"
              value={filters.min_profit_margin}
              onChange={(e) => handleFilterChange("min_profit_margin", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Max Profit %</label>
            <input
              type="number"
              placeholder="999999"
              value={filters.max_profit_margin}
              onChange={(e) => handleFilterChange("max_profit_margin", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Status</label>
            <select
              value={filters.listing_status}
              onChange={(e) => handleFilterChange("listing_status", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            >
              <option value="">All</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Condition</label>
            <input
              type="text"
              placeholder="Filter condition..."
              value={filters.condition}
              onChange={(e) => handleFilterChange("condition", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Sort By</label>
            <select
              value={filters.sort_by}
              onChange={(e) => handleFilterChange("sort_by", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            >
              <option value="sku">SKU</option>
              <option value="price">Price</option>
              <option value="profit_margin">Profit %</option>
              <option value="date">Date</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "12px", fontWeight: "bold" }}>Order</label>
            <select
              value={filters.sort_order}
              onChange={(e) => handleFilterChange("sort_order", e.target.value)}
              style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box" }}
            >
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
          </div>
        </div>

        {/* Control Buttons */}
        <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
          <button
            onClick={resetFilters}
            style={{ padding: "8px 16px", backgroundColor: "#6c757d", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
          >
            Reset Filters
          </button>
          <button
            onClick={() => setShowAdvancedFilters(true)}
            style={{ 
              padding: "8px 16px", 
              backgroundColor: "#ff9800", 
              color: "white", 
              border: "none", 
              borderRadius: "4px", 
              cursor: "pointer",
              fontWeight: "bold"
            }}
          >
            🔍 Advanced Filters {Object.keys(columnFilters).length > 0 && `(${Object.keys(columnFilters).length})`}
          </button>
          <button
            onClick={bulkGenerateSeo}
            disabled={selectedSkus.size === 0 || seoGenerating}
            style={{ 
              padding: "8px 16px", 
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#9c27b0",
              color: "white", 
              border: "none", 
              borderRadius: "4px", 
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
          >
            {seoGenerating ? "⏳ Generating..." : "📝 SEO"} {selectedSkus.size > 0 && `(${selectedSkus.size})`}
          </button>
          <button
            onClick={() => setShowColumnSelector(true)}
            style={{ padding: "8px 16px", backgroundColor: "#0066cc", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
          >
            ⚙️ Columns ({visibleColumns.length})
          </button>
        </div>

        {/* Table */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#999" }}>⏳ Loading...</div>
        ) : (
          <>
            <div style={{ overflowX: "auto", marginBottom: "20px", backgroundColor: "white", borderRadius: "4px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ backgroundColor: "#f8f9fa", borderBottom: "2px solid #dee2e6" }}>
                    <th
                      style={{
                        padding: "12px",
                        textAlign: "center",
                        fontSize: "12px",
                        fontWeight: "bold",
                        whiteSpace: "nowrap",
                        width: "40px",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSkus.size === listings.length && listings.length > 0}
                        onChange={toggleSelectAll}
                        title="Select all SKUs on this page"
                        style={{ cursor: "pointer" }}
                      />
                    </th>
                    {visibleColumns.map(colId => (
                      <th
                        key={colId}
                        style={{
                          padding: "12px",
                          textAlign: colId === "image" ? "center" : "left",
                          fontSize: "12px",
                          fontWeight: "bold",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {getColumnLabel(colId)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {listings.map((listing, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid #eee",
                        backgroundColor: selectedSkus.has(listing.sku) ? "#e3f2fd" : (idx % 2 === 0 ? "#ffffff" : "#f9f9f9"),
                      }}
                    >
                      <td
                        style={{
                          padding: "10px",
                          textAlign: "center",
                          width: "40px",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedSkus.has(listing.sku)}
                          onChange={() => toggleSkuSelection(listing.sku)}
                          style={{ cursor: "pointer" }}
                        />
                      </td>
                      {visibleColumns.map(colId => {
                        const value = getCellValue(listing, colId);
                        
                        if (colId === "image") {
                          return (
                            <td key={colId} style={{ padding: "10px", textAlign: "center" }}>
                              <ImagePlaceholder
                                src={value}
                                alt={listing.title}
                                onClick={() => setSelectedImage(value)}
                              />
                            </td>
                          );
                        }
                        
                        if (colId === "title") {
                          return (
                            <td key={colId} style={{ padding: "10px", fontSize: "12px", maxWidth: "300px" }}>
                              <a
                                href={listing.view_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{ color: "#0066cc", textDecoration: "none" }}
                              >
                                {value}
                              </a>
                            </td>
                          );
                        }
                        
                        return (
                          <td key={colId} style={getCellStyle(colId, value)}>
                            {formatCellValue(value, colId)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {listings.length === 0 && !loading && (
              <div style={{ textAlign: "center", padding: "40px", color: "#999", backgroundColor: "white", borderRadius: "4px" }}>
                No listings found matching your filters.
              </div>
            )}

            {/* Pagination */}
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

              <div style={{ display: "flex", gap: "5px" }}>
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
                Page {page} of {totalPages} ({total} total)
              </span>
            </div>
          </>
        )}

        {/* Column Selector Modal */}
        {showColumnSelector && (
          <ColumnSelector
            visibleColumns={visibleColumns}
            onColumnsChange={setVisibleColumns}
            onClose={() => setShowColumnSelector(false)}
          />
        )}

        {/* Advanced Filters Modal */}
        {showAdvancedFilters && (
          <AdvancedFilters
            visibleColumns={visibleColumns}
            allColumnsConfig={ALL_COLUMNS}
            columnFilters={columnFilters}
            onFiltersChange={(newFilters) => {
              setColumnFilters(newFilters);
              setPage(1); // Reset to first page when filters change
              fetchListings(1);
            }}
            onClose={() => setShowAdvancedFilters(false)}
          />
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
    </div>
  );
}

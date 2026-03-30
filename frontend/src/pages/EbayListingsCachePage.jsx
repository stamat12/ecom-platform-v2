import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

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
  { id: "days_listed", label: "Days Listed", default: true },
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
  { id: "ebay_seo_title", label: "eBay SEO Title", default: false },
  { id: "title_matches_ebay_seo_title", label: "Title = eBay SEO Title", default: false },
  { id: "last_title_change_value", label: "Last Live Title", default: true },
  { id: "last_title_change_days_ago", label: "Title Changed", default: true },
  { id: "last_title_change_at", label: "Title Changed At", default: false },
  { id: "last_price_new", label: "Last Live Price €", default: true },
  { id: "last_price_change_days_ago", label: "Price Changed", default: true },
  { id: "last_price_change_at", label: "Price Changed At", default: false },
  { id: "last_price_old", label: "Prev Live Price €", default: false },
  { id: "last_auction_convert_days_ago", label: "Auction Age", default: true },
  { id: "last_auction_convert_at", label: "Auction Since", default: false },
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
  
  if (columnId.startsWith("profit.") || columnId === "price" || columnId === "last_price_old" || columnId === "last_price_new") {
    const num = parseFloat(value);
    if (!isNaN(num)) return `€${num.toFixed(2)}`;
    return value;
  }
  
  if (columnId.includes("_percent") || columnId === "profit.net_profit_margin_percent") {
    const num = parseFloat(value);
    if (!isNaN(num)) return `${num.toFixed(1)}%`;
    return value;
  }
  
  if (columnId === "days_listed" || columnId === "last_title_change_days_ago" || columnId === "last_price_change_days_ago" || columnId === "last_auction_convert_days_ago") {
    const n = parseInt(value, 10);
    if (isNaN(n)) return "—";
    return `${n}d`;
  }

  if (columnId === "last_price_change_at") {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    const daysAgo = Math.floor((Date.now() - date.getTime()) / 86400000);
    return `${daysAgo}d`;
  }

  if (columnId === "last_auction_convert_at") {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  if (columnId === "start_time" || columnId === "end_time" || columnId === "last_title_change_at") {
    // Format as YYYY-MM-DD for better sorting
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  if (columnId === "best_offer_enabled") {
    return value ? "Yes" : "No";
  }

  if (columnId === "title_matches_ebay_seo_title") {
    if (value === "Not generated") return "Not generated";
    if (value === "Yes" || value === "No") return value;
    return value ? "Yes" : "No";
  }

  if (columnId === "ebay_seo_title") {
    return String(value);
  }
  
  if (typeof value === "string" && value.length > 50) {
    return value.substring(0, 47) + "...";
  }
  
  return String(value);
};

const COMPACT_COLUMNS = new Set([
  "days_listed",
  "last_title_change_days_ago",
  "last_price_change_days_ago",
  "last_auction_convert_days_ago",
  "count_main_images",
  "title_matches_ebay_seo_title",
  "ebay_seo_product_type",
  "ebay_seo_product_model",
  "ebay_seo_keyword_1",
  "ebay_seo_keyword_2",
  "ebay_seo_keyword_3",
  "quantity_total",
  "quantity_sold",
]);

const getHeaderStyle = (columnId) => {
  const baseStyle = {
    padding: "12px",
    textAlign: columnId === "image" ? "center" : "left",
    fontSize: "12px",
    fontWeight: "bold",
    whiteSpace: "nowrap",
    minWidth: "120px",
    verticalAlign: "top",
  };

  if (COMPACT_COLUMNS.has(columnId)) {
    return {
      ...baseStyle,
      minWidth: "90px",
      width: "90px",
      whiteSpace: "normal",
      lineHeight: "1.25",
      wordBreak: "normal",
      overflowWrap: "break-word",
    };
  }

  return baseStyle;
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

  if (columnId === "title_matches_ebay_seo_title") {
    const color = value === "Not generated" ? "#6c757d" : value === "Yes" || value === true ? "#28a745" : "#dc3545";
    return {
      ...baseStyle,
      fontWeight: "bold",
      color,
      whiteSpace: "nowrap",
    };
  }

  if (columnId === "ebay_seo_title") {
    return {
      ...baseStyle,
      whiteSpace: "normal",
      wordBreak: "normal",
      overflowWrap: "break-word",
      minWidth: "220px",
      maxWidth: "300px",
      lineHeight: "1.35",
    };
  }

  if (columnId === "last_title_change_value") {
    return {
      ...baseStyle,
      whiteSpace: "normal",
      wordBreak: "normal",
      overflowWrap: "break-word",
      minWidth: "220px",
      maxWidth: "320px",
      lineHeight: "1.35",
    };
  }

  if (COMPACT_COLUMNS.has(columnId)) {
    return {
      ...baseStyle,
      minWidth: "90px",
      maxWidth: "90px",
      whiteSpace: "normal",
      wordBreak: "normal",
      overflowWrap: "break-word",
      lineHeight: "1.25",
    };
  }
  
  return baseStyle;
};

// ─── Price calculator helpers ──────────────────────────────────────────────────

/**
 * Given a target profit margin % and a listing's profit_analysis, compute the
 * required new eBay listing price (brutto, DE marketplace, no surcharge).
 */
const computePriceFromMargin = (
  targetMarginPct,
  profit,
  shippingNetOverride = null,
  shippingListingOverride = null,
) => {
  if (!profit) return null;
  const totalCostNet   = profit.total_cost_net        || 0;
  const commissionPct  = profit.sales_commission_percentage || 0;
  const paymentFee     = profit.payment_fee            || 0;
  const shippingNet = Number.isFinite(Number(shippingNetOverride))
    ? Number(shippingNetOverride)
    : (profit.shipping_costs_net || 0);
  const shippingList = Number.isFinite(Number(shippingListingOverride))
    ? Number(shippingListingOverride)
    : (profit.shipping_listing || 4.99);
  const vatRate        = 0.19;

  const targetNetProfit = (totalCostNet * targetMarginPct) / 100;
  const numerator = targetNetProfit + paymentFee + shippingNet + totalCostNet;
  const divisor   = 1 / (1 + vatRate) - commissionPct;
  if (divisor <= 0) return null;
  return Math.max((numerator / divisor) - shippingList, 0.99);
};

/**
 * Given a new eBay price and a listing's profit_analysis, compute the resulting
 * profit margin %.
 */
const computeMarginFromPrice = (
  price,
  profit,
  shippingNetOverride = null,
  shippingListingOverride = null,
) => {
  if (!profit) return null;
  const totalCostNet   = profit.total_cost_net        || 0;
  if (totalCostNet <= 0) return null;
  const commissionPct  = profit.sales_commission_percentage || 0;
  const paymentFee     = profit.payment_fee            || 0;
  const shippingNet = Number.isFinite(Number(shippingNetOverride))
    ? Number(shippingNetOverride)
    : (profit.shipping_costs_net || 0);
  const shippingList = Number.isFinite(Number(shippingListingOverride))
    ? Number(shippingListingOverride)
    : (profit.shipping_listing || 4.99);
  const vatRate        = 0.19;

  const custPayment     = parseFloat(price) + shippingList;
  const sellingNetto    = custPayment / (1 + vatRate);
  const commission      = custPayment * commissionPct;
  const netProfit       = sellingNetto - commission - paymentFee - shippingNet - totalCostNet;
  return (netProfit / totalCostNet) * 100;
};

// ─── PriceAdjuster modal ──────────────────────────────────────────────────────

const PriceAdjuster = ({ listings, selectedSkus, onClose, onDone }) => {
  // Build initial rows from selected SKUs that appear in the current page
  const initialRows = React.useMemo(() => {
    return Array.from(selectedSkus)
      .map(sku => listings.find(l => l.sku === sku))
      .filter(Boolean)
      .map(l => ({
        sku:        l.sku,
        op:         l.op,
        title:      l.title || l.ebay_seo_title || "",
        imageUrl:   l.primary_image_url || "",
        currentPrice: parseFloat(l.price) || 0,
        profit:     l.profit_analysis || null,
        newPrice:   (parseFloat(l.price) || 0).toFixed(2),
        newMargin:  l.profit_analysis
          ? (computeMarginFromPrice(parseFloat(l.price) || 0, l.profit_analysis) || 0).toFixed(1)
          : "",
        include: true,
      }));
  }, [listings, selectedSkus]);

  const [rows, setRows] = React.useState(initialRows);
  const [globalMargin, setGlobalMargin] = React.useState("");
  const [updating, setUpdating] = React.useState(false);
  const [results, setResults] = React.useState([]);

  const updateRow = (idx, field, rawValue) => {
    setRows(prev => {
      const next = [...prev];
      const row  = { ...next[idx] };
      if (field === "newPrice") {
        row.newPrice = rawValue;
        const n = parseFloat(rawValue);
        if (!isNaN(n) && n > 0 && row.profit) {
          const m = computeMarginFromPrice(n, row.profit);
          row.newMargin = m !== null ? m.toFixed(1) : "";
        }
      } else if (field === "newMargin") {
        row.newMargin = rawValue;
        const m = parseFloat(rawValue);
        if (!isNaN(m) && row.profit) {
          const p = computePriceFromMargin(m, row.profit);
          row.newPrice = p !== null ? p.toFixed(2) : row.newPrice;
        }
      } else if (field === "include") {
        row.include = rawValue;
      }
      next[idx] = row;
      return next;
    });
  };

  const applyGlobalMargin = () => {
    const m = parseFloat(globalMargin);
    if (isNaN(m)) return;
    setRows(prev => prev.map(row => {
      if (!row.profit) return row;
      const p = computePriceFromMargin(m, row.profit);
      return {
        ...row,
        newMargin: m.toFixed(1),
        newPrice:  p !== null ? p.toFixed(2) : row.newPrice,
      };
    }));
  };

  const handleUpdate = async () => {
    const toUpdate = rows.filter(r => r.include && parseFloat(r.newPrice) !== r.currentPrice && parseFloat(r.newPrice) > 0);
    if (toUpdate.length === 0) {
      alert("No price changes to apply (all prices are the same as current, or excluded).");
      return;
    }
    setUpdating(true);
    setResults([]);
    const out = [];
    for (const row of toUpdate) {
      try {
        const resp = await fetch(`${API_BASE}/api/ebay/revise-price`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sku: row.sku, new_price: parseFloat(row.newPrice) }),
        });
        const data = await resp.json().catch(() => ({}));
        if (resp.ok && data.success !== false) {
          out.push({ sku: row.sku, success: true, message: data.message || `€${row.newPrice}` });
        } else {
          out.push({ sku: row.sku, success: false, message: data.detail || data.message || `HTTP ${resp.status}` });
        }
      } catch (err) {
        out.push({ sku: row.sku, success: false, message: err.message });
      }
    }
    setUpdating(false);
    setResults(out);
    const succeeded = out.filter(r => r.success).length;
    if (succeeded > 0) onDone();
  };

  const fmt = v => (v === null || v === undefined || v === "" ? "—" : v);
  const fmtEur = v => { const n = parseFloat(v); return isNaN(n) ? "—" : `€${n.toFixed(2)}`; };
  const fmtPct = v => { const n = parseFloat(v); return isNaN(n) ? "—" : `${n.toFixed(1)}%`; };

  const toUpdate = rows.filter(r => r.include && parseFloat(r.newPrice) !== r.currentPrice && parseFloat(r.newPrice) > 0);

  return (
    <div style={{ position:"fixed", top:0, left:0, right:0, bottom:0, backgroundColor:"rgba(0,0,0,0.55)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:999 }}>
      <div style={{ backgroundColor:"white", borderRadius:"8px", padding:"24px", maxWidth:"1400px", width:"97vw", maxHeight:"90vh", overflowY:"auto", boxShadow:"0 6px 20px rgba(0,0,0,0.3)" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"16px" }}>
          <h2 style={{ margin:0, fontSize:"18px" }}>💰 Price Adjuster ({rows.length} listing{rows.length !== 1 ? "s" : ""})</h2>
          <button onClick={onClose} style={{ padding:"6px 12px", backgroundColor:"#dc3545", color:"white", border:"none", borderRadius:"4px", cursor:"pointer" }}>✕ Close</button>
        </div>

        {/* Global margin setter */}
        <div style={{ backgroundColor:"#f0f8ff", padding:"12px 16px", borderRadius:"6px", marginBottom:"16px", display:"flex", alignItems:"center", gap:"12px", flexWrap:"wrap" }}>
          <span style={{ fontSize:"13px", fontWeight:"bold" }}>Set target margin % for all:</span>
          <input
            type="number"
            step="1"
            placeholder="e.g. 50"
            value={globalMargin}
            onChange={e => setGlobalMargin(e.target.value)}
            onKeyDown={e => e.key === "Enter" && applyGlobalMargin()}
            style={{ width:"90px", padding:"6px 8px", border:"1px solid #ccc", borderRadius:"4px", fontSize:"13px" }}
          />
          <button onClick={applyGlobalMargin} style={{ padding:"6px 14px", backgroundColor:"#0066cc", color:"white", border:"none", borderRadius:"4px", cursor:"pointer", fontSize:"13px" }}>
            Apply to all
          </button>
          <span style={{ fontSize:"12px", color:"#666" }}>Computes the price each listing needs to hit that margin.</span>
        </div>

        {/* Rows table */}
        <div style={{ overflowX:"auto", marginBottom:"16px" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"12px" }}>
            <thead>
              <tr style={{ backgroundColor:"#f8f9fa", borderBottom:"2px solid #dee2e6" }}>
                <th style={{ padding:"8px", textAlign:"center" }}>✓</th>
                <th style={{ padding:"8px", textAlign:"center" }}>Image</th>
                <th style={{ padding:"8px", textAlign:"left", minWidth:"200px", maxWidth:"300px" }}>Title</th>
                <th style={{ padding:"8px", textAlign:"left" }}>SKU</th>
                <th style={{ padding:"8px", textAlign:"right" }}>OP €</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Current Price</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Cost Net</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Commission</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Payment Fee</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Shipping Net</th>
                <th style={{ padding:"8px", textAlign:"right", color:"#28a745" }}>Net Profit</th>
                <th style={{ padding:"8px", textAlign:"right", color:"#28a745" }}>Margin %</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>New Price €</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>New Margin %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                const p = row.profit || {};
                const priceChanged = parseFloat(row.newPrice) !== row.currentPrice;
                return (
                  <tr key={row.sku} style={{ borderBottom:"1px solid #eee", backgroundColor: priceChanged ? "#fffde7" : (idx % 2 === 0 ? "#fff" : "#f9f9f9") }}>
                    <td style={{ padding:"6px", textAlign:"center" }}>
                      <input type="checkbox" checked={row.include} onChange={e => updateRow(idx, "include", e.target.checked)} />
                    </td>
                    <td style={{ padding:"6px", textAlign:"center" }}>
                      {row.imageUrl ? (
                        <img src={row.imageUrl} alt={row.sku} style={{ width:"52px", height:"52px", objectFit:"cover", borderRadius:"4px", border:"1px solid #ddd" }} onError={e => { e.target.style.display="none"; }} />
                      ) : (
                        <div style={{ width:"52px", height:"52px", backgroundColor:"#e9ecef", borderRadius:"4px", display:"inline-flex", alignItems:"center", justifyContent:"center", fontSize:"18px" }}>🖼️</div>
                      )}
                    </td>
                    <td style={{ padding:"6px", fontSize:"11px", whiteSpace:"normal", wordBreak:"break-word", maxWidth:"300px", lineHeight:"1.35" }}>{row.title || "—"}</td>
                    <td style={{ padding:"6px", fontWeight:"bold" }}>{row.sku}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(row.op)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(row.currentPrice)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.total_cost_net)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.sales_commission)} <span style={{ color:"#888", fontSize:"10px" }}>({fmtPct((p.sales_commission_percentage || 0) * 100)})</span></td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.payment_fee)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.shipping_costs_net)}</td>
                    <td style={{ padding:"6px", textAlign:"right", fontWeight:"bold", color: p.net_profit > 0 ? "#28a745" : "#dc3545" }}>{fmtEur(p.net_profit)}</td>
                    <td style={{ padding:"6px", textAlign:"right", fontWeight:"bold", color: parseFloat(p.net_profit_margin_percent) > 0 ? "#28a745" : "#dc3545" }}>{fmtPct(p.net_profit_margin_percent)}</td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input
                        type="number"
                        step="0.01"
                        min="0.99"
                        value={row.newPrice}
                        onChange={e => updateRow(idx, "newPrice", e.target.value)}
                        style={{ width:"80px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px" }}
                      />
                    </td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input
                        type="number"
                        step="1"
                        value={row.newMargin}
                        onChange={e => updateRow(idx, "newMargin", e.target.value)}
                        style={{ width:"70px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px" }}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Update results */}
        {results.length > 0 && (
          <div style={{ marginBottom:"16px", padding:"12px", backgroundColor:"#f8f9fa", borderRadius:"6px", fontSize:"12px" }}>
            <strong>Results:</strong>
            {results.map(r => (
              <div key={r.sku} style={{ color: r.success ? "#28a745" : "#dc3545", marginTop:"4px" }}>
                {r.success ? "✓" : "✗"} {r.sku}: {r.message}
              </div>
            ))}
          </div>
        )}

        {/* Footer buttons */}
        <div style={{ display:"flex", justifyContent:"flex-end", gap:"10px" }}>
          <button onClick={onClose} style={{ padding:"8px 20px", backgroundColor:"#6c757d", color:"white", border:"none", borderRadius:"4px", cursor:"pointer" }}>Cancel</button>
          <button
            onClick={handleUpdate}
            disabled={updating || toUpdate.length === 0}
            style={{ padding:"8px 20px", backgroundColor: updating || toUpdate.length === 0 ? "#ccc" : "#d32f2f", color:"white", border:"none", borderRadius:"4px", cursor: updating || toUpdate.length === 0 ? "default" : "pointer", fontWeight:"bold" }}
          >
            {updating ? "⏳ Updating..." : `🚀 Update ${toUpdate.length} eBay Price${toUpdate.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
};

const AuctionAdjuster = ({ listings, selectedSkus, onClose, onDone }) => {
  const computeAuctionMetrics = (priceRaw, profit, shippingNetRaw, shippingListingRaw) => {
    if (!profit) return null;
    const price = parseFloat(priceRaw);
    if (isNaN(price) || price <= 0) return null;

    const totalCostNet = parseFloat(profit.total_cost_net || 0);
    const commissionPct = parseFloat(profit.sales_commission_percentage || 0);
    const paymentFee = parseFloat(profit.payment_fee || 0);
    const shippingListParsed = parseFloat(shippingListingRaw);
    const shippingList = !isNaN(shippingListParsed)
      ? shippingListParsed
      : parseFloat(profit.shipping_listing || 4.99);
    const shippingNetParsed = parseFloat(shippingNetRaw);
    const shippingNet = !isNaN(shippingNetParsed)
      ? shippingNetParsed
      : parseFloat(profit.shipping_costs_net || 0);
    const vatRate = 0.19;

    const customerPayment = price + shippingList;
    const sellingNetto = customerPayment / (1 + vatRate);
    const commission = customerPayment * commissionPct;
    const netProfit = sellingNetto - commission - paymentFee - shippingNet - totalCostNet;
    const marginPercent = totalCostNet > 0 ? (netProfit / totalCostNet) * 100 : null;

    return {
      commission,
      netProfit,
      marginPercent,
    };
  };

  const initialRows = React.useMemo(() => {
    return Array.from(selectedSkus)
      .map(sku => listings.find(l => l.sku === sku))
      .filter(Boolean)
      .map(l => {
        const profit = l.profit_analysis || null;
        const startPrice = parseFloat(l.price) || 0;
        const shippingNet = profit?.shipping_costs_net ?? 9.4;
        const margin = profit
          ? computeMarginFromPrice(startPrice, profit, shippingNet)
          : null;

        return {
          sku: l.sku,
          op: l.op,
          title: l.title || l.ebay_seo_title || "",
          imageUrl: l.primary_image_url || "",
          currentPrice: startPrice,
          listingType: l.listing_type || "",
          profit,
          shippingListing: Number(profit?.shipping_listing ?? 4.99).toFixed(2),
          shippingNet: Number(shippingNet).toFixed(2),
          startPrice: startPrice.toFixed(2),
          targetMargin: margin !== null ? margin.toFixed(1) : "",
          include: true,
        };
      });
  }, [listings, selectedSkus]);

  const [rows, setRows] = React.useState(initialRows);
  const [globalMargin, setGlobalMargin] = React.useState("");
  const [globalShippingNet, setGlobalShippingNet] = React.useState("9.40");
  const [globalShippingListing, setGlobalShippingListing] = React.useState("4.99");
  const [updating, setUpdating] = React.useState(false);
  const [results, setResults] = React.useState([]);

  const updateRow = (idx, field, rawValue) => {
    setRows(prev => {
      const next = [...prev];
      const row = { ...next[idx] };

      if (field === "startPrice") {
        row.startPrice = rawValue;
        const price = parseFloat(rawValue);
        const ship = parseFloat(row.shippingNet);
        const shipListing = parseFloat(row.shippingListing);
        if (!isNaN(price) && price > 0 && row.profit) {
          const margin = computeMarginFromPrice(price, row.profit, ship, shipListing);
          row.targetMargin = margin !== null ? margin.toFixed(1) : "";
        }
      } else if (field === "targetMargin") {
        row.targetMargin = rawValue;
        const margin = parseFloat(rawValue);
        const ship = parseFloat(row.shippingNet);
        const shipListing = parseFloat(row.shippingListing);
        if (!isNaN(margin) && row.profit) {
          const price = computePriceFromMargin(margin, row.profit, ship, shipListing);
          row.startPrice = price !== null ? price.toFixed(2) : row.startPrice;
        }
      } else if (field === "shippingListing") {
        row.shippingListing = rawValue;
        const ship = parseFloat(row.shippingNet);
        const shipListing = parseFloat(rawValue);
        const price = parseFloat(row.startPrice);
        if (!isNaN(shipListing) && row.profit && !isNaN(price) && price > 0) {
          const margin = computeMarginFromPrice(price, row.profit, ship, shipListing);
          row.targetMargin = margin !== null ? margin.toFixed(1) : row.targetMargin;
        }
      } else if (field === "shippingNet") {
        row.shippingNet = rawValue;
        const ship = parseFloat(rawValue);
        const shipListing = parseFloat(row.shippingListing);
        const price = parseFloat(row.startPrice);
        if (!isNaN(ship) && row.profit && !isNaN(price) && price > 0) {
          const margin = computeMarginFromPrice(price, row.profit, ship, shipListing);
          row.targetMargin = margin !== null ? margin.toFixed(1) : row.targetMargin;
        }
      } else if (field === "include") {
        row.include = rawValue;
      }

      next[idx] = row;
      return next;
    });
  };

  const applyGlobalMargin = () => {
    const margin = parseFloat(globalMargin);
    if (isNaN(margin)) return;
    setRows(prev => prev.map(row => {
      if (!row.profit) return row;
      const ship = parseFloat(row.shippingNet);
      const shipListing = parseFloat(row.shippingListing);
      const price = computePriceFromMargin(margin, row.profit, ship, shipListing);
      return {
        ...row,
        targetMargin: margin.toFixed(1),
        startPrice: price !== null ? price.toFixed(2) : row.startPrice,
      };
    }));
  };

  const applyGlobalShippingNet = () => {
    const ship = parseFloat(globalShippingNet);
    if (isNaN(ship) || ship < 0) return;
    setRows(prev => prev.map(row => {
      const price = parseFloat(row.startPrice);
      const shipListing = parseFloat(row.shippingListing);
      const margin = row.profit && !isNaN(price) && price > 0
        ? computeMarginFromPrice(price, row.profit, ship, shipListing)
        : null;
      return {
        ...row,
        shippingNet: ship.toFixed(2),
        targetMargin: margin !== null ? margin.toFixed(1) : row.targetMargin,
      };
    }));
  };

  const applyGlobalShippingListing = () => {
    const shipListing = parseFloat(globalShippingListing);
    if (isNaN(shipListing) || shipListing < 0) return;
    setRows(prev => prev.map(row => {
      const price = parseFloat(row.startPrice);
      const ship = parseFloat(row.shippingNet);
      const margin = row.profit && !isNaN(price) && price > 0
        ? computeMarginFromPrice(price, row.profit, ship, shipListing)
        : null;
      return {
        ...row,
        shippingListing: shipListing.toFixed(2),
        targetMargin: margin !== null ? margin.toFixed(1) : row.targetMargin,
      };
    }));
  };

  const handleConvert = async () => {
    const toConvert = rows.filter(r => r.include && parseFloat(r.startPrice) > 0);
    if (toConvert.length === 0) {
      alert("No valid rows selected for auction conversion.");
      return;
    }

    const confirmed = window.confirm(
      `This will end and relist ${toConvert.length} listing(s) as 7-day auction. Continue?`
    );
    if (!confirmed) return;

    setUpdating(true);
    setResults([]);
    const out = [];

    for (const row of toConvert) {
      try {
        const resp = await fetch(`${API_BASE}/api/ebay/convert-to-auction`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sku: row.sku,
            start_price: parseFloat(row.startPrice),
            duration_days: 7,
          }),
        });

        const data = await resp.json().catch(() => ({}));
        if (resp.ok && data.success !== false) {
          out.push({ sku: row.sku, success: true, message: data.message || "Converted" });
        } else {
          out.push({ sku: row.sku, success: false, message: data.detail || data.message || `HTTP ${resp.status}` });
        }
      } catch (err) {
        out.push({ sku: row.sku, success: false, message: err.message || "Unknown network error" });
      }
    }

    setUpdating(false);
    setResults(out);
    const succeeded = out.filter(r => r.success).length;
    if (succeeded > 0) onDone();
  };

  const fmtEur = v => {
    const n = parseFloat(v);
    return isNaN(n) ? "-" : `EUR${n.toFixed(2)}`;
  };
  const fmtPct = v => {
    const n = parseFloat(v);
    return isNaN(n) ? "-" : `${n.toFixed(1)}%`;
  };

  return (
    <div style={{ position:"fixed", top:0, left:0, right:0, bottom:0, backgroundColor:"rgba(0,0,0,0.55)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:999 }}>
      <div style={{ backgroundColor:"white", borderRadius:"8px", padding:"24px", maxWidth:"1450px", width:"97vw", maxHeight:"90vh", overflowY:"auto", boxShadow:"0 6px 20px rgba(0,0,0,0.3)" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"16px" }}>
          <h2 style={{ margin:0, fontSize:"18px" }}>Auction 7 Days ({rows.length} listing{rows.length !== 1 ? "s" : ""})</h2>
          <button onClick={onClose} style={{ padding:"6px 12px", backgroundColor:"#dc3545", color:"white", border:"none", borderRadius:"4px", cursor:"pointer" }}>Close</button>
        </div>

        <div style={{ backgroundColor:"#eef6ff", padding:"12px 16px", borderRadius:"6px", marginBottom:"16px", display:"flex", alignItems:"center", gap:"12px", flexWrap:"wrap" }}>
          <span style={{ fontSize:"13px", fontWeight:"bold" }}>Target margin % for all:</span>
          <input type="number" step="1" value={globalMargin} onChange={e => setGlobalMargin(e.target.value)} style={{ width:"90px", padding:"6px 8px", border:"1px solid #ccc", borderRadius:"4px", fontSize:"13px" }} />
          <button onClick={applyGlobalMargin} style={{ padding:"6px 14px", backgroundColor:"#0066cc", color:"white", border:"none", borderRadius:"4px", cursor:"pointer", fontSize:"13px" }}>Apply Margin</button>

          <span style={{ fontSize:"13px", fontWeight:"bold", marginLeft:"16px" }}>Shipping charged to buyer EUR (all):</span>
          <input type="number" step="0.01" min="0" value={globalShippingListing} onChange={e => setGlobalShippingListing(e.target.value)} style={{ width:"100px", padding:"6px 8px", border:"1px solid #ccc", borderRadius:"4px", fontSize:"13px" }} />
          <button onClick={applyGlobalShippingListing} style={{ padding:"6px 14px", backgroundColor:"#5d4037", color:"white", border:"none", borderRadius:"4px", cursor:"pointer", fontSize:"13px" }}>Apply Buyer Shipping</button>

          <span style={{ fontSize:"13px", fontWeight:"bold", marginLeft:"16px" }}>Your shipping cost net EUR (all):</span>
          <input type="number" step="0.01" min="0" value={globalShippingNet} onChange={e => setGlobalShippingNet(e.target.value)} style={{ width:"100px", padding:"6px 8px", border:"1px solid #ccc", borderRadius:"4px", fontSize:"13px" }} />
          <button onClick={applyGlobalShippingNet} style={{ padding:"6px 14px", backgroundColor:"#455a64", color:"white", border:"none", borderRadius:"4px", cursor:"pointer", fontSize:"13px" }}>Apply Cost Shipping</button>
          <span style={{ fontSize:"12px", color:"#666" }}>Buyer shipping and your shipping cost are both editable per row and both affect margin.</span>
        </div>

        <div style={{ overflowX:"auto", marginBottom:"16px" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"12px" }}>
            <thead>
              <tr style={{ backgroundColor:"#f8f9fa", borderBottom:"2px solid #dee2e6" }}>
                <th style={{ padding:"8px", textAlign:"center" }}>Include</th>
                <th style={{ padding:"8px", textAlign:"center" }}>Image</th>
                <th style={{ padding:"8px", textAlign:"left", minWidth:"220px" }}>Title</th>
                <th style={{ padding:"8px", textAlign:"left" }}>SKU</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Current Price</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Current Type</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Cost Net</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Commission</th>
                <th style={{ padding:"8px", textAlign:"right" }}>Payment Fee</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>Shipping Charged to Buyer EUR</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>Your Shipping Cost Net EUR</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>Start Price EUR</th>
                <th style={{ padding:"8px", textAlign:"right", backgroundColor:"#fff3cd" }}>Net Profit EUR</th>
                <th style={{ padding:"8px", textAlign:"center", backgroundColor:"#fff3cd" }}>Margin %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                const p = row.profit || {};
                const computed = computeAuctionMetrics(row.startPrice, p, row.shippingNet, row.shippingListing);
                return (
                  <tr key={row.sku} style={{ borderBottom:"1px solid #eee", backgroundColor: idx % 2 === 0 ? "#fff" : "#f9f9f9" }}>
                    <td style={{ padding:"6px", textAlign:"center" }}>
                      <input type="checkbox" checked={row.include} onChange={e => updateRow(idx, "include", e.target.checked)} />
                    </td>
                    <td style={{ padding:"6px", textAlign:"center" }}>
                      {row.imageUrl ? (
                        <img src={row.imageUrl} alt={row.sku} style={{ width:"52px", height:"52px", objectFit:"cover", borderRadius:"4px", border:"1px solid #ddd" }} onError={e => { e.target.style.display="none"; }} />
                      ) : (
                        <div style={{ width:"52px", height:"52px", backgroundColor:"#e9ecef", borderRadius:"4px", display:"inline-flex", alignItems:"center", justifyContent:"center", fontSize:"18px" }}>N/A</div>
                      )}
                    </td>
                    <td style={{ padding:"6px", fontSize:"11px", whiteSpace:"normal", wordBreak:"break-word", maxWidth:"300px", lineHeight:"1.35" }}>{row.title || "-"}</td>
                    <td style={{ padding:"6px", fontWeight:"bold" }}>{row.sku}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(row.currentPrice)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{row.listingType || "-"}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.total_cost_net)}</td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(computed?.commission)} <span style={{ color:"#888", fontSize:"10px" }}>({fmtPct((p.sales_commission_percentage || 0) * 100)})</span></td>
                    <td style={{ padding:"6px", textAlign:"right" }}>{fmtEur(p.payment_fee)}</td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input type="number" step="0.01" min="0" value={row.shippingListing} onChange={e => updateRow(idx, "shippingListing", e.target.value)} title="What buyer pays for shipping" style={{ width:"100px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px" }} />
                    </td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input type="number" step="0.01" min="0" value={row.shippingNet} onChange={e => updateRow(idx, "shippingNet", e.target.value)} title="Your net shipping cost" style={{ width:"90px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px" }} />
                    </td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input type="number" step="0.01" min="0.01" value={row.startPrice} onChange={e => updateRow(idx, "startPrice", e.target.value)} style={{ width:"90px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px" }} />
                    </td>
                    <td style={{ padding:"6px", textAlign:"right", backgroundColor:"#fffde7", fontWeight:"bold", color: (computed?.netProfit || 0) >= 0 ? "#28a745" : "#dc3545" }}>
                      {fmtEur(computed?.netProfit)}
                    </td>
                    <td style={{ padding:"6px", textAlign:"center", backgroundColor:"#fffde7" }}>
                      <input type="number" step="1" value={row.targetMargin} onChange={e => updateRow(idx, "targetMargin", e.target.value)} style={{ width:"80px", padding:"4px 6px", border:"1px solid #ccc", borderRadius:"4px", textAlign:"right", fontSize:"12px", color: (computed?.marginPercent || 0) >= 0 ? "#28a745" : "#dc3545", fontWeight:"bold" }} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {results.length > 0 && (
          <div style={{ marginBottom:"16px", padding:"12px", backgroundColor:"#f8f9fa", borderRadius:"6px", fontSize:"12px" }}>
            <strong>Results:</strong>
            {results.map(r => (
              <div key={r.sku} style={{ color: r.success ? "#28a745" : "#dc3545", marginTop:"4px" }}>
                {r.success ? "OK" : "ERR"} {r.sku}: {r.message}
              </div>
            ))}
          </div>
        )}

        <div style={{ display:"flex", justifyContent:"flex-end", gap:"10px" }}>
          <button onClick={onClose} style={{ padding:"8px 20px", backgroundColor:"#6c757d", color:"white", border:"none", borderRadius:"4px", cursor:"pointer" }}>Cancel</button>
          <button onClick={handleConvert} disabled={updating} style={{ padding:"8px 20px", backgroundColor: updating ? "#ccc" : "#ad1457", color:"white", border:"none", borderRadius:"4px", cursor: updating ? "default" : "pointer", fontWeight:"bold" }}>
            {updating ? "Converting..." : "Convert to Auction (7 Days)"}
          </button>
        </div>
      </div>
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
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
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
    sort_by: "sku",
    sort_order: "asc",
  });

  // SKU Batch-style checkbox filters (independent from visible columns)
  const [selectedStatusFilters, setSelectedStatusFilters] = useState(new Set());
  const [selectedConditionFilters, setSelectedConditionFilters] = useState(new Set());
  const [selectedCategoryFilters, setSelectedCategoryFilters] = useState(new Set());
  const [selectedTitleMatchFilters, setSelectedTitleMatchFilters] = useState(new Set());

  // Selected SKUs for bulk operations
  const [selectedSkus, setSelectedSkus] = useState(new Set());
  const [seoGenerating, setSeoGenerating] = useState(false);
  const [titleGenerating, setTitleGenerating] = useState(false);
  const [titleUpdatingEbay, setTitleUpdatingEbay] = useState(false);
  const [profitRecalculating, setProfitRecalculating] = useState(false);
  const [showPriceAdjuster, setShowPriceAdjuster] = useState(false);
  const [showAuctionAdjuster, setShowAuctionAdjuster] = useState(false);
  const [columnSort, setColumnSort] = useState({ columnId: null, direction: "asc" });
  const [columnWidths, setColumnWidths] = useState(() => {
    const saved = localStorage.getItem("ebayListingsColumnWidths");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch {
        return {};
      }
    }
    return {};
  });
  const resizeStateRef = useRef({
    active: false,
    columnId: null,
    startX: 0,
    startWidth: 0,
  });

  useEffect(() => {
    localStorage.setItem("ebayListingsColumnWidths", JSON.stringify(columnWidths));
  }, [columnWidths]);

  useEffect(() => {
    return () => {
      if (resizeStateRef.current.active) {
        document.body.style.cursor = "";
      }
    };
  }, []);

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

  // Select/deselect all visible SKUs on current page
  const toggleSelectAll = () => {
    const currentPageSkus = filteredSortedListings.map(l => l.sku);
    const allCurrentPageSelected = currentPageSkus.every(sku => selectedSkus.has(sku));
    
    const newSet = new Set(selectedSkus);
    
    if (allCurrentPageSelected) {
      // Deselect all from current page
      currentPageSkus.forEach(sku => newSet.delete(sku));
    } else {
      // Select all from current page
      currentPageSkus.forEach(sku => newSet.add(sku));
    }
    
    setSelectedSkus(newSet);
  };

  // Helper to check if all current page SKUs are selected
  const areAllCurrentPageSelected = () => {
    return filteredSortedListings.length > 0 && filteredSortedListings.every(l => selectedSkus.has(l.sku));
  };

  const expandSkuRange = (value) => {
    const input = String(value || "").trim();
    const match = input.match(/^([A-Za-z]*)(\d+)-([A-Za-z]*)(\d+)$/);
    if (!match) return [];

    const [, startPrefix, startNumRaw, endPrefix, endNumRaw] = match;
    if (startPrefix !== endPrefix) return [];

    const startNum = parseInt(startNumRaw, 10);
    const endNum = parseInt(endNumRaw, 10);
    if (!Number.isFinite(startNum) || !Number.isFinite(endNum)) return [];
    if (startNum >= endNum || endNum - startNum > 1000) return [];

    const width = startNumRaw.length;
    const expanded = [];
    for (let number = startNum; number <= endNum; number += 1) {
      expanded.push(`${startPrefix}${String(number).padStart(width, "0")}`);
    }
    return expanded;
  };

  const parseHybridSku = (rawSku) => {
    const normalized = String(rawSku || "").trim();
    if (!normalized) return [];

    const parsed = [];
    const commaParts = normalized.split(",").map(part => part.trim()).filter(Boolean);

    const processPart = (part) => {
      if (part.includes(" - ")) {
        part.split(" - ").map(token => token.trim()).filter(Boolean).forEach(token => parsed.push(token));
        return;
      }

      if (part.includes("-")) {
        const expanded = expandSkuRange(part);
        if (expanded.length > 0) {
          expanded.forEach(token => parsed.push(token));
          return;
        }
      }

      parsed.push(part);
    };

    if (commaParts.length > 0) {
      commaParts.forEach(processPart);
    } else {
      processPart(normalized);
    }

    return Array.from(new Set(parsed));
  };

  const sendSelectedToSkuBatch = () => {
    if (selectedSkus.size === 0) {
      alert("Please select at least one SKU");
      return;
    }

    const expandedSkus = [];
    Array.from(selectedSkus).forEach((listingSku) => {
      const parsed = parseHybridSku(listingSku);
      if (parsed.length > 0) {
        expandedSkus.push(...parsed);
      }
    });

    const uniqueSkus = Array.from(new Set(expandedSkus));
    if (uniqueSkus.length === 0) {
      alert("No valid SKUs found in selection");
      return;
    }

    navigate("/skus/batch", { state: { selectedSkus: uniqueSkus } });
  };

  const postSkuAction = async (sku, endpoint) => {
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, force: false }),
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        return {
          sku,
          success: false,
          message: payload?.detail || payload?.message || `HTTP ${response.status}`,
        };
      }

      return {
        sku,
        ...payload,
        success: payload?.success !== false,
      };
    } catch (err) {
      return { sku, success: false, message: err.message || "Unknown network error" };
    }
  };

  const formatFailures = (failedResults) => {
    if (!failedResults.length) return "";
    const maxRows = 12;
    const lines = [];
    
    for (const r of failedResults.slice(0, maxRows)) {
      // Handle skipped SKUs (ones without JSON files)
      if (r.skus_without_json && Array.isArray(r.skus_without_json) && r.skus_without_json.length > 0) {
        lines.push(`- ${r.sku}: Skipped ${r.skus_without_json.length} SKU(s) without JSON: ${r.skus_without_json.join(", ")}`);
      }
      
      // If this result has individual SKU statuses (hybrid SKU), show those
      if (r.skus_status && Array.isArray(r.skus_status)) {
        const failedSkus = r.skus_status.filter(s => !s.success);
        for (const sku of failedSkus) {
          lines.push(`  - ${sku.sku}: ${sku.error || "Failed"}`);
        }
      } else if (!r.success && !r.skus_without_json?.length) {
        // Regular failure (not skipped)
        lines.push(`- ${r.sku}: ${r.message || "Unknown error"}`);
      }
    }
    
    const more = failedResults.length > maxRows ? `\n...and ${failedResults.length - maxRows} more` : "";
    return lines.length > 0 ? `\n\nFailed/Skipped SKUs:\n${lines.join("\n")}${more}` : "";
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
      const results = await Promise.all(skusArray.map(sku => postSkuAction(sku, "/api/ebay/enrich-seo")));

      const successful = results.filter(r => r.success).length;
      const failedResults = results.filter(r => !r.success);
      const failed = failedResults.length;

      let message = `SEO generation complete: ${successful} successful`;
      if (failed > 0) {
        message += `, ${failed} failed`;
      }
      message += formatFailures(failedResults);
      
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

  // Bulk generate assembled eBay Title and save to eBay SEO
  const bulkGenerateTitle = async () => {
    if (selectedSkus.size === 0) {
      alert("Please select at least one SKU");
      return;
    }

    setTitleGenerating(true);
    setError(null);

    try {
      const skusArray = Array.from(selectedSkus);
      const results = await Promise.all(skusArray.map(sku => postSkuAction(sku, "/api/ebay/enrich-title")));

      const successful = results.filter(r => r.success).length;
      const failedResults = results.filter(r => !r.success);
      const failed = failedResults.length;

      let message = `Title generation complete: ${successful} successful`;
      if (failed > 0) {
        message += `, ${failed} failed`;
      }
      message += formatFailures(failedResults);

      alert(message);

      fetchListings(page);
      setSelectedSkus(new Set());
    } catch (err) {
      setError(`Failed to generate title: ${err.message}`);
    } finally {
      setTitleGenerating(false);
    }
  };

  // Bulk update live eBay listing titles for selected SKUs
  const bulkUpdateEbayTitles = async () => {
    if (selectedSkus.size === 0) {
      alert("Please select at least one SKU");
      return;
    }

    setTitleUpdatingEbay(true);
    setError(null);

    try {
      const skusArray = Array.from(selectedSkus);
      const results = await Promise.all(skusArray.map(sku => postSkuAction(sku, "/api/ebay/revise-title")));

      const successful = results.filter(r => r.success).length;
      const failedResults = results.filter(r => !r.success);
      const failed = failedResults.length;

      let message = `eBay title update complete: ${successful} successful`;
      if (failed > 0) {
        message += `, ${failed} failed`;
      }
      message += formatFailures(failedResults);

      alert(message);
      fetchListings(page);
      setSelectedSkus(new Set());
    } catch (err) {
      setError(`Failed to update eBay titles: ${err.message}`);
    } finally {
      setTitleUpdatingEbay(false);
    }
  };

  const recalculateProfitOnly = async () => {
    setProfitRecalculating(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/skus/ebay-listings/recompute-profit`, {
        method: "POST",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success === false) {
        throw new Error(payload.detail || payload.message || `HTTP ${response.status}`);
      }
      await fetchListings(page);
      alert(`Profit recalculated for ${payload.count || 0} listing(s).`);
    } catch (err) {
      setError(`Failed to recalculate profit: ${err.message}`);
    } finally {
      setProfitRecalculating(false);
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
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
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
      sort_by: "sku",
      sort_order: "asc",
    });
    setSelectedStatusFilters(new Set());
    setSelectedConditionFilters(new Set());
    setSelectedCategoryFilters(new Set());
    setSelectedTitleMatchFilters(new Set());
  };

  const getColumnLabel = (colId) => {
    return ALL_COLUMNS.find(c => c.id === colId)?.label || colId;
  };

  const getCellValue = (listing, columnId) => {
    if (columnId === "image") return listing.primary_image_url;

    if (columnId === "title_matches_ebay_seo_title") {
      if (listing.ebay_seo_title === null || listing.ebay_seo_title === undefined || String(listing.ebay_seo_title).trim() === "") {
        return "Not generated";
      }
      const normalize = (text) => String(text || "").trim().replace(/\s+/g, " ").toLowerCase();
      return normalize(listing.title) === normalize(listing.ebay_seo_title) ? "Yes" : "No";
    }

    if (columnId.startsWith("profit.")) {
      const profitKey = columnId.replace("profit.", "");
      return listing.profit_analysis?.[profitKey];
    }
    return listing[columnId];
  };

  const handleHeaderSort = (columnId) => {
    if (columnId === "image") return;
    setColumnSort((prev) => {
      if (prev.columnId !== columnId) return { columnId, direction: "asc" };
      return { columnId, direction: prev.direction === "asc" ? "desc" : "asc" };
    });
  };

  const sortedListings = React.useMemo(() => {
    if (!columnSort.columnId) return listings;
    const dir = columnSort.direction === "asc" ? 1 : -1;
    const sorted = [...listings].sort((a, b) => {
      const av = getCellValue(a, columnSort.columnId);
      const bv = getCellValue(b, columnSort.columnId);

      if (av === null || av === undefined || av === "") return 1 * dir;
      if (bv === null || bv === undefined || bv === "") return -1 * dir;

      const aNum = Number(av);
      const bNum = Number(bv);
      const bothNumbers = Number.isFinite(aNum) && Number.isFinite(bNum);
      if (bothNumbers) return (aNum - bNum) * dir;

      const aDate = new Date(av);
      const bDate = new Date(bv);
      if (!Number.isNaN(aDate.getTime()) && !Number.isNaN(bDate.getTime())) {
        return (aDate.getTime() - bDate.getTime()) * dir;
      }

      return String(av).localeCompare(String(bv), undefined, {
        numeric: true,
        sensitivity: "base",
      }) * dir;
    });
    return sorted;
  }, [listings, columnSort]);

  const getTitleMatchValue = (listing) => {
    if (listing.ebay_seo_title === null || listing.ebay_seo_title === undefined || String(listing.ebay_seo_title).trim() === "") {
      return "Not generated";
    }
    const normalize = (text) => String(text || "").trim().replace(/\s+/g, " ").toLowerCase();
    return normalize(listing.title) === normalize(listing.ebay_seo_title) ? "Yes" : "No";
  };

  const availableStatusValues = React.useMemo(() => {
    const values = new Set();
    listings.forEach((listing) => values.add(String(listing.listing_status || "Unknown")));
    return Array.from(values).sort();
  }, [listings]);

  const availableConditionValues = React.useMemo(() => {
    const values = new Set();
    listings.forEach((listing) => values.add(String(listing.condition_name || "Unknown")));
    return Array.from(values).sort();
  }, [listings]);

  const availableCategoryValues = React.useMemo(() => {
    const values = new Set();
    listings.forEach((listing) => values.add(String(listing.category_name || "Unknown")));
    return Array.from(values).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  }, [listings]);

  const activeFilterCount =
    selectedStatusFilters.size +
    selectedConditionFilters.size +
    selectedCategoryFilters.size +
    selectedTitleMatchFilters.size +
    (filters.search_sku ? 1 : 0) +
    (filters.search_title ? 1 : 0) +
    (filters.min_price ? 1 : 0) +
    (filters.max_price ? 1 : 0) +
    (filters.min_profit_margin ? 1 : 0) +
    (filters.max_profit_margin ? 1 : 0);

  const filteredSortedListings = React.useMemo(() => {
    return sortedListings.filter((listing) => {
      if (selectedStatusFilters.size > 0 && !selectedStatusFilters.has(String(listing.listing_status || "Unknown"))) {
        return false;
      }
      if (selectedConditionFilters.size > 0 && !selectedConditionFilters.has(String(listing.condition_name || "Unknown"))) {
        return false;
      }
      if (selectedCategoryFilters.size > 0 && !selectedCategoryFilters.has(String(listing.category_name || "Unknown"))) {
        return false;
      }
      if (selectedTitleMatchFilters.size > 0 && !selectedTitleMatchFilters.has(getTitleMatchValue(listing))) {
        return false;
      }
      return true;
    });
  }, [sortedListings, selectedStatusFilters, selectedConditionFilters, selectedCategoryFilters, selectedTitleMatchFilters]);

  const getAppliedColumnWidthStyle = (columnId) => {
    const width = Number(columnWidths[columnId]);
    if (!Number.isFinite(width) || width <= 0) return {};
    return {
      width: `${width}px`,
      minWidth: `${width}px`,
      maxWidth: `${width}px`,
    };
  };

  const onResizeMouseDown = (event, columnId) => {
    event.preventDefault();
    event.stopPropagation();

    const th = event.currentTarget.closest("th");
    if (!th) return;

    const startWidth = th.getBoundingClientRect().width;

    resizeStateRef.current = {
      active: true,
      columnId,
      startX: event.clientX,
      startWidth,
    };

    document.body.style.cursor = "col-resize";

    const onMouseMove = (moveEvent) => {
      const state = resizeStateRef.current;
      if (!state.active || !state.columnId) return;
      const deltaX = moveEvent.clientX - state.startX;
      const nextWidth = Math.max(70, Math.round(state.startWidth + deltaX));
      setColumnWidths(prev => ({ ...prev, [state.columnId]: nextWidth }));
    };

    const onMouseUp = () => {
      resizeStateRef.current = {
        active: false,
        columnId: null,
        startX: 0,
        startWidth: 0,
      };
      document.body.style.cursor = "";
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
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

        {/* Filter Panel */}
        <div style={{ background: "#f9f9f9", padding: 12, borderRadius: 8, marginBottom: 16, border: "2px solid #e0e0e0" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <button
              onClick={() => setShowFilters(!showFilters)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontWeight: "bold",
                color: "#2196F3",
                fontSize: 14,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: 0,
              }}
            >
              <span style={{ fontSize: 16, transform: showFilters ? "rotate(90deg)" : "rotate(0deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
              🔍 Filters {activeFilterCount > 0 && `(${activeFilterCount} active)`}
            </button>
            <div style={{ fontSize: 12, color: "#666" }}>
              Showing {filteredSortedListings.length} / {sortedListings.length} listing(s) on this page
            </div>
          </div>

          {showFilters && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Search & Range</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <input type="text" placeholder="SKU contains..." value={filters.search_sku} onChange={(e) => handleFilterChange("search_sku", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                  <input type="text" placeholder="Title contains..." value={filters.search_title} onChange={(e) => handleFilterChange("search_title", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                  <input type="number" placeholder="Min Price €" value={filters.min_price} onChange={(e) => handleFilterChange("min_price", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                  <input type="number" placeholder="Max Price €" value={filters.max_price} onChange={(e) => handleFilterChange("max_price", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                  <input type="number" placeholder="Min Profit %" value={filters.min_profit_margin} onChange={(e) => handleFilterChange("min_profit_margin", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                  <input type="number" placeholder="Max Profit %" value={filters.max_profit_margin} onChange={(e) => handleFilterChange("max_profit_margin", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }} />
                </div>
              </div>

              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Status</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
                  {availableStatusValues.map((status) => (
                    <label key={status} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                      <input type="checkbox" checked={selectedStatusFilters.has(status)} onChange={(e) => {
                        const next = new Set(selectedStatusFilters);
                        if (e.target.checked) next.add(status); else next.delete(status);
                        setSelectedStatusFilters(next);
                      }} />
                      <span>{status}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Condition</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
                  {availableConditionValues.map((condition) => (
                    <label key={condition} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                      <input type="checkbox" checked={selectedConditionFilters.has(condition)} onChange={(e) => {
                        const next = new Set(selectedConditionFilters);
                        if (e.target.checked) next.add(condition); else next.delete(condition);
                        setSelectedConditionFilters(next);
                      }} />
                      <span>{condition}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Category</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto" }}>
                  {availableCategoryValues.map((category) => (
                    <label key={category} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                      <input type="checkbox" checked={selectedCategoryFilters.has(category)} onChange={(e) => {
                        const next = new Set(selectedCategoryFilters);
                        if (e.target.checked) next.add(category); else next.delete(category);
                        setSelectedCategoryFilters(next);
                      }} />
                      <span>{category}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Title Match</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {["Yes", "No", "Not generated"].map((match) => (
                    <label key={match} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                      <input type="checkbox" checked={selectedTitleMatchFilters.has(match)} onChange={(e) => {
                        const next = new Set(selectedTitleMatchFilters);
                        if (e.target.checked) next.add(match); else next.delete(match);
                        setSelectedTitleMatchFilters(next);
                      }} />
                      <span>{match}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Sorting</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <select value={filters.sort_by} onChange={(e) => handleFilterChange("sort_by", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }}>
                    <option value="sku">SKU</option>
                    <option value="price">Price</option>
                    <option value="profit_margin">Profit %</option>
                    <option value="date">Date</option>
                  </select>
                  <select value={filters.sort_order} onChange={(e) => handleFilterChange("sort_order", e.target.value)} style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: "4px", boxSizing: "border-box", fontSize: 12 }}>
                    <option value="asc">Ascending</option>
                    <option value="desc">Descending</option>
                  </select>
                </div>
              </div>
            </div>
          )}
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
            onClick={recalculateProfitOnly}
            disabled={profitRecalculating}
            style={{
              padding: "8px 16px",
              backgroundColor: profitRecalculating ? "#ccc" : "#8e24aa",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: profitRecalculating ? "default" : "pointer",
              fontWeight: "bold"
            }}
            title="Recalculate profit_analysis for current eBay cache without refetching from eBay"
          >
            {profitRecalculating ? "⏳ Recalculating Profit..." : "🧮 Recalculate Profit"}
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
            onClick={bulkGenerateTitle}
            disabled={selectedSkus.size === 0 || titleGenerating}
            style={{
              padding: "8px 16px",
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#2e7d32",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
          >
            {titleGenerating ? "⏳ Generating..." : "🏷️ Title"} {selectedSkus.size > 0 && `(${selectedSkus.size})`}
          </button>
          <button
            onClick={bulkUpdateEbayTitles}
            disabled={selectedSkus.size === 0 || titleUpdatingEbay}
            style={{
              padding: "8px 16px",
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#d32f2f",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
            title="Update live eBay listing titles for selected SKUs"
          >
            {titleUpdatingEbay ? "⏳ Updating eBay..." : "🚀 Update eBay Title"} {selectedSkus.size > 0 && `(${selectedSkus.size})`}
          </button>
          <button
            onClick={() => {
              if (selectedSkus.size === 0) { alert("Please select at least one SKU"); return; }
              setShowPriceAdjuster(true);
            }}
            disabled={selectedSkus.size === 0}
            style={{
              padding: "8px 16px",
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#e65100",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
            title="Open Price Adjuster to view margins and update eBay prices"
          >
            💰 Price Adjuster {selectedSkus.size > 0 && `(${selectedSkus.size})`}
          </button>
          <button
            onClick={() => {
              if (selectedSkus.size === 0) { alert("Please select at least one SKU"); return; }
              setShowAuctionAdjuster(true);
            }}
            disabled={selectedSkus.size === 0}
            style={{
              padding: "8px 16px",
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#ad1457",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
            title="Convert selected fixed listings to 7-day auction with start-price planning"
          >
            🏁 Auction 7 Days {selectedSkus.size > 0 && `(${selectedSkus.size})`}
          </button>
          <button
            onClick={sendSelectedToSkuBatch}
            disabled={selectedSkus.size === 0}
            style={{
              padding: "8px 16px",
              backgroundColor: selectedSkus.size === 0 ? "#ccc" : "#0d6efd",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: selectedSkus.size === 0 ? "default" : "pointer",
              fontWeight: "bold"
            }}
            title="Send selected SKUs to SKU Batch page (hybrid SKUs are expanded)"
          >
            📦 Send to SKU Batch {selectedSkus.size > 0 && `(${selectedSkus.size})`}
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
              <table style={{ width: "max-content", minWidth: "100%", tableLayout: "auto", borderCollapse: "collapse" }}>
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
                        checked={areAllCurrentPageSelected()}
                        onChange={toggleSelectAll}
                        title="Select/deselect all SKUs on this page"
                        style={{ cursor: "pointer" }}
                      />
                    </th>
                    {visibleColumns.map(colId => (
                      <th
                        key={colId}
                        onClick={() => handleHeaderSort(colId)}
                        title={colId === "image" ? "Not sortable" : "Click to sort"}
                        style={{
                          ...getHeaderStyle(colId),
                          ...getAppliedColumnWidthStyle(colId),
                          cursor: colId === "image" ? "default" : "pointer",
                          userSelect: "none",
                          position: "relative",
                        }}
                      >
                        {getColumnLabel(colId)}
                        {columnSort.columnId === colId && (
                          <span style={{ marginLeft: "6px", color: "#0066cc" }}>
                            {columnSort.direction === "asc" ? "▲" : "▼"}
                          </span>
                        )}
                        <div
                          onMouseDown={(e) => onResizeMouseDown(e, colId)}
                          onClick={(e) => e.stopPropagation()}
                          title="Drag to resize"
                          style={{
                            position: "absolute",
                            top: 0,
                            right: 0,
                            width: "10px",
                            height: "100%",
                            cursor: "col-resize",
                            userSelect: "none",
                            touchAction: "none",
                          }}
                        />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredSortedListings.map((listing, idx) => (
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
                            <td key={colId} style={{ padding: "10px", textAlign: "center", ...getAppliedColumnWidthStyle(colId) }}>
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
                            <td key={colId} style={{ padding: "10px", fontSize: "12px", maxWidth: "300px", ...getAppliedColumnWidthStyle(colId) }}>
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
                          <td key={colId} style={{ ...getCellStyle(colId, value), ...getAppliedColumnWidthStyle(colId) }}>
                            {formatCellValue(value, colId)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredSortedListings.length === 0 && !loading && (
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

        {/* Price Adjuster Modal */}
        {showPriceAdjuster && (
          <PriceAdjuster
            listings={listings}
            selectedSkus={selectedSkus}
            onClose={() => setShowPriceAdjuster(false)}
            onDone={() => {
              setShowPriceAdjuster(false);
              fetchListings(page);
              setSelectedSkus(new Set());
            }}
          />
        )}

        {showAuctionAdjuster && (
          <AuctionAdjuster
            listings={listings}
            selectedSkus={selectedSkus}
            onClose={() => setShowAuctionAdjuster(false)}
            onDone={() => {
              setShowAuctionAdjuster(false);
              fetchListings(page);
              setSelectedSkus(new Set());
            }}
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

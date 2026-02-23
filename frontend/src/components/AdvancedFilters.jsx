import React, { useState } from "react";

/**
 * AdvancedFilters Component
 * Provides per-column filtering with smart UI based on column data types
 * Supports: text search, numeric ranges, date ranges, multiselect for enums
 */
export const AdvancedFilters = ({
  visibleColumns,
  allColumnsConfig,
  columnFilters,
  onFiltersChange,
  onClose,
}) => {
  const [expandedFilters, setExpandedFilters] = useState({});
  const [filterValues, setFilterValues] = useState(columnFilters);

  const getColumnConfig = (columnId) => {
    return allColumnsConfig.find(c => c.id === columnId) || {};
  };

  const determineColumnType = (columnId) => {
    // Numeric columns
    if (["price", "quantity_total", "quantity_available", "quantity_sold", 
          "profit.selling_price_brutto", "profit.selling_price_netto", 
          "profit.total_cost_net", "profit.net_profit", 
          "profit.net_profit_margin_percent", "profit.sales_commission",
          "profit.sales_commission_percentage", "profit.payment_fee",
          "profit.shipping_costs_net", "count_main_images"].includes(columnId)) {
      return "number";
    }
    // Date columns
    if (["start_time", "end_time"].includes(columnId)) {
      return "date";
    }
    // Boolean columns
    if (["best_offer_enabled"].includes(columnId)) {
      return "boolean";
    }
    // Text columns
    return "text";
  };

  const handleTextFilter = (columnId, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: { ...prev[columnId], text: value }
    }));
  };

  const handleTextPresenceFilter = (columnId, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: {
        ...prev[columnId],
        has_value: value === "" ? null : value === "true"
      }
    }));
  };

  const handleTextExactFilter = (columnId, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: {
        ...prev[columnId],
        exact: value === "" ? null : value
      }
    }));
  };

  const handleNumberRange = (columnId, field, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: { ...prev[columnId], [field]: value === "" ? null : parseFloat(value) }
    }));
  };

  const handleDateRange = (columnId, field, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: { ...prev[columnId], [field]: value }
    }));
  };

  const handleBooleanFilter = (columnId, value) => {
    setFilterValues(prev => ({
      ...prev,
      [columnId]: { ...prev[columnId], value: value === "" ? null : value === "true" }
    }));
  };

  const toggleFilter = (columnId) => {
    setExpandedFilters(prev => ({
      ...prev,
      [columnId]: !prev[columnId]
    }));
  };

  const clearColumnFilter = (columnId) => {
    const newValues = { ...filterValues };
    delete newValues[columnId];
    setFilterValues(newValues);
  };

  const applyFilters = () => {
    // Remove empty filters
    const cleanedFilters = {};
    Object.entries(filterValues).forEach(([columnId, value]) => {
      if (value && Object.values(value).some(v => v !== null && v !== "")) {
        cleanedFilters[columnId] = value;
      }
    });
    onFiltersChange(cleanedFilters);
  };

  const resetAllFilters = () => {
    setFilterValues({});
  };

  const renderFilterControl = (columnId) => {
    const type = determineColumnType(columnId);
    const filterState = filterValues[columnId] || {};
    const columnConfig = getColumnConfig(columnId);

    switch (type) {
      case "text":
        if (columnId === "title_matches_ebay_seo_title") {
          return (
            <div style={{ padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
              <select
                value={filterState.exact || ""}
                onChange={(e) => handleTextExactFilter(columnId, e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  fontSize: "13px"
                }}
              >
                <option value="">Any</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
                <option value="Not generated">Not generated</option>
              </select>
            </div>
          );
        }

        return (
          <div style={{ padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
            <select
              value={filterState.has_value === null || filterState.has_value === undefined ? "" : filterState.has_value ? "true" : "false"}
              onChange={(e) => handleTextPresenceFilter(columnId, e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                boxSizing: "border-box",
                fontSize: "13px",
                marginBottom: "8px"
              }}
            >
              <option value="">Any</option>
              <option value="true">Has value (not —)</option>
              <option value="false">Empty only (—)</option>
            </select>
            <input
              type="text"
              placeholder={`Search ${columnConfig.label}...`}
              value={filterState.text || ""}
              onChange={(e) => handleTextFilter(columnId, e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                boxSizing: "border-box",
                fontSize: "13px"
              }}
            />
          </div>
        );

      case "number":
        return (
          <div style={{ padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
            <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
              <input
                type="number"
                placeholder="Min"
                value={filterState.min !== null && filterState.min !== undefined ? filterState.min : ""}
                onChange={(e) => handleNumberRange(columnId, "min", e.target.value)}
                style={{
                  flex: 1,
                  padding: "8px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  fontSize: "13px"
                }}
              />
              <input
                type="number"
                placeholder="Max"
                value={filterState.max !== null && filterState.max !== undefined ? filterState.max : ""}
                onChange={(e) => handleNumberRange(columnId, "max", e.target.value)}
                style={{
                  flex: 1,
                  padding: "8px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  fontSize: "13px"
                }}
              />
            </div>
            {(filterState.min !== null || filterState.max !== null) && (
              <small style={{ color: "#666" }}>
                {filterState.min !== null && filterState.min !== undefined && `Min: ${filterState.min}`}
                {filterState.min !== null && filterState.max !== null ? " to " : ""}
                {filterState.max !== null && filterState.max !== undefined && `Max: ${filterState.max}`}
              </small>
            )}
          </div>
        );

      case "date":
        return (
          <div style={{ padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <input
                type="date"
                value={filterState.from || ""}
                onChange={(e) => handleDateRange(columnId, "from", e.target.value)}
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  fontSize: "13px"
                }}
              />
              <input
                type="date"
                value={filterState.to || ""}
                onChange={(e) => handleDateRange(columnId, "to", e.target.value)}
                style={{
                  padding: "8px",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  boxSizing: "border-box",
                  fontSize: "13px"
                }}
              />
            </div>
            {(filterState.from || filterState.to) && (
              <small style={{ color: "#666", marginTop: "4px", display: "block" }}>
                {filterState.from && `From: ${filterState.from}`}
                {filterState.from && filterState.to && " to "}
                {filterState.to && `To: ${filterState.to}`}
              </small>
            )}
          </div>
        );

      case "boolean":
        return (
          <div style={{ padding: "12px 0", borderBottom: "1px solid #e0e0e0" }}>
            <select
              value={filterState.value === null ? "" : filterState.value ? "true" : "false"}
              onChange={(e) => handleBooleanFilter(columnId, e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
                border: "1px solid #ddd",
                borderRadius: "4px",
                boxSizing: "border-box",
                fontSize: "13px"
              }}
            >
              <option value="">Any</option>
              <option value="true">True / Yes</option>
              <option value="false">False / No</option>
            </select>
          </div>
        );

      default:
        return null;
    }
  };

  const sortedVisibleColumns = visibleColumns.map(id => getColumnConfig(id)).filter(Boolean);

  return (
    <div style={{
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      backgroundColor: "white",
      padding: "20px",
      borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
      zIndex: 1000,
      width: "90%",
      maxWidth: "800px",
      maxHeight: "90vh",
      overflow: "hidden",
      display: "flex",
      flexDirection: "column"
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "16px",
        paddingBottom: "12px",
        borderBottom: "2px solid #f0f0f0"
      }}>
        <h2 style={{ margin: 0, fontSize: "18px", fontWeight: "bold" }}>
          Advanced Filters
        </h2>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            fontSize: "24px",
            cursor: "pointer",
            padding: 0,
            color: "#999"
          }}
        >
          ×
        </button>
      </div>

      {/* Filter Controls - Scrollable */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        marginBottom: "16px",
        height: "400px"
      }}>
        {sortedVisibleColumns.map(columnConfig => (
          <div key={columnConfig.id} style={{
            marginBottom: "8px",
            backgroundColor: filterValues[columnConfig.id] ? "#f8f9fa" : "white",
            borderLeft: filterValues[columnConfig.id] ? "3px solid #0066cc" : "3px solid #ddd",
            padding: "0 0 0 12px"
          }}>
            <div
              onClick={() => toggleFilter(columnConfig.id)}
              style={{
                padding: "10px",
                cursor: "pointer",
                fontWeight: filterValues[columnConfig.id] ? "bold" : "normal",
                fontSize: "13px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                backgroundColor: expandedFilters[columnConfig.id] ? "#f0f0f0" : "transparent"
              }}
            >
              <span>{columnConfig.label}</span>
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                {filterValues[columnConfig.id] && (
                  <span style={{
                    backgroundColor: "#0066cc",
                    color: "white",
                    borderRadius: "12px",
                    padding: "2px 8px",
                    fontSize: "11px",
                    fontWeight: "bold"
                  }}>
                    ✓
                  </span>
                )}
                <span style={{ color: "#999" }}>
                  {expandedFilters[columnConfig.id] ? "▼" : "▶"}
                </span>
              </div>
            </div>

            {expandedFilters[columnConfig.id] && (
              <div style={{ padding: "0 10px" }}>
                {renderFilterControl(columnConfig.id)}
                {filterValues[columnConfig.id] && (
                  <button
                    onClick={() => clearColumnFilter(columnConfig.id)}
                    style={{
                      padding: "4px 8px",
                      backgroundColor: "#f8d7da",
                      color: "#721c24",
                      border: "1px solid #f5c6cb",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontSize: "12px",
                      marginBottom: "8px"
                    }}
                  >
                    Clear Filter
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer Actions */}
      <div style={{
        display: "flex",
        gap: "10px",
        borderTop: "1px solid #f0f0f0",
        paddingTop: "12px"
      }}>
        <button
          onClick={resetAllFilters}
          style={{
            flex: 1,
            padding: "10px",
            backgroundColor: "#6c757d",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: "bold"
          }}
        >
          Reset All
        </button>
        <button
          onClick={() => {
            applyFilters();
            onClose();
          }}
          style={{
            flex: 2,
            padding: "10px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: "bold"
          }}
        >
          Apply Filters ({Object.keys(filterValues).filter(k => filterValues[k] && Object.values(filterValues[k]).some(v => v !== null && v !== "")).length})
        </button>
      </div>
    </div>
  );
};

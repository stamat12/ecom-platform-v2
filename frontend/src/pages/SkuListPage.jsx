import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function SkuListPage() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [selectedSkus, setSelectedSkus] = useState([]);
  const navigate = useNavigate();

  // Column and filter state
  const [allColumns, setAllColumns] = useState([]);
  const [defaultColumns, setDefaultColumns] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [columnFilters, setColumnFilters] = useState({}); // { columnName: filterValue or typed object }
  const [filterLoading, setFilterLoading] = useState(true);
  const [columnMeta, setColumnMeta] = useState({}); // { columnName: { type, operators, enum_values } }
  const [distinctValues, setDistinctValues] = useState({}); // { columnName: [values] }
  const multiSelectStringCols = ["Brand", "Color", "Category", "Condition", "Size"]; // multi-select typeahead
  const [chipInputs, setChipInputs] = useState({}); // temp text inputs per column
  const [suggestions, setSuggestions] = useState({}); // { columnName: [values] }
  const [openSuggest, setOpenSuggest] = useState({}); // { columnName: boolean }
  const [columnWidths, setColumnWidths] = useState({}); // { columnName: px }
  const [resizing, setResizing] = useState(null); // { col, startX, startWidth }
  const profileId = "default"; // could be derived from user context later

  // Load available columns, column meta, and persisted filters on mount
  useEffect(() => {
    const load = async () => {
      try {
        const [colRes, metaRes, filtRes] = await Promise.all([
          fetch("/api/skus/columns"),
          fetch("/api/skus/columns/meta"),
          fetch(`/api/skus/filters?profile_id=${encodeURIComponent(profileId)}`),
        ]);

        if (!colRes.ok) throw new Error("Failed to load columns");
        const colData = await colRes.json();
        setAllColumns(colData.columns || []);
        setDefaultColumns(colData.default_columns || []);
        if (metaRes.ok) {
          const metaData = await metaRes.json();
          const byName = {};
          (metaData.columns || []).forEach((m) => { byName[m.name] = m; });
          setColumnMeta(byName);
        }

        if (filtRes.ok) {
          const filtData = await filtRes.json();
          const validSelected = (filtData.selected_columns || []).filter((c) => (colData.columns || []).includes(c));
          setSelectedColumns(validSelected.length ? validSelected : (colData.default_columns || []));
          setColumnFilters(filtData.column_filters || {});
          setPageSize(Number(filtData.page_size || 50));
          setColumnWidths(filtData.column_widths || {});
        } else {
          // Fallback to defaults
          setSelectedColumns(colData.default_columns || []);
        }

        // Preload distinct values for multi-select string columns that are present
        const toLoad = multiSelectStringCols.filter((c) => (colData.columns || []).includes(c));
        await Promise.all(toLoad.map(async (c) => {
          try {
            const r = await fetch(`/api/skus/columns/distinct?column=${encodeURIComponent(c)}&limit=200`);
            if (r.ok) {
              const d = await r.json();
              setDistinctValues((prev) => ({ ...prev, [c]: d.values || [] }));
            }
          } catch {}
        }));
      } catch (e) {
        setErr(String(e));
      } finally {
        setFilterLoading(false);
      }
    };
    load();
  }, []);

  // Load SKUs when filters or pagination change
  useEffect(() => {
    if (filterLoading) return;

    const params = new URLSearchParams({
      page,
      page_size: pageSize,
    });

    if (selectedColumns.length > 0) {
      params.append("columns", selectedColumns.join(","));
    }

    // Build typed filters from columnFilters state
    const filters = [];
    for (const [column, value] of Object.entries(columnFilters)) {
      const meta = columnMeta[column] || { type: "string" };
      const type = meta.type;
      if (type === "number" && value && (value.min || value.max)) {
        const min = value.min;
        const max = value.max;
        if (min && max) {
          filters.push({ column, type, operator: "between", value: Number(min), value2: Number(max) });
        } else if (min) {
          filters.push({ column, type, operator: "gte", value: Number(min) });
        } else if (max) {
          filters.push({ column, type, operator: "lte", value: Number(max) });
        }
      } else if (type === "date" && value && (value.start || value.end)) {
        const start = value.start;
        const end = value.end;
        if (start && end) {
          filters.push({ column, type, operator: "between", value: start, value2: end });
        } else if (start) {
          filters.push({ column, type, operator: "gte", value: start });
        } else if (end) {
          filters.push({ column, type, operator: "lte", value: end });
        }
      } else if (type === "boolean" && typeof value === "string" && value) {
        const op = value === "true" ? "is_true" : value === "false" ? "is_false" : null;
        if (op) filters.push({ column, type, operator: op });
      } else if (type === "enum" && Array.isArray(value) && value.length > 0) {
        filters.push({ column, type, operator: "in", values: value });
      } else if (type === "enum" && typeof value === "string" && value.trim()) {
        filters.push({ column, type, operator: "equals", value: value.trim() });
      } else if (multiSelectStringCols.includes(column) && Array.isArray(value) && value.length > 0) {
        filters.push({ column, type: "string", operator: "in", values: value });
      } else if (typeof value === "string" && value.trim()) {
        filters.push({ column, type: "string", operator: "contains", value: value.trim() });
      }
    }

    if (filters.length > 0) {
      params.append("filters", JSON.stringify(filters));
    }

    fetch(`/api/skus?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load SKUs");
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data.items)) {
          setRows(data.items);
          setTotal(data.total);
        } else {
          setRows([]);
        }
      })
      .catch((e) => setErr(String(e)));
  }, [page, pageSize, selectedColumns, columnFilters, filterLoading]);

  const totalPages = Math.ceil(total / pageSize);

  const handleResizeStart = (col, event) => {
    const header = event.currentTarget.parentElement;
    const startWidth = header ? header.offsetWidth : 120;
    setResizing({ col, startX: event.clientX, startWidth });
    event.preventDefault();
  };

  const handleMouseMove = (event) => {
    if (!resizing) return;
    const delta = event.clientX - resizing.startX;
    const newWidth = Math.max(80, resizing.startWidth + delta);
    setColumnWidths((prev) => ({ ...prev, [resizing.col]: Math.round(newWidth) }));
  };

  const handleMouseUp = () => {
    if (resizing) setResizing(null);
  };

  useEffect(() => {
    if (!resizing) return;
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [resizing]);

  const handleColumnToggle = (col) => {
    if (selectedColumns.includes(col)) {
      setSelectedColumns(selectedColumns.filter((c) => c !== col));
    } else {
      setSelectedColumns([...selectedColumns, col]);
    }
    setPage(1);
  };

  const handleSelectAll = () => {
    if (selectedColumns.length === allColumns.length) {
      setSelectedColumns([]);
    } else {
      setSelectedColumns([...allColumns]);
    }
    setPage(1);
  };

  const handleResetColumns = () => {
    setSelectedColumns([...defaultColumns]);
    setPage(1);
  };

  const handleFilterChange = (column, value) => {
    setColumnFilters((prev) => ({
      ...prev,
      [column]: value,
    }));
    setPage(1);
  };

  const handleTokenAdd = (column) => {
    const text = (chipInputs[column] || "").trim();
    if (!text) return;
    const current = Array.isArray(columnFilters[column]) ? columnFilters[column] : [];
    if (!current.includes(text)) {
      handleFilterChange(column, [...current, text]);
    }
    setChipInputs((prev) => ({ ...prev, [column]: "" }));
    setOpenSuggest((prev) => ({ ...prev, [column]: false }));
  };

  const handleTokenRemove = (column, token) => {
    const current = Array.isArray(columnFilters[column]) ? columnFilters[column] : [];
    handleFilterChange(column, current.filter((t) => t !== token));
  };

  const handleTokenClear = (column) => {
    handleFilterChange(column, []);
  };

  // Debounced suggestions fetcher for multi-select string columns
  useEffect(() => {
    const controllers = [];
    const timers = [];
    multiSelectStringCols.forEach((col) => {
      const q = (chipInputs[col] || "").trim();
      // Only query when user typed something
      if (!q) {
        setSuggestions((prev) => ({ ...prev, [col]: [] }));
        return;
      }
      const controller = new AbortController();
      controllers.push(controller);
      const t = setTimeout(async () => {
        try {
          const r = await fetch(`/api/skus/columns/distinct?column=${encodeURIComponent(col)}&q=${encodeURIComponent(q)}&limit=20`, { signal: controller.signal });
          if (r.ok) {
            const d = await r.json();
            setSuggestions((prev) => ({ ...prev, [col]: d.values || [] }));
            setOpenSuggest((prev) => ({ ...prev, [col]: true }));
          }
        } catch (_) {}
      }, 200);
      timers.push(t);
    });
    return () => {
      controllers.forEach((c) => c.abort());
      timers.forEach((t) => clearTimeout(t));
    };
  }, [chipInputs]);

  const persistFilters = (opts = {}) => {
    const payload = {
      profile_id: profileId,
      selected_columns: selectedColumns,
      column_filters: columnFilters,
      page_size: pageSize,
      column_widths: columnWidths,
    };
    fetch("/api/skus/filters", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: opts.keepalive === true,
      signal: opts.signal,
    }).catch(() => {
      try {
        const key = `sku_filters:${profileId}`;
        window.localStorage.setItem(key, JSON.stringify(payload));
      } catch {}
    });
  };

  // Persist filters/columns/page size whenever they change (debounced)
  useEffect(() => {
    if (filterLoading) return;
    const controller = new AbortController();
    const id = setTimeout(() => {
      persistFilters({ signal: controller.signal });
    }, 250);
    return () => {
      controller.abort();
      clearTimeout(id);
    };
  }, [selectedColumns, columnFilters, pageSize, columnWidths, filterLoading]);

  // Flush state on unmount to avoid losing recent changes when navigating away quickly
  useEffect(() => {
    return () => {
      persistFilters({ keepalive: true });
    };
  }, []);

  const pageSkus = rows
    .map((row) => row["SKU"] ?? row["SKU (Old)"])
    .filter(Boolean);
  const pageAllSelected = pageSkus.length > 0 && pageSkus.every((sku) => selectedSkus.includes(sku));

  const toggleSku = (sku) => {
    if (!sku) return;
    setSelectedSkus((prev) =>
      prev.includes(sku) ? prev.filter((s) => s !== sku) : [...prev, sku]
    );
  };

  const toggleSelectPage = () => {
    const pageSkus = rows
      .map((row) => row["SKU"] ?? row["SKU (Old)"])
      .filter(Boolean);
    const allSelected = pageSkus.every((sku) => selectedSkus.includes(sku));
    if (allSelected) {
      setSelectedSkus((prev) => prev.filter((sku) => !pageSkus.includes(sku)));
    } else {
      setSelectedSkus((prev) => Array.from(new Set([...prev, ...pageSkus])));
    }
  };

  const goToSelected = () => {
    if (selectedSkus.length === 0) return;
    const first = selectedSkus[0];
    navigate(`/skus/${encodeURIComponent(first)}`, { state: { selectedSkus } });
  };

  if (err) {
    return <div style={{ color: "red" }}>Error: {err}</div>;
  }

  return (
    <div>
      <h3>SKUs (Total: {total})</h3>

      <div style={{ marginBottom: 12, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={goToSelected}
          disabled={selectedSkus.length === 0}
          style={{ padding: "6px 10px", cursor: selectedSkus.length === 0 ? "not-allowed" : "pointer" }}
        >
          View selected (single)
        </button>
        <button
          onClick={() => navigate("/skus/batch", { state: { selectedSkus } })}
          disabled={selectedSkus.length === 0}
          style={{ padding: "6px 10px", cursor: selectedSkus.length === 0 ? "not-allowed" : "pointer" }}
        >
          View selected (one page)
        </button>
        <span style={{ color: "#555" }}>Selected: {selectedSkus.length}</span>
      </div>

      {/* Column Selector Section */}
      <div style={{ background: "#f9f9f9", padding: 12, borderRadius: 8, marginBottom: 16 }}>
        <h4 style={{ margin: "0 0 12px 0" }}>
          Display Columns
          <button
            onClick={handleSelectAll}
            style={{
              marginLeft: 8,
              padding: "4px 8px",
              fontSize: "0.85em",
              cursor: "pointer",
            }}
          >
            {selectedColumns.length === allColumns.length ? "Deselect All" : "Select All"}
          </button>
          <button
            onClick={handleResetColumns}
            style={{
              marginLeft: 8,
              padding: "4px 8px",
              fontSize: "0.85em",
              cursor: "pointer",
            }}
          >
            Reset to Default
          </button>
        </h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 8 }}>
          {allColumns.map((col) => (
            <label
              key={col}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                cursor: "pointer",
                padding: "4px 8px",
                background: selectedColumns.includes(col) ? "#e3f2fd" : "#fff",
                borderRadius: 4,
                border: "1px solid " + (selectedColumns.includes(col) ? "#2196F3" : "#ddd"),
              }}
            >
              <input
                type="checkbox"
                checked={selectedColumns.includes(col)}
                onChange={() => handleColumnToggle(col)}
                style={{ cursor: "pointer" }}
              />
              <span style={{ fontSize: "0.9em" }}>{col}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Pagination Controls */}
      <div style={{ marginBottom: 12, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <label>
          Page size:
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            style={{ marginLeft: 6 }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </label>
      </div>

      {/* Data Table with Column-Level Filters */}
      <div style={{ overflowX: "auto" }}>
        <table border="1" cellPadding="6" style={{ borderCollapse: "collapse", width: "100%", minWidth: 800 }}>
          <thead>
            {/* Column Headers */}
            <tr style={{ background: "#f0f0f0" }}>
              <th style={{ minWidth: 50 }}>
                <input
                  type="checkbox"
                  checked={pageAllSelected}
                  onChange={toggleSelectPage}
                  aria-label="Select all on page"
                />
              </th>
              {selectedColumns.length > 0 ? (
                selectedColumns.map((col) => {
                  const widthPx = columnWidths[col];
                  return (
                    <th
                      key={col}
                      style={{ textAlign: "left", minWidth: 120, width: widthPx ? `${widthPx}px` : undefined, position: "relative" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <span>{col}</span>
                        <span
                          onMouseDown={(e) => handleResizeStart(col, e)}
                          style={{ cursor: "col-resize", padding: "0 4px", userSelect: "none" }}
                          aria-label={`Resize ${col}`}
                        >
                          ⋮
                        </span>
                      </div>
                    </th>
                  );
                })
              ) : (
                <th colSpan="1">Select columns to display</th>
              )}
            </tr>

            {/* Filter Row */}
            {selectedColumns.length > 0 && (
              <tr style={{ background: "#fafafa" }}>
                <th />
                {selectedColumns.map((col) => {
                  const meta = columnMeta[col] || { type: "string" };
                  const val = columnFilters[col] ?? (multiSelectStringCols.includes(col) ? [] : "");
                  if (meta.type === "number") {
                    const v = typeof val === "object" ? val : { min: "", max: "" };
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <input type="number" placeholder="Min" value={v.min || ""}
                            onChange={(e) => handleFilterChange(col, { ...v, min: e.target.value })}
                            style={{ width: "50%" }} />
                          <input type="number" placeholder="Max" value={v.max || ""}
                            onChange={(e) => handleFilterChange(col, { ...v, max: e.target.value })}
                            style={{ width: "50%" }} />
                        </div>
                      </th>
                    );
                  }
                  if (meta.type === "date") {
                    const v = typeof val === "object" ? val : { start: "", end: "" };
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <input type="date" value={v.start || ""}
                            onChange={(e) => handleFilterChange(col, { ...v, start: e.target.value })}
                            style={{ width: "50%" }} />
                          <input type="date" value={v.end || ""}
                            onChange={(e) => handleFilterChange(col, { ...v, end: e.target.value })}
                            style={{ width: "50%" }} />
                        </div>
                      </th>
                    );
                  }
                  if (meta.type === "boolean") {
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <select value={val || ""}
                          onChange={(e) => handleFilterChange(col, e.target.value)}
                          style={{ width: "100%" }}>
                          <option value="">Any</option>
                          <option value="true">True</option>
                          <option value="false">False</option>
                        </select>
                      </th>
                    );
                  }
                  // Typeahead chips for Brand/Color (force even if inferred enum)
                  if (multiSelectStringCols.includes(col)) {
                    const tokens = Array.isArray(val) ? val : [];
                    const inputVal = chipInputs[col] || "";
                    const opts = suggestions[col] || [];
                    const isOpen = !!openSuggest[col] && inputVal.length > 0 && opts.length > 0;
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4, position: "relative" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <input
                            type="text"
                            placeholder={`Search ${col}...`}
                            value={inputVal}
                            onChange={(e) => setChipInputs((prev) => ({ ...prev, [col]: e.target.value }))}
                            onFocus={() => setOpenSuggest((prev) => ({ ...prev, [col]: true }))}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.preventDefault();
                                handleTokenAdd(col);
                              }
                              if (e.key === "Escape") {
                                setOpenSuggest((prev) => ({ ...prev, [col]: false }));
                              }
                            }}
                            style={{ width: "100%", padding: "4px 6px" }}
                          />
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <button onClick={() => handleTokenAdd(col)}>Add</button>
                            <button onClick={() => handleTokenClear(col)} disabled={tokens.length === 0}>Clear</button>
                          </div>
                        </div>
                        {isOpen && (
                          <div style={{ position: "absolute", zIndex: 10, background: "#fff", border: "1px solid #ccc", borderRadius: 4, width: "100%", maxHeight: 160, overflowY: "auto" }}>
                            {opts.map((o) => (
                              <div key={o}
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => {
                                  // clicking should not blur input before we add
                                  const current = Array.isArray(columnFilters[col]) ? columnFilters[col] : [];
                                  if (!current.includes(o)) handleFilterChange(col, [...current, o]);
                                  setChipInputs((prev) => ({ ...prev, [col]: "" }));
                                  setOpenSuggest((prev) => ({ ...prev, [col]: false }));
                                }}
                                style={{ padding: "6px 8px", cursor: "pointer" }}
                              >
                                {o}
                              </div>
                            ))}
                          </div>
                        )}
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                          {tokens.map((t) => (
                            <span key={t} style={{ background: "#e0e0e0", borderRadius: 12, padding: "2px 8px" }}>
                              {t}
                              <button onClick={() => handleTokenRemove(col, t)} style={{ marginLeft: 6 }}>x</button>
                            </span>
                          ))}
                        </div>
                      </th>
                    );
                  }
                  if (meta.type === "enum" && Array.isArray(meta.enum_values)) {
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <select multiple value={Array.isArray(val) ? val : []}
                          onChange={(e) => {
                            const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
                            handleFilterChange(col, selected);
                          }}
                          style={{ width: "100%", minHeight: 80 }}>
                          {meta.enum_values.map((ev) => (
                            <option key={ev} value={ev}>{ev}</option>
                          ))}
                        </select>
                      </th>
                    );
                  }
                  // default string input
                  return (
                    <th key={`filter-${col}`} style={{ padding: 4 }}>
                      <input
                        type="text"
                        placeholder={`Filter ${col}...`}
                        value={typeof val === "string" ? val : ""}
                        onChange={(e) => handleFilterChange(col, e.target.value)}
                        style={{
                          width: "100%",
                          padding: "4px 6px",
                          border: "1px solid #ccc",
                          borderRadius: 3,
                          boxSizing: "border-box",
                          fontSize: "0.9em",
                        }}
                      />
                    </th>
                  );
                })}
              </tr>
            )}
          </thead>

          <tbody>
            {selectedColumns.length === 0 ? (
              <tr>
                <td style={{ padding: 20, textAlign: "center", color: "#999" }}>
                  Please select at least one column to display
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(1, selectedColumns.length + 1)} style={{ padding: 20, textAlign: "center", color: "#999" }}>
                  No results found
                </td>
              </tr>
            ) : (
              rows.map((row, idx) => {
                const sku = row["SKU"] ?? row["SKU (Old)"];
                if (!sku) return null;
                return (
                  <tr key={idx}>
                    <td style={{ textAlign: "center" }}>
                      <input
                        type="checkbox"
                        checked={selectedSkus.includes(sku)}
                        onChange={() => toggleSku(sku)}
                        aria-label={`Select ${sku}`}
                      />
                    </td>
                    {selectedColumns.map((col) => {
                      const isSkuCol = col === "SKU" || col === "SKU (Old)";
                      const cellValue = row[col] ?? "-";
                      const widthPx = columnWidths[col];
                      
                      return (
                        <td
                          key={`${idx}-${col}`}
                          style={{
                            maxWidth: widthPx ? `${widthPx}px` : 200,
                            width: widthPx ? `${widthPx}px` : undefined,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {isSkuCol ? (
                            <Link
                              to={`/skus/${encodeURIComponent(sku)}`}
                              style={{ color: "#2196F3", textDecoration: "none" }}
                            >
                              {cellValue}
                            </Link>
                          ) : (
                            cellValue
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Bottom Pagination */}
      <div style={{ marginTop: 16, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button onClick={() => setPage(1)} disabled={page === 1}>
          First
        </button>
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
          Previous
        </button>
        <span>
          Page {page} of {totalPages}
        </span>
        <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}>
          Next
        </button>
        <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}>
          Last
        </button>
      </div>
    </div>
  );
}


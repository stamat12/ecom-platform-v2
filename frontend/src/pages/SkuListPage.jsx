import { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function SkuListPage() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [selectedSkus, setSelectedSkus] = useState([]);
  const [folderImagesComputing, setFolderImagesComputing] = useState(false);
  const [folderImagesStatus, setFolderImagesStatus] = useState({});
  const [folderImagesProgress, setFolderImagesProgress] = useState({ current: 0, total: 0 });
  const [ebayListingsComputing, setEbayListingsComputing] = useState(false);
  const [ebayListingsStatus, setEbayListingsStatus] = useState({});
  const [ebayListingsProgress, setEbayListingsProgress] = useState({ current: 0, total: 0 });
  const [inventoryExporting, setInventoryExporting] = useState(false);
  const [inventoryDbUpdating, setInventoryDbUpdating] = useState(false);
  const [excelSyncModalOpen, setExcelSyncModalOpen] = useState(false);
  const [excelSheets, setExcelSheets] = useState({});
  const [selectedSheets, setSelectedSheets] = useState({});
  const [excelSyncLoading, setExcelSyncLoading] = useState(false);
  const navigate = useNavigate();
  const hasRestoredState = useRef(false);

  // Column and filter state
  const [allColumns, setAllColumns] = useState([]);
  const [defaultColumns, setDefaultColumns] = useState([]);
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [columnFilters, setColumnFilters] = useState({}); // { columnName: filterValue or typed object }
  const [filterMode, setFilterMode] = useState({}); // { columnName: 'include' | 'exclude' }
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const [filterLoading, setFilterLoading] = useState(true);
  const [columnMeta, setColumnMeta] = useState({}); // { columnName: { type, operators, enum_values } }
  const [distinctValues, setDistinctValues] = useState({}); // { columnName: [values] }
  const multiSelectStringCols = ["Brand", "Color", "Category", "Condition", "Size", "Lager", "Vinted", "Willhaben", "Status"]; // multi-select typeahead
  const [chipInputs, setChipInputs] = useState({}); // temp text inputs per column
  const [suggestions, setSuggestions] = useState({}); // { columnName: [values] }
  const [openSuggest, setOpenSuggest] = useState({}); // { columnName: boolean }
  const [emptyFilters, setEmptyFilters] = useState({}); // { columnName: boolean } - true to show only empty values
  const [columnWidths, setColumnWidths] = useState({}); // { columnName: px }
  const [resizing, setResizing] = useState(null); // { col, startX, startWidth }
  const profileId = "default"; // could be derived from user context later

  // Load available columns, column meta, and persisted filters on mount
  useEffect(() => {
    // Prevent double execution in React strict mode
    if (hasRestoredState.current) return;
    
    const load = async () => {
      try {
        // Check if we have saved state from batch navigation
        const savedState = sessionStorage.getItem('skuListPageState');
        let restoredState = null;
        if (savedState) {
          try {
            restoredState = JSON.parse(savedState);
            console.log('Restored state:', restoredState);
            sessionStorage.removeItem('skuListPageState'); // Clear after restoring
          } catch (e) {
            console.error('Failed to parse saved state:', e);
          }
        }
        
        hasRestoredState.current = true;

        // Read localStorage state (filters, modes, columns, sizes)
        let localState = null;
        try {
          const savedLocal = localStorage.getItem('SkuListPageFilters');
          if (savedLocal) localState = JSON.parse(savedLocal);
        } catch (e) {
          console.error('Failed to parse saved filters:', e);
        }

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
          const localSelected = (localState?.selectedColumns || []).filter((c) => (colData.columns || []).includes(c));
          const localFilters = localState?.columnFilters || null;
          const localFilterMode = localState?.filterMode || null;
          const localPageSize = localState?.pageSize || null;
          const localColumnWidths = localState?.columnWidths || null;
          const localEmptyFilters = localState?.emptyFilters || null;
          
          // Use restored state if available, otherwise use persisted filters or server filters
          if (restoredState) {
            console.log('Applying restored state...');
            const cols = (restoredState.selectedColumns && restoredState.selectedColumns.length > 0) 
              ? restoredState.selectedColumns 
              : (validSelected.length ? validSelected : (colData.default_columns || []));
            console.log('Setting columns to:', cols);
            console.log('Setting filters to:', restoredState.columnFilters);
            setSelectedColumns(cols);
            setColumnFilters(restoredState.columnFilters || filtData.column_filters || {});
            setFilterMode(restoredState.filterMode || localFilterMode || {});
            setPageSize(restoredState.pageSize || Number(filtData.page_size || 50));
            setColumnWidths(restoredState.columnWidths || filtData.column_widths || {});
            setEmptyFilters(restoredState.emptyFilters || localEmptyFilters || {});
            setSelectedSkus(restoredState.selectedSkus || []);
            setPage(restoredState.page || 1);
          } else {
            const cols = localSelected.length ? localSelected : (validSelected.length ? validSelected : (colData.default_columns || []));
            setSelectedColumns(cols);
            setColumnFilters(localFilters || filtData.column_filters || {});
            setFilterMode(localFilterMode || filtData.filter_mode || {});
            setPageSize(localPageSize || Number(filtData.page_size || 50));
            setColumnWidths(localColumnWidths || filtData.column_widths || {});
            setEmptyFilters(localEmptyFilters || {});
          }
        } else {
          // Fallback to defaults or restored state
          if (restoredState) {
            setSelectedColumns(restoredState.selectedColumns || (colData.default_columns || []));
            setColumnFilters(restoredState.columnFilters || {});
            setFilterMode(restoredState.filterMode || {});
            setPageSize(restoredState.pageSize || 50);
            setColumnWidths(restoredState.columnWidths || {});
            setEmptyFilters(restoredState.emptyFilters || {});
            setSelectedSkus(restoredState.selectedSkus || []);
            setPage(restoredState.page || 1);
          } else {
            const localSelected = (localState?.selectedColumns || []).filter((c) => (colData.columns || []).includes(c));
            setSelectedColumns(localSelected.length ? localSelected : (colData.default_columns || []));
            setColumnFilters(localState?.columnFilters || {});
            setFilterMode(localState?.filterMode || {});
            setEmptyFilters(localState?.emptyFilters || {});
            if (localState?.pageSize) setPageSize(localState.pageSize);
            if (localState?.columnWidths) setColumnWidths(localState.columnWidths);
          }
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

  // Persist filters to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('SkuListPageFilters', JSON.stringify({
        columnFilters,
        filterMode,
        selectedColumns,
        pageSize,
        columnWidths,
        emptyFilters
      }));
    } catch (e) {
      console.error('Failed to save filters to localStorage:', e);
    }
  }, [columnFilters, filterMode, selectedColumns, pageSize, columnWidths, emptyFilters]);

  // Load SKUs when filters or pagination change
  useEffect(() => {
    if (filterLoading) return;

    console.log('Loading SKUs with:', {
      page,
      pageSize,
      selectedColumns,
      columnFilters
    });

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
      const mode = filterMode[column] || "include";
      const isExclude = mode === "exclude";
      
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
        const op = isExclude ? "not_in" : "in";
        filters.push({ column, type, operator: op, values: value });
      } else if (type === "enum" && typeof value === "string" && value.trim()) {
        filters.push({ column, type, operator: "equals", value: value.trim() });
      } else if (multiSelectStringCols.includes(column) && Array.isArray(value) && value.length > 0) {
        const op = isExclude ? "not_in" : "in";
        filters.push({ column, type: "string", operator: op, values: value });
      } else if (typeof value === "string" && value.trim()) {
        filters.push({ column, type: "string", operator: "contains", value: value.trim() });
      }
    }

    // Add empty filters for Vinted and Willhaben columns
    for (const [column, isEmpty] of Object.entries(emptyFilters)) {
      if (isEmpty) {
        filters.push({ column, type: "string", operator: "is_empty", value: null });
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
  }, [page, pageSize, selectedColumns, columnFilters, filterMode, filterLoading, emptyFilters]);

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

  const handleMoveColumnLeft = (col) => {
    const idx = selectedColumns.indexOf(col);
    if (idx <= 0) return; // Already at leftmost position or not selected
    const newCols = [...selectedColumns];
    [newCols[idx - 1], newCols[idx]] = [newCols[idx], newCols[idx - 1]];
    setSelectedColumns(newCols);
  };

  const handleMoveColumnRight = (col) => {
    const idx = selectedColumns.indexOf(col);
    if (idx < 0 || idx >= selectedColumns.length - 1) return; // Not selected or already at rightmost
    const newCols = [...selectedColumns];
    [newCols[idx], newCols[idx + 1]] = [newCols[idx + 1], newCols[idx]];
    setSelectedColumns(newCols);
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
      filter_mode: filterMode,
      page_size: pageSize,
      column_widths: columnWidths,
      emptyFilters: emptyFilters,
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
  }, [selectedColumns, columnFilters, filterMode, pageSize, columnWidths, emptyFilters, filterLoading]);

  // Flush state on unmount to avoid losing recent changes when navigating away quickly
  useEffect(() => {
    return () => {
      persistFilters({ keepalive: true });
    };
  }, []);

  // Load initial status timestamps on mount
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const folderRes = await fetch("/api/skus/folder-images/status");
        const folderData = await folderRes.json();
        setFolderImagesStatus(folderData);
      } catch (e) {
        console.error("Error loading folder images status:", e);
      }

      try {
        const ebayRes = await fetch("/api/skus/ebay-listings/status");
        const ebayData = await ebayRes.json();
        setEbayListingsStatus(ebayData);
      } catch (e) {
        console.error("Error loading eBay listings status:", e);
      }
    };
    
    loadStatus();
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

  const computeFolderImages = async () => {
    setFolderImagesComputing(true);
    try {
      const eventSource = new EventSource("/api/skus/folder-images/compute");
      
      eventSource.onmessage = (event) => {
        try {
          const progress = JSON.parse(event.data);
          setFolderImagesProgress(progress);
          if (progress.status === "completed") {
            setFolderImagesStatus(progress);
            eventSource.close();
            alert(`✅ Computed folder images for ${progress.processed} SKUs`);
          }
        } catch (e) {
          console.error("Error parsing progress:", e);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setFolderImagesComputing(false);
      };
    } catch (error) {
      console.error("Error computing folder images:", error);
      alert(`Error: ${error.message}`);
      setFolderImagesComputing(false);
    }
  };

  const computeEbayListings = async () => {
    setEbayListingsComputing(true);
    try {
      const eventSource = new EventSource("/api/skus/ebay-listings/compute");
      
      eventSource.onmessage = (event) => {
        try {
          const progress = JSON.parse(event.data);
          setEbayListingsProgress(progress);
          if (progress.status === "completed") {
            setEbayListingsStatus(progress);
            eventSource.close();
            alert(`✅ Synced eBay listings for ${progress.processed} SKUs`);
            setEbayListingsComputing(false);
          }
        } catch (e) {
          console.error("Error parsing progress:", e);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        setEbayListingsComputing(false);
      };
    } catch (error) {
      console.error("Error computing eBay listings:", error);
      alert(`Error: ${error.message}`);
      setEbayListingsComputing(false);
    }
  };

  const exportInventoryToJsons = async () => {
    setInventoryExporting(true);
    try {
      const res = await fetch("/api/inventory/export-to-jsons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(data.message || "JSONs updated from Excel");
      } else {
        alert(data.detail || data.message || "Export to JSONs failed");
      }
    } catch (error) {
      console.error("Error exporting to JSONs:", error);
      alert(`Error: ${error.message}`);
    } finally {
      setInventoryExporting(false);
    }
  };

  const updateDbFromJsons = async () => {
    setInventoryDbUpdating(true);
    try {
      const res = await fetch("/api/inventory/update-db-from-jsons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(data.message || "Database updated from JSONs");
      } else {
        alert(data.detail || data.message || "Database update failed");
      }
    } catch (error) {
      console.error("Error updating database from JSONs:", error);
      alert(`Error: ${error.message}`);
    } finally {
      setInventoryDbUpdating(false);
    }
  };

  const openExcelSyncModal = async () => {
    setExcelSyncLoading(true);
    try {
      const res = await fetch("/api/excel/sheets");
      if (res.ok) {
        const data = await res.json();
        setExcelSheets(data.sheets || {});
        // Initialize all sheets as selected with all columns
        const initial = {};
        Object.entries(data.sheets || {}).forEach(([sheet, columns]) => {
          initial[sheet] = {
            selected: true,
            columns: columns.reduce((acc, col) => ({ ...acc, [col]: true }), {})
          };
        });
        setSelectedSheets(initial);
        setExcelSyncModalOpen(true);
      } else {
        alert("Failed to load Excel sheets");
      }
    } catch (error) {
      console.error("Error loading Excel sheets:", error);
      alert(`Error: ${error.message}`);
    } finally {
      setExcelSyncLoading(false);
    }
  };

  const syncExcelToDb = async () => {
    setExcelSyncLoading(true);
    try {
      const sheetsToSync = [];
      Object.entries(selectedSheets).forEach(([sheet, info]) => {
        if (info.selected) {
          const selectedCols = Object.entries(info.columns)
            .filter(([_, selected]) => selected)
            .map(([col, _]) => col);
          if (selectedCols.length > 0) {
            sheetsToSync.push({ sheet_name: sheet, columns: selectedCols });
          }
        }
      });

      if (sheetsToSync.length === 0) {
        alert("Please select at least one sheet and columns");
        setExcelSyncLoading(false);
        return;
      }

      const res = await fetch("/api/excel/sync-to-db", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sheets: sheetsToSync })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert("✅ " + data.message);
        setExcelSyncModalOpen(false);
      } else {
        alert(data.message || "Sync failed");
      }
    } catch (error) {
      console.error("Error syncing Excel to DB:", error);
      alert(`Error: ${error.message}`);
    } finally {
      setExcelSyncLoading(false);
    }
  };

  const selectAllSheets = () => {
    const updated = {};
    Object.entries(selectedSheets).forEach(([sheet, info]) => {
      updated[sheet] = { ...info, selected: true };
    });
    setSelectedSheets(updated);
  };

  const deselectAllSheets = () => {
    const updated = {};
    Object.entries(selectedSheets).forEach(([sheet, info]) => {
      updated[sheet] = { ...info, selected: false };
    });
    setSelectedSheets(updated);
  };

  const selectAllColumns = (sheet) => {
    setSelectedSheets(prev => ({
      ...prev,
      [sheet]: {
        ...prev[sheet],
        columns: Object.keys(prev[sheet]?.columns || {}).reduce((acc, col) => ({ ...acc, [col]: true }), {})
      }
    }));
  };

  const deselectAllColumns = (sheet) => {
    setSelectedSheets(prev => ({
      ...prev,
      [sheet]: {
        ...prev[sheet],
        columns: Object.keys(prev[sheet]?.columns || {}).reduce((acc, col) => ({ ...acc, [col]: false }), {})
      }
    }));
  };

  if (err) {
    return <div style={{ color: "red" }}>Error: {err}</div>;
  }

  return (
    <div>
      <h3>SKUs (Total: {total})</h3>

      <div style={{ marginBottom: 12, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={computeFolderImages}
          disabled={folderImagesComputing}
          style={{ padding: "6px 10px", background: "#4CAF50", color: "white", border: "none", borderRadius: 4, cursor: folderImagesComputing ? "not-allowed" : "pointer" }}
        >
          {folderImagesComputing ? "Computing..." : "Compute Folder Images"}
        </button>
        {folderImagesStatus.last_update && (
          <span style={{ fontSize: "0.9em", color: "#666" }}>
            Last updated: {new Date(folderImagesStatus.last_update).toLocaleString()}
          </span>
        )}
        {folderImagesComputing && folderImagesProgress.total > 0 && (
          <div style={{ flex: 1, maxWidth: 300 }}>
            <div style={{ fontSize: "0.9em", marginBottom: 4 }}>
              Processing: {folderImagesProgress.current} / {folderImagesProgress.total}
            </div>
            <div style={{ width: "100%", height: 20, background: "#e0e0e0", borderRadius: 4, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  background: "#4CAF50",
                  width: `${(folderImagesProgress.current / folderImagesProgress.total) * 100}%`,
                  transition: "width 0.3s ease"
                }}
              />
            </div>
          </div>
        )}
        <button
          onClick={computeEbayListings}
          disabled={ebayListingsComputing}
          style={{ padding: "6px 10px", background: "#FF9800", color: "white", border: "none", borderRadius: 4, cursor: ebayListingsComputing ? "not-allowed" : "pointer" }}
        >
          {ebayListingsComputing ? "Fetching..." : "Fetch eBay Listings"}
        </button>
        {ebayListingsStatus.last_update && (
          <span style={{ fontSize: "0.9em", color: "#666" }}>
            Last eBay sync: {new Date(ebayListingsStatus.last_update).toLocaleString()}
          </span>
        )}
        {ebayListingsComputing && ebayListingsProgress.total > 0 && (
          <div style={{ flex: 1, maxWidth: 300 }}>
            <div style={{ fontSize: "0.9em", marginBottom: 4 }}>
              Processing: {ebayListingsProgress.current} / {ebayListingsProgress.total}
            </div>
            <div style={{ width: "100%", height: 20, background: "#e0e0e0", borderRadius: 4, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  background: "#FF9800",
                  width: `${(ebayListingsProgress.current / ebayListingsProgress.total) * 100}%`,
                  transition: "width 0.3s ease"
                }}
              />
            </div>
          </div>
        )}
        <button
          onClick={updateDbFromJsons}
          disabled={inventoryDbUpdating}
          style={{ padding: "6px 10px", cursor: inventoryDbUpdating ? "not-allowed" : "pointer", background: "#2e7d32", color: "white", border: "none", borderRadius: 4 }}
        >
          {inventoryDbUpdating ? "Updating DB..." : "🗄️ Update DB from JSON (New only)"}
        </button>
        <button
          onClick={openExcelSyncModal}
          disabled={excelSyncLoading}
          style={{ padding: "6px 10px", cursor: excelSyncLoading ? "not-allowed" : "pointer", background: "#1565c0", color: "white", border: "none", borderRadius: 4 }}
        >
          {excelSyncLoading ? "Loading..." : "📊 Sync Excel to DB (Selective)"}
        </button>
        <button
          onClick={exportInventoryToJsons}
          disabled={inventoryExporting}
          style={{ padding: "6px 10px", cursor: inventoryExporting ? "not-allowed" : "pointer", background: "#ff9800", color: "white", border: "none", borderRadius: 4 }}
        >
          {inventoryExporting ? "Updating JSONs..." : "📤 Update JSONs from Excel (Category, Status, Lager)"}
        </button>
      </div>

      {/* Excel Sync Modal */}
      {excelSyncModalOpen && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 16,
          zIndex: 999,
        }}>
          <div style={{
            background: "white",
            borderRadius: 10,
            maxWidth: 700,
            maxHeight: "80vh",
            overflow: "auto",
            padding: 24,
            boxShadow: "0 10px 40px rgba(0,0,0,0.2)",
          }}>
            <h3 style={{ marginTop: 0, marginBottom: 16 }}>Sync Excel to Database</h3>
            <p style={{ color: "#666", marginBottom: 16, fontSize: 13 }}>Select sheets and columns to sync from Excel to the database</p>

            <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
              <button
                onClick={selectAllSheets}
                style={{
                  padding: "6px 12px",
                  fontSize: 12,
                  background: "#4caf50",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontWeight: "bold"
                }}
              >
                Select All Sheets
              </button>
              <button
                onClick={deselectAllSheets}
                style={{
                  padding: "6px 12px",
                  fontSize: 12,
                  background: "#f44336",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontWeight: "bold"
                }}
              >
                Deselect All Sheets
              </button>
            </div>

            <div style={{ marginBottom: 16, maxHeight: 400, overflowY: "auto" }}>
              {Object.entries(excelSheets).map(([sheet, columns]) => (
                <div key={sheet} style={{
                  marginBottom: 16,
                  padding: 12,
                  border: "1px solid #e0e0e0",
                  borderRadius: 6,
                  background: "#f9f9f9"
                }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={selectedSheets[sheet]?.selected || false}
                      onChange={(e) => {
                        setSelectedSheets(prev => ({
                          ...prev,
                          [sheet]: {
                            ...prev[sheet],
                            selected: e.target.checked
                          }
                        }));
                      }}
                      style={{ width: 18, height: 18, cursor: "pointer" }}
                    />
                    <span style={{ fontWeight: 600, color: "#333" }}>{sheet}</span>
                  </label>

                  {selectedSheets[sheet]?.selected && (
                    <div>
                      <div style={{ marginBottom: 8, display: "flex", gap: 6 }}>
                        <button
                          onClick={() => selectAllColumns(sheet)}
                          style={{
                            padding: "4px 10px",
                            fontSize: 11,
                            background: "#2196f3",
                            color: "white",
                            border: "none",
                            borderRadius: 3,
                            cursor: "pointer",
                            fontWeight: "bold"
                          }}
                        >
                          All Cols
                        </button>
                        <button
                          onClick={() => deselectAllColumns(sheet)}
                          style={{
                            padding: "4px 10px",
                            fontSize: 11,
                            background: "#ff9800",
                            color: "white",
                            border: "none",
                            borderRadius: 3,
                            cursor: "pointer",
                            fontWeight: "bold"
                          }}
                        >
                          No Cols
                        </button>
                      </div>
                      <div style={{
                        marginLeft: 28,
                        paddingTop: 8,
                        borderTop: "1px solid #e0e0e0",
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                        gap: 8
                      }}>
                      {columns.map(col => (
                        <label key={col} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={selectedSheets[sheet]?.columns?.[col] || false}
                            onChange={(e) => {
                              setSelectedSheets(prev => ({
                                ...prev,
                                [sheet]: {
                                  ...prev[sheet],
                                  columns: {
                                    ...prev[sheet]?.columns,
                                    [col]: e.target.checked
                                  }
                                }
                              }));
                            }}
                            style={{ width: 16, height: 16, cursor: "pointer" }}
                          />
                          <span style={{ fontSize: 12, color: "#555" }}>{col}</span>
                        </label>
                      ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button
                onClick={() => setExcelSyncModalOpen(false)}
                disabled={excelSyncLoading}
                style={{
                  padding: "8px 16px",
                  fontSize: 12,
                  background: "#999",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: excelSyncLoading ? "not-allowed" : "pointer",
                  fontWeight: "bold"
                }}
              >
                Cancel
              </button>
              <button
                onClick={syncExcelToDb}
                disabled={excelSyncLoading}
                style={{
                  padding: "8px 16px",
                  fontSize: 12,
                  background: "#1565c0",
                  color: "white",
                  border: "none",
                  borderRadius: 4,
                  cursor: excelSyncLoading ? "not-allowed" : "pointer",
                  fontWeight: "bold"
                }}
              >
                {excelSyncLoading ? "Syncing..." : "✅ Sync Selected"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 12, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          onClick={goToSelected}
          disabled={selectedSkus.length === 0}
          style={{ padding: "6px 10px", cursor: selectedSkus.length === 0 ? "not-allowed" : "pointer" }}
        >
          View selected (single)
        </button>
        <button
          onClick={() => {
            // Save current state before navigating
            const stateToSave = {
              selectedSkus,
              page,
              columnFilters,
              selectedColumns,
              columnWidths,
              pageSize
            };
            console.log('Saving state:', stateToSave);
            sessionStorage.setItem('skuListPageState', JSON.stringify(stateToSave));
            navigate("/skus/batch", { state: { selectedSkus } });
          }}
          disabled={selectedSkus.length === 0}
          style={{ padding: "6px 10px", cursor: selectedSkus.length === 0 ? "not-allowed" : "pointer" }}
        >
          View selected (one page)
        </button>
        <button
          onClick={() => setSelectedSkus([])}
          disabled={selectedSkus.length === 0}
          style={{ padding: "6px 10px", cursor: selectedSkus.length === 0 ? "not-allowed" : "pointer", background: "#dc3545", color: "white", border: "none", borderRadius: 4 }}
        >
          Deselect All
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
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
          {allColumns.map((col) => {
            const isSelected = selectedColumns.includes(col);
            const idx = selectedColumns.indexOf(col);
            const canMoveLeft = isSelected && idx > 0;
            const canMoveRight = isSelected && idx < selectedColumns.length - 1;
            
            return (
              <div
                key={col}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "4px 8px",
                  background: isSelected ? "#e3f2fd" : "#fff",
                  borderRadius: 4,
                  border: "1px solid " + (isSelected ? "#2196F3" : "#ddd"),
                }}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handleColumnToggle(col)}
                  style={{ cursor: "pointer" }}
                />
                <span style={{ fontSize: "0.9em", flex: 1 }}>{col}</span>
                {isSelected && (
                  <div style={{ display: "flex", gap: 2 }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveColumnLeft(col);
                      }}
                      disabled={!canMoveLeft}
                      title="Move left"
                      style={{
                        padding: "2px 6px",
                        fontSize: "12px",
                        cursor: canMoveLeft ? "pointer" : "not-allowed",
                        background: canMoveLeft ? "#2196F3" : "#ddd",
                        color: "white",
                        border: "none",
                        borderRadius: 3,
                      }}
                    >
                      ←
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveColumnRight(col);
                      }}
                      disabled={!canMoveRight}
                      title="Move right"
                      style={{
                        padding: "2px 6px",
                        fontSize: "12px",
                        cursor: canMoveRight ? "pointer" : "not-allowed",
                        background: canMoveRight ? "#2196F3" : "#ddd",
                        color: "white",
                        border: "none",
                        borderRadius: 3,
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
                  const mode = filterMode[col] || "include";
                  const hasFilter = val && (Array.isArray(val) ? val.length > 0 : true) && typeof val !== "object" || (typeof val === "object" && (val.min || val.max || val.start || val.end));
                  
                  if (meta.type === "number") {
                    const v = typeof val === "object" ? val : { min: "", max: "" };
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                          <div style={{ flex: 1 }}>
                            <input type="number" placeholder="Min" value={v.min || ""}
                              onChange={(e) => handleFilterChange(col, { ...v, min: e.target.value })}
                              style={{ width: "100%", marginBottom: 2 }} />
                            <input type="number" placeholder="Max" value={v.max || ""}
                              onChange={(e) => handleFilterChange(col, { ...v, max: e.target.value })}
                              style={{ width: "100%" }} />
                          </div>
                          {hasFilter && (
                            <div style={{ display: "flex", gap: 2 }}>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "include" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: mode === "include" ? "#4CAF50" : "#ddd",
                                  color: mode === "include" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Include mode"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "exclude" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: mode === "exclude" ? "#f44336" : "#ddd",
                                  color: mode === "exclude" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Exclude mode"
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>
                      </th>
                    );
                  }
                  if (meta.type === "date") {
                    const v = typeof val === "object" ? val : { start: "", end: "" };
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                          <div style={{ flex: 1 }}>
                            <input type="date" value={v.start || ""}
                              onChange={(e) => handleFilterChange(col, { ...v, start: e.target.value })}
                              style={{ width: "100%", marginBottom: 2 }} />
                            <input type="date" value={v.end || ""}
                              onChange={(e) => handleFilterChange(col, { ...v, end: e.target.value })}
                              style={{ width: "100%" }} />
                          </div>
                          {hasFilter && (
                            <div style={{ display: "flex", gap: 2 }}>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "include" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: mode === "include" ? "#4CAF50" : "#ddd",
                                  color: mode === "include" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Include mode"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "exclude" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: mode === "exclude" ? "#f44336" : "#ddd",
                                  color: mode === "exclude" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Exclude mode"
                              >
                                ✕
                              </button>
                            </div>
                          )}
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
                        <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                          <div style={{ flex: 1 }}>
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
                                <label style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap", fontSize: "0.9em" }}>
                                  <input
                                    type="checkbox"
                                    checked={emptyFilters[col] || false}
                                    onChange={(e) => setEmptyFilters((prev) => ({ ...prev, [col]: e.target.checked }))}
                                  />
                                  Empty
                                </label>
                              </div>
                            </div>
                            {isOpen && (
                              <div style={{ position: "absolute", zIndex: 10, background: "#fff", border: "1px solid #ccc", borderRadius: 4, width: "calc(100% - 60px)", maxHeight: 160, overflowY: "auto" }}>
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
                          </div>
                          {tokens.length > 0 && (
                            <div style={{ display: "flex", gap: 2 }}>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "include" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: filterMode[col] === "include" ? "#4CAF50" : "#ddd",
                                  color: filterMode[col] === "include" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Include mode"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "exclude" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: filterMode[col] === "exclude" ? "#f44336" : "#ddd",
                                  color: filterMode[col] === "exclude" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Exclude mode"
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>
                      </th>
                    );
                  }
                  if (meta.type === "enum" && Array.isArray(meta.enum_values)) {
                    return (
                      <th key={`filter-${col}`} style={{ padding: 4 }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                          <select multiple value={Array.isArray(val) ? val : []}
                            onChange={(e) => {
                              const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
                              handleFilterChange(col, selected);
                            }}
                            style={{ flex: 1, minHeight: 80 }}>
                            {meta.enum_values.map((ev) => (
                              <option key={ev} value={ev}>{ev}</option>
                            ))}
                          </select>
                          {Array.isArray(val) && val.length > 0 && (
                            <div style={{ display: "flex", gap: 2 }}>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "include" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: filterMode[col] === "include" ? "#4CAF50" : "#ddd",
                                  color: filterMode[col] === "include" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Include mode"
                              >
                                ✓
                              </button>
                              <button
                                onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "exclude" }))}
                                style={{
                                  padding: "4px 8px",
                                  background: filterMode[col] === "exclude" ? "#f44336" : "#ddd",
                                  color: filterMode[col] === "exclude" ? "white" : "black",
                                  border: "none",
                                  borderRadius: 3,
                                  cursor: "pointer",
                                  fontSize: "0.8em",
                                  fontWeight: "bold"
                                }}
                                title="Exclude mode"
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>
                      </th>
                    );
                  }
                  // default string input
                  return (
                    <th key={`filter-${col}`} style={{ padding: 4 }}>
                      <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                        <input
                          type="text"
                          placeholder={`Filter ${col}...`}
                          value={typeof val === "string" ? val : ""}
                          onChange={(e) => handleFilterChange(col, e.target.value)}
                          style={{
                            flex: 1,
                            padding: "4px 6px",
                            border: "1px solid #ccc",
                            borderRadius: 3,
                            boxSizing: "border-box",
                            fontSize: "0.9em",
                          }}
                        />
                        {val && (
                          <div style={{ display: "flex", gap: 2 }}>
                            <button
                              onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "include" }))}
                              style={{
                                padding: "4px 8px",
                                background: filterMode[col] === "include" ? "#4CAF50" : "#ddd",
                                color: filterMode[col] === "include" ? "white" : "black",
                                border: "none",
                                borderRadius: 3,
                                cursor: "pointer",
                                fontSize: "0.8em",
                                fontWeight: "bold"
                              }}
                              title="Include mode"
                            >
                              ✓
                            </button>
                            <button
                              onClick={() => setFilterMode((prev) => ({ ...prev, [col]: "exclude" }))}
                              style={{
                                padding: "4px 8px",
                                background: filterMode[col] === "exclude" ? "#f44336" : "#ddd",
                                color: filterMode[col] === "exclude" ? "white" : "black",
                                border: "none",
                                borderRadius: 3,
                                cursor: "pointer",
                                fontSize: "0.8em",
                                fontWeight: "bold"
                              }}
                              title="Exclude mode"
                            >
                              ✕
                            </button>
                          </div>
                        )}
                      </div>
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


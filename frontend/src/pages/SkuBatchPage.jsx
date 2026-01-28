import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

function Modal({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        zIndex: 999,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "white",
          borderRadius: 10,
          maxWidth: "90vw",
          maxHeight: "90vh",
          overflow: "auto",
          padding: 12,
        }}
      >
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
          <button onClick={onClose} style={{ padding: "6px 10px" }}>Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function SkuBatchPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const selectedSkus = useMemo(() => {
    const incoming = Array.isArray(location.state?.selectedSkus)
      ? location.state.selectedSkus.filter(Boolean)
      : [];
    return Array.from(new Set(incoming));
  }, [location.state]);

  const [items, setItems] = useState([]);
  const [preview, setPreview] = useState(null); // { sku, image }
  const [rotating, setRotating] = useState({}); // { "sku/filename": true }
  const [jsonStatus, setJsonStatus] = useState({}); // { sku: true/false }
  const [generatingJson, setGeneratingJson] = useState({}); // { sku: true/false }
  const [selectedImages, setSelectedImages] = useState({}); // { sku: [filenames] }
  const [classifying, setClassifying] = useState({});
  const [batchClassifying, setBatchClassifying] = useState(false);

  // Product details state
  const [productDetails, setProductDetails] = useState({}); // { sku: ProductDetailResponse }
  const [detailsLoading, setDetailsLoading] = useState({}); // { sku: boolean }
  const [expandedDetails, setExpandedDetails] = useState({}); // { sku: boolean }
  const [editingDetails, setEditingDetails] = useState({}); // { sku: boolean }
  const [editedFieldsState, setEditedFieldsState] = useState({}); // { sku: { category: { field: value } } }

  // AI Enrichment state
  const [selectedSkusForEnrichment, setSelectedSkusForEnrichment] = useState(new Set()); // Set of SKUs to enrich
  const [enrichmentInProgress, setEnrichmentInProgress] = useState(false);
  const [enrichmentResults, setEnrichmentResults] = useState(null); // null | { total, succeeded, failed, results }

  // Calculate total selected images across all SKUs
  const totalSelectedImages = useMemo(() => {
    return Object.values(selectedImages).reduce((sum, filenames) => sum + filenames.length, 0);
  }, [selectedImages]);

  // Build flat array of {sku, filename} for batch classification
  const getAllSelectedImages = () => {
    const result = [];
    Object.entries(selectedImages).forEach(([sku, filenames]) => {
      filenames.forEach(filename => {
        result.push({ sku, filename });
      });
    });
    return result;
  };

  const handleGenerateJson = async (sku) => {
    setGeneratingJson((prev) => ({ ...prev, [sku]: true }));
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/json/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const result = await res.json();
      if (result.success) {
        setJsonStatus((prev) => ({ ...prev, [sku]: true }));
      } else {
        alert(result.message || "Failed to create JSON");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setGeneratingJson((prev) => ({ ...prev, [sku]: false }));
    }
  };

  const handleClassifyImages = async (sku, classificationType) => {
    const filenames = selectedImages[sku] || [];
    if (filenames.length === 0) {
      alert("No images selected for this SKU");
      return;
    }

    setClassifying((prev) => ({ ...prev, [sku]: true }));
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/images/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          filenames,
          classification_type: classificationType,
        }),
      });
      const result = await res.json();
      if (result.success) {
        alert(`✅ Classified ${result.processed_count} image(s) as ${classificationType}`);
        setSelectedImages((prev) => ({ ...prev, [sku]: [] }));
        // Refresh images for this SKU
        const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setItems((prev) =>
            prev.map((item) =>
              item.sku === sku ? { ...item, data: refreshData, error: null } : item
            )
          );
        }
      } else {
        alert(result.message || "Classification failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setClassifying((prev) => ({ ...prev, [sku]: false }));
    }
  };

  const handleBatchClassifyAll = async (classificationType) => {
    const allImages = getAllSelectedImages();
    if (allImages.length === 0) {
      alert("No images selected");
      return;
    }

    setBatchClassifying(true);
    try {
      const res = await fetch("/api/images/classify-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          images: allImages,
          classification_type: classificationType,
        }),
      });
      const result = await res.json();
      if (result.success) {
        alert(`✅ Classified ${result.processed_count} image(s) across ${new Set(allImages.map(i => i.sku)).size} SKU(s) as ${classificationType}`);
        setSelectedImages({});
        // Refresh all SKUs
        await fetchAllImages();
      } else {
        alert(result.message || "Batch classification failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setBatchClassifying(false);
    }
  };

  const handleBatchMarkAsMain = async () => {
    const allImages = getAllSelectedImages();
    if (allImages.length === 0) {
      alert("No images selected");
      return;
    }

    setBatchClassifying(true);
    try {
      const res = await fetch("/api/images/main-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          images: allImages,
          action: "mark",
        }),
      });
      const result = await res.json();
      if (result.success) {
        alert(`✅ Marked ${result.processed_count} image(s) across ${new Set(allImages.map(i => i.sku)).size} SKU(s) as Main`);
        setSelectedImages({});
        // Refresh all SKUs
        await fetchAllImages();
      } else {
        alert(result.message || "Batch main marking failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setBatchClassifying(false);
    }
  };

  const fetchAllImages = async () => {
    const promises = selectedSkus.map(async (sku) => {
      try {
        const resJson = await fetch(`/api/skus/${encodeURIComponent(sku)}/json/status`);
        const jsonData = await resJson.json();
        setJsonStatus((prev) => ({ ...prev, [sku]: jsonData.json_exists }));
        
        const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (!res.ok) {
          return { sku, data: null, error: "Failed to load images" };
        }
        const data = await res.json();
        return { sku, data, error: null };
      } catch (e) {
        return { sku, data: null, error: e.message };
      }
    });
    const results = await Promise.all(promises);
    setItems(results);
  };

  const toggleImageSelection = (sku, filename) => {
    setSelectedImages((prev) => {
      const current = prev[sku] || [];
      const updated = current.includes(filename)
        ? current.filter((f) => f !== filename)
        : [...current, filename];
      return { ...prev, [sku]: updated };
    });
  };

  const handleToggleMainImage = async (sku, filename, isCurrentlyMain) => {
    try {
      const endpoint = isCurrentlyMain ? "unmark-main" : "mark-main";
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/images/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          filenames: [filename],
        }),
      });
      const result = await res.json();
      if (result.success) {
        // Refresh images for this SKU
        const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setItems((prev) =>
            prev.map((item) =>
              item.sku === sku ? { ...item, data: refreshData, error: null } : item
            )
          );
        }
      } else {
        alert(result.message || "Failed to update main image");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  };

  const handleRotate = async (sku, filename, degrees) => {
    const key = `${sku}/${filename}`;
    setRotating((prev) => ({ ...prev, [key]: true }));

    try {
      const res = await fetch(
        `/api/images/${encodeURIComponent(sku)}/${encodeURIComponent(filename)}/rotate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sku, filename, degrees }),
        }
      );

      if (!res.ok) throw new Error("Rotation failed");
      const result = await res.json();

      if (result.success) {
        // Refresh images for this SKU
        const safeSku = encodeURIComponent(sku);
        const refreshRes = await fetch(`/api/skus/${safeSku}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setItems((prev) =>
            prev.map((item) =>
              item.sku === sku ? { ...item, data: refreshData, error: null } : item
            )
          );
        }
      } else {
        alert(result.message || "Rotation failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setRotating((prev) => ({ ...prev, [key]: false }));
    }
  };

  const loadProductDetails = async (sku) => {
    if (productDetails[sku]) return; // Already loaded

    setDetailsLoading((prev) => ({ ...prev, [sku]: true }));
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
      if (res.ok) {
        const data = await res.json();
        setProductDetails((prev) => ({ ...prev, [sku]: data }));
      }
    } catch (e) {
      console.error(`Failed to load details for ${sku}:`, e);
    } finally {
      setDetailsLoading((prev) => ({ ...prev, [sku]: false }));
    }
  };

  const toggleDetailsExpand = async (sku) => {
    if (!expandedDetails[sku]) {
      await loadProductDetails(sku);
      // Initialize edit state
      if (productDetails[sku] && !editedFieldsState[sku]) {
        const initialEdited = {};
        productDetails[sku].categories.forEach(cat => {
          initialEdited[cat.name] = {};
          cat.fields.forEach(field => {
            initialEdited[cat.name][field.name] = field.value;
          });
        });
        setEditedFieldsState(prev => ({ ...prev, [sku]: initialEdited }));
      }
    }
    setExpandedDetails((prev) => ({ ...prev, [sku]: !prev[sku] }));
  };

  const toggleSkuForEnrichment = (sku) => {
    const newSet = new Set(selectedSkusForEnrichment);
    if (newSet.has(sku)) {
      newSet.delete(sku);
    } else {
      newSet.add(sku);
    }
    setSelectedSkusForEnrichment(newSet);
  };

  const handleEnrichAll = async () => {
    if (selectedSkusForEnrichment.size === 0) {
      alert("Please select at least one SKU to enrich");
      return;
    }

    setEnrichmentInProgress(true);
    setEnrichmentResults(null);

    try {
      const res = await fetch(`/api/ai/enrich/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skus: Array.from(selectedSkusForEnrichment),
        }),
      });

      const result = await res.json();
      setEnrichmentResults(result);

      if (result.success || result.failed === 0) {
        alert(`✅ Enrichment complete! Succeeded: ${result.succeeded}, Failed: ${result.failed}`);
      } else {
        alert(`⚠️ Enrichment completed with errors. Succeeded: ${result.succeeded}, Failed: ${result.failed}`);
      }

      // Reload product details for enriched SKUs
      setEnrichmentInProgress(false);
      selectedSkusForEnrichment.forEach(sku => {
        setProductDetails(prev => {
          const newState = { ...prev };
          delete newState[sku];
          return newState;
        });
      });
      setSelectedSkusForEnrichment(new Set());
    } catch (e) {
      alert(`Error: ${e.message}`);
      setEnrichmentInProgress(false);
    }
  };

  useEffect(() => {
    if (selectedSkus.length === 0) {
      setItems([]);
      return;
    }

    let cancelled = false;
    async function loadAll() {
      await fetchAllImages();
    }
    loadAll();
    return () => {
      cancelled = true;
    };
  }, [selectedSkus]);

  if (selectedSkus.length === 0) {
    return (
      <div>
        <div style={{ marginBottom: 12 }}>
          <Link to="/skus">← Back to list</Link>
        </div>
        <div>No SKUs selected.</div>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", maxWidth: "2200px", margin: "0 auto", padding: "0 16px", boxSizing: "border-box" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <Link to="/skus">← Back to list</Link>
        <h3 style={{ margin: 0 }}>Batch view ({selectedSkus.length} SKUs)</h3>
      </div>

      {/* Global classification panel */}
      {totalSelectedImages > 0 && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          background: "#f5f5f5",
          padding: 12,
          borderRadius: 0,
          marginBottom: 16,
          border: "none",
          borderBottom: "2px solid #2196F3",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 8 }}>
            Batch Classify: {totalSelectedImages} image(s) selected across {Object.keys(selectedImages).filter(sku => selectedImages[sku].length > 0).length} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={() => handleBatchClassifyAll("phone")}
              disabled={batchClassifying}
              style={{
                padding: "8px 14px",
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: 4,
                fontWeight: "bold",
              }}
            >
              📱 Classify All as Phone
            </button>
            <button
              onClick={() => handleBatchClassifyAll("stock")}
              disabled={batchClassifying}
              style={{
                padding: "8px 14px",
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#FF9800",
                color: "white",
                border: "none",
                borderRadius: 4,
                fontWeight: "bold",
              }}
            >
              📦 Classify All as Stock
            </button>
            <button
              onClick={() => handleBatchClassifyAll("enhanced")}
              disabled={batchClassifying}
              style={{
                padding: "8px 14px",
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#9C27B0",
                color: "white",
                border: "none",
                borderRadius: 4,
                fontWeight: "bold",
              }}
            >
              ✨ Classify All as Enhanced
            </button>
            <button
              onClick={handleBatchMarkAsMain}
              disabled={batchClassifying}
              style={{
                padding: "8px 14px",
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#FFD700",
                color: "#000",
                border: "none",
                borderRadius: 4,
                fontWeight: "bold",
              }}
            >
              ⭐ Mark All as Main
            </button>
            <button
              onClick={() => setSelectedImages({})}
              style={{
                padding: "8px 14px",
                cursor: "pointer",
                background: "#666",
                color: "white",
                border: "none",
                borderRadius: 4,
              }}
            >
              Clear All Selections
            </button>
          </div>
        </div>
      )}

      {/* AI Enrichment Panel */}
      <div style={{
        background: "#f0f7ff",
        padding: 16,
        borderRadius: 8,
        marginBottom: 24,
        border: "2px solid #1976D2",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
      }}>
        <div style={{ fontWeight: "bold", marginBottom: 12, fontSize: 16, color: "#1976D2" }}>
          🤖 AI Product Details Enrichment
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12, alignItems: "center" }}>
          <span style={{ color: "#555" }}>Select SKUs to enrich: <strong>{selectedSkusForEnrichment.size}</strong> selected</span>
          <button
            onClick={() => {
              if (selectedSkusForEnrichment.size === items.length) {
                setSelectedSkusForEnrichment(new Set());
              } else {
                const allSkus = new Set(items.map(item => item.sku));
                setSelectedSkusForEnrichment(allSkus);
              }
            }}
            style={{
              padding: "6px 12px",
              fontSize: 12,
              background: "#555",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {selectedSkusForEnrichment.size === items.length ? "Deselect All" : "Select All"}
          </button>
          <button
            onClick={handleEnrichAll}
            disabled={enrichmentInProgress || selectedSkusForEnrichment.size === 0}
            style={{
              padding: "8px 16px",
              fontSize: 12,
              background: enrichmentInProgress ? "#ccc" : "#1976D2",
              color: "white",
              border: "none",
              borderRadius: 4,
              fontWeight: "bold",
              cursor: enrichmentInProgress || selectedSkusForEnrichment.size === 0 ? "not-allowed" : "pointer",
            }}
          >
            {enrichmentInProgress ? "Enriching..." : "✨ Enrich Selected SKUs"}
          </button>
        </div>

        {/* Enrichment results */}
        {enrichmentResults && (
          <div style={{
            background: "white",
            padding: 12,
            borderRadius: 4,
            marginTop: 12,
            border: `2px solid ${enrichmentResults.failed === 0 ? "#4CAF50" : "#FF9800"}`,
          }}>
            <div style={{ fontWeight: "bold", marginBottom: 8 }}>
              {enrichmentResults.failed === 0 ? "✅" : "⚠️"} Results: {enrichmentResults.succeeded} succeeded, {enrichmentResults.failed} failed
            </div>
            {Object.entries(enrichmentResults.results).map(([s, res]) => (
              <div key={s} style={{ fontSize: 12, padding: "4px 0", color: res.success ? "#4CAF50" : "#FF3D00" }}>
                {s}: {res.success ? `+${res.updated_fields} fields` : res.message}
              </div>
            ))}
          </div>
        )}
      </div>

      {items.length === 0 && (
        <div style={{
          padding: 24,
          textAlign: "center",
          color: "#999",
          background: "#f5f5f5",
          borderRadius: 8,
          marginBottom: 24
        }}>
          <div style={{ fontSize: 14 }}>Loading SKU data...</div>
          <div style={{ fontSize: 12, marginTop: 8 }}>Selected: {selectedSkus.length} SKU(s)</div>
        </div>
      )}

      {items.map(({ sku, data, error }) => {
        const images = Array.isArray(data?.images) ? data.images : [];
        return (
          <div key={sku} style={{ marginBottom: 24, border: "1px solid #e0e0e0", borderRadius: 10, padding: 16 }}>
            {/* SKU Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 4 }}>
                  <input
                    type="checkbox"
                    checked={selectedSkusForEnrichment.has(sku)}
                    onChange={() => toggleSkuForEnrichment(sku)}
                    style={{ width: 18, height: 18, cursor: "pointer" }}
                    title="Select for AI enrichment"
                  />
                  <h4 style={{ margin: 0 }}>SKU: <span style={{ fontFamily: "ui-monospace" }}>{sku}</span></h4>
                  {jsonStatus[sku] !== undefined && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 8px", background: jsonStatus[sku] ? "#e8f5e9" : "#fff3e0", borderRadius: 4, fontSize: "0.85em" }}>
                      <span style={{ fontWeight: "bold", color: jsonStatus[sku] ? "#4caf50" : "#ff9800" }}>
                        {jsonStatus[sku] ? "✓ JSON" : "✗ No JSON"}
                      </span>
                      {!jsonStatus[sku] && (
                        <button
                          onClick={() => handleGenerateJson(sku)}
                          disabled={generatingJson[sku]}
                          style={{
                            padding: "4px 6px",
                            fontSize: "0.8em",
                            cursor: generatingJson[sku] ? "not-allowed" : "pointer",
                            background: "#ff9800",
                            color: "white",
                            border: "none",
                            borderRadius: 3,
                          }}
                        >
                          {generatingJson[sku] ? "Gen..." : "Gen"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <div style={{ color: "#666", marginTop: 4 }}>
                  {error ? (
                    <span style={{ color: "#c00" }}>{error}</span>
                  ) : (
                    `folder_found=${String(data?.folder_found)} • count=${data?.count ?? images.length} • selected=${(selectedImages[sku] || []).length}`
                  )}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button onClick={() => navigate(`/skus/${encodeURIComponent(sku)}`, { state: { selectedSkus } })}>
                  Open single view
                </button>
                {images.length > 0 && (
                  <>
                    <button
                      onClick={() => {
                        const allFilenames = images.map(img => img.filename);
                        setSelectedImages(prev => ({ ...prev, [sku]: allFilenames }));
                      }}
                      style={{
                        padding: "6px 10px",
                        fontSize: "0.8em",
                        cursor: "pointer",
                        background: "#666",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                      }}
                    >
                      Select All
                    </button>
                    <button
                      onClick={() => handleClassifyImages(sku, "phone")}
                      disabled={!selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku]}
                      style={{
                        padding: "6px 10px",
                        fontSize: "0.8em",
                        cursor: !selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku] ? "not-allowed" : "pointer",
                        background: "#2196F3",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                      }}
                    >
                      📱 Phone
                    </button>
                    <button
                      onClick={() => handleClassifyImages(sku, "stock")}
                      disabled={!selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku]}
                      style={{
                        padding: "6px 10px",
                        fontSize: "0.8em",
                        cursor: !selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku] ? "not-allowed" : "pointer",
                        background: "#FF9800",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                      }}
                    >
                      📦 Stock
                    </button>
                    <button
                      onClick={() => handleClassifyImages(sku, "enhanced")}
                      disabled={!selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku]}
                      style={{
                        padding: "6px 10px",
                        fontSize: "0.8em",
                        cursor: !selectedImages[sku] || selectedImages[sku].length === 0 || classifying[sku] ? "not-allowed" : "pointer",
                        background: "#9C27B0",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                      }}
                    >
                      ✨ Enhanced
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Product Details Collapsible Section */}
            <div style={{ marginTop: 16, borderTop: "2px solid #e0e0e0", paddingTop: 16 }}>
              <button
                onClick={() => toggleDetailsExpand(sku)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontWeight: "bold",
                  color: "#2196F3",
                  fontSize: 15,
                  marginBottom: 12
                }}
              >
                <span style={{ fontSize: 18, transform: expandedDetails[sku] ? "rotate(90deg)" : "rotate(0deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
                📋 Product Details {productDetails[sku] && `(${productDetails[sku].filled_fields}/${productDetails[sku].total_fields})`}
              </button>

              {expandedDetails[sku] && (
                <div>
                  {detailsLoading[sku] && <div style={{ fontSize: 12, color: "#666" }}>Loading...</div>}

                  {productDetails[sku] && (
                    <div>
                      <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f0f0f0", borderRadius: 4 }}>
                        <div style={{ color: "#666", fontSize: 11 }}>Completion</div>
                        <div style={{ fontWeight: "bold", marginTop: 4, fontSize: 14 }}>
                          {productDetails[sku].completion_percentage}%
                        </div>
                        <div style={{ marginTop: 6, background: "#ddd", borderRadius: 3, height: 6, overflow: "hidden" }}>
                          <div
                            style={{
                              background: "#4CAF50",
                              height: "100%",
                              width: `${productDetails[sku].completion_percentage}%`,
                              transition: "width 0.3s ease"
                            }}
                          />
                        </div>
                      </div>

                      {!editingDetails[sku] ? (
                        <>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 12 }}>
                            {productDetails[sku].categories.map((cat) => (
                              <div key={cat.name} style={{ paddingBottom: 12, borderBottom: "1px solid #e0e0e0" }}>
                                <div style={{ fontWeight: "bold", color: "#1976D2", marginBottom: 8, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                                  {cat.name}
                                </div>
                                {cat.fields.map((field) => (
                                  <div key={field.name} style={{ marginBottom: 8 }}>
                                    <div style={{
                                      color: field.is_highlighted ? "#c62828" : "#555",
                                      fontWeight: field.is_highlighted ? "700" : "600",
                                      marginBottom: 3,
                                      fontSize: 12
                                    }}>
                                      {field.name}
                                    </div>
                                    <div style={{
                                      color: field.value ? "#333" : "#999",
                                      background: field.value ? "#f9f9f9" : "#fff",
                                      padding: "6px 8px",
                                      borderRadius: 3,
                                      fontSize: 12,
                                      minHeight: 24,
                                      wordBreak: "break-word",
                                      border: "1px solid #e0e0e0"
                                    }}>
                                      {field.value || "(empty)"}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>

                          <button
                            onClick={() => {
                              const initialEdited = {};
                              productDetails[sku].categories.forEach(cat => {
                                initialEdited[cat.name] = {};
                                cat.fields.forEach(field => {
                                  initialEdited[cat.name][field.name] = field.value;
                                });
                              });
                              setEditedFieldsState(prev => ({ ...prev, [sku]: initialEdited }));
                              setEditingDetails(prev => ({ ...prev, [sku]: true }));
                            }}
                            style={{
                              padding: "8px 16px",
                              fontSize: 12,
                              background: "#2196F3",
                              color: "white",
                              border: "none",
                              borderRadius: 4,
                              cursor: "pointer",
                              fontWeight: "bold"
                            }}
                          >
                            ✏️ Edit All Details
                          </button>
                        </>
                      ) : (
                        <>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 12 }}>
                            {productDetails[sku].categories.map((cat) => (
                              <div key={cat.name} style={{ paddingBottom: 12, borderBottom: "1px solid #e0e0e0" }}>
                                <div style={{ fontWeight: "bold", color: "#1976D2", marginBottom: 8, fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                                  {cat.name}
                                </div>
                                {cat.fields.map((field) => (
                                  <div key={field.name} style={{ marginBottom: 8 }}>
                                    <label style={{
                                      display: "block",
                                      color: field.is_highlighted ? "#c62828" : "#555",
                                      fontWeight: field.is_highlighted ? "700" : "600",
                                      marginBottom: 4,
                                      fontSize: 12
                                    }}>
                                      {field.name}
                                    </label>
                                    <textarea
                                      value={editedFieldsState[sku]?.[cat.name]?.[field.name] ?? field.value}
                                      onChange={(e) => {
                                        setEditedFieldsState(prev => ({
                                          ...prev,
                                          [sku]: {
                                            ...(prev[sku] || {}),
                                            [cat.name]: {
                                              ...(prev[sku]?.[cat.name] || {}),
                                              [field.name]: e.target.value
                                            }
                                          }
                                        }));
                                      }}
                                      style={{
                                        width: "100%",
                                        padding: "6px 8px",
                                        border: "1px solid #2196F3",
                                        borderRadius: 3,
                                        fontSize: 12,
                                        fontFamily: "monospace",
                                        minHeight: 50,
                                        boxSizing: "border-box",
                                        resize: "vertical"
                                      }}
                                    />
                                  </div>
                                ))}
                              </div>
                            ))}
                          </div>

                          <div style={{ display: "flex", gap: 8 }}>
                            <button
                              onClick={async () => {
                                try {
                                  const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({
                                      sku,
                                      updates: editedFieldsState[sku]
                                    })
                                  });
                                  const result = await res.json();
                                  if (result.success) {
                                    alert(`✅ Saved ${result.updated_fields} field(s)`);
                                    setEditingDetails(prev => ({ ...prev, [sku]: false }));
                                    // Refresh product details
                                    const detailsRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
                                    if (detailsRes.ok) {
                                      const detailsData = await detailsRes.json();
                                      setProductDetails(prev => ({ ...prev, [sku]: detailsData }));
                                    }
                                  } else {
                                    alert(result.message || "Failed to save");
                                  }
                                } catch (e) {
                                  alert(`Error: ${e.message}`);
                                }
                              }}
                              style={{
                                flex: 1,
                                padding: "8px 16px",
                                fontSize: 12,
                                background: "#4CAF50",
                                color: "white",
                                border: "none",
                                borderRadius: 4,
                                cursor: "pointer",
                                fontWeight: "bold"
                              }}
                            >
                              💾 Save All Changes
                            </button>
                            <button
                              onClick={() => setEditingDetails(prev => ({ ...prev, [sku]: false }))}
                              style={{
                                flex: 1,
                                padding: "8px 16px",
                                fontSize: 12,
                                background: "#999",
                                color: "white",
                                border: "none",
                                borderRadius: 4,
                                cursor: "pointer",
                                fontWeight: "bold"
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {images.length === 0 && !error && (
              <div style={{ padding: 12, color: "#666" }}>No images found.</div>
            )}

            {images.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10 }}>
                {images.map((img) => {
                  const rotatingKey = `${sku}/${img.filename}`;
                  const isRotating = rotating[rotatingKey];
                  const isSelected = (selectedImages[sku] || []).includes(img.filename);
                  return (
                    <div key={img.filename} style={{ border: isSelected ? "3px solid #2196F3" : "1px solid #ddd", borderRadius: 10, overflow: "hidden", position: "relative" }}>
                      {/* Selection checkbox */}
                      <div style={{ position: "absolute", top: 4, left: 4, zIndex: 10 }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleImageSelection(sku, img.filename)}
                          style={{ width: 20, height: 20, cursor: "pointer" }}
                        />
                      </div>
                      {/* Main image star badge */}
                      {img.is_main && (
                        <div style={{
                          position: "absolute",
                          top: 4,
                          left: 32,
                          zIndex: 10,
                          background: "#FFD700",
                          color: "#000",
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: "0.7em",
                          fontWeight: "bold",
                          boxShadow: "0 2px 4px rgba(0,0,0,0.2)"
                        }}>
                          ⭐ Main
                        </div>
                      )}
                      {/* Classification badge */}
                      {img.classification && (
                        <div style={{
                          position: "absolute",
                          top: 4,
                          right: 4,
                          zIndex: 10,
                          padding: "2px 6px",
                          borderRadius: 4,
                          fontSize: "0.7em",
                          fontWeight: "bold",
                          background: img.classification === "phone" ? "#2196F3" : img.classification === "stock" ? "#FF9800" : "#9C27B0",
                          color: "white"
                        }}>
                          {img.classification === "phone" ? "📱" : img.classification === "stock" ? "📦" : "✨"}
                        </div>
                      )}
                      <button
                        onClick={() => setPreview({ sku, img })}
                        style={{ all: "unset", cursor: "pointer", display: "block", position: "relative" }}
                        title={img.filename}
                      >
                        <img
                          src={`${img.thumb_url}&t=${Date.now()}`}
                          alt={img.filename}
                          style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "cover", display: "block", opacity: isRotating ? 0.5 : 1 }}
                          loading="lazy"
                        />
                        {isRotating && (
                          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.3)", color: "white" }}>
                            Rotating...
                          </div>
                        )}
                      </button>
                      <div style={{ padding: 8 }}>
                        <div style={{ fontSize: 12, fontFamily: "ui-monospace", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {img.filename}
                        </div>
                        <div style={{ fontSize: 12, color: "#666", marginTop: 4, display: "flex", gap: 8, flexWrap: "wrap" }}>
                          {img.is_ebay ? <span>eBay</span> : null}
                          {img.source ? <span>{img.source}</span> : null}
                        </div>
                        <div style={{ marginTop: 6, display: "flex", gap: 4, justifyContent: "center", flexWrap: "wrap" }}>
                          <button
                            onClick={() => handleToggleMainImage(sku, img.filename, img.is_main)}
                            style={{ 
                              padding: "2px 6px", 
                              fontSize: 11, 
                              cursor: "pointer",
                              background: img.is_main ? "#FFD700" : "#e0e0e0",
                              color: img.is_main ? "#000" : "#666",
                              border: "none",
                              borderRadius: 3,
                              fontWeight: img.is_main ? "bold" : "normal"
                            }}
                            title={img.is_main ? "Unmark as main" : "Mark as main"}
                          >
                            {img.is_main ? "⭐ Main" : "☆ Main"}
                          </button>
                          <button
                            onClick={() => handleRotate(sku, img.filename, 90)}
                            disabled={isRotating}
                            style={{ padding: "2px 6px", fontSize: 11, cursor: isRotating ? "not-allowed" : "pointer" }}
                            title="Rotate 90° clockwise"
                          >
                            ↻90°
                          </button>
                          <button
                            onClick={() => handleRotate(sku, img.filename, 180)}
                            disabled={isRotating}
                            style={{ padding: "2px 6px", fontSize: 11, cursor: isRotating ? "not-allowed" : "pointer" }}
                            title="Rotate 180°"
                          >
                            ↻180°
                          </button>
                          <button
                            onClick={() => handleRotate(sku, img.filename, 270)}
                            disabled={isRotating}
                            style={{ padding: "2px 6px", fontSize: 11, cursor: isRotating ? "not-allowed" : "pointer" }}
                            title="Rotate 270° clockwise"
                          >
                            ↻270°
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      <Modal open={!!preview} onClose={() => setPreview(null)}>
        {preview && (
          <div>
            <div style={{ fontFamily: "ui-monospace", marginBottom: 8 }}>
              {preview.sku} • {preview.img.filename}
            </div>
            <img
              src={preview.img.preview_url || preview.img.original_url}
              alt={preview.img.filename}
              style={{ maxWidth: "85vw", maxHeight: "75vh", display: "block" }}
            />
            <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <a href={preview.img.original_url} target="_blank" rel="noreferrer">Open original</a>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useLocation, useNavigate } from "react-router-dom";

function Modal({ open, onClose, children }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ background: "white", borderRadius: 10, maxWidth: "90vw", maxHeight: "90vh", overflow: "auto", padding: 12 }}
      >
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
          <button onClick={onClose} style={{ padding: "6px 10px" }}>Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function SkuDetailPage() {
  const { sku: skuParam } = useParams();
  const sku = decodeURIComponent(skuParam ?? "");
  const location = useLocation();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [data, setData] = useState(null);
  const [jsonExists, setJsonExists] = useState(null);
  const [generatingJson, setGeneratingJson] = useState(false);

  const [preview, setPreview] = useState(null); // image object
  const [gridCols, setGridCols] = useState(4); // number of columns in the grid
  const [rotating, setRotating] = useState({}); // { "filename": true }
  const [selectedImages, setSelectedImages] = useState([]); // selected image filenames
  const [classifying, setClassifying] = useState(false);

  // Product details state
  const [productDetails, setProductDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [editingDetails, setEditingDetails] = useState(false);
  const [editedFields, setEditedFields] = useState({});

  const handleGenerateJson = async () => {
    setGeneratingJson(true);
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/json/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const result = await res.json();
      if (result.success) {
        setJsonExists(true);
        alert("JSON created from inventory data");
      } else {
        alert(result.message || "Failed to create JSON");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setGeneratingJson(false);
    }
  };

  const handleClassifyImages = async (classificationType) => {
    if (selectedImages.length === 0) {
      alert("No images selected");
      return;
    }

    setClassifying(true);
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/images/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          filenames: selectedImages,
          classification_type: classificationType,
        }),
      });
      const result = await res.json();
      if (result.success) {
        alert(`✅ Classified ${result.processed_count} image(s) as ${classificationType}`);
        setSelectedImages([]);
        // Refresh to show updated classifications
        const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setData(refreshData);
        }
      } else {
        alert(result.message || "Classification failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setClassifying(false);
    }
  };

  const toggleImageSelection = (filename) => {
    setSelectedImages((prev) =>
      prev.includes(filename)
        ? prev.filter((f) => f !== filename)
        : [...prev, filename]
    );
  };

  const handleToggleMainImage = async (filename, isCurrentlyMain) => {
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
        // Refresh images to show updated main status
        const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setData(refreshData);
        }
      } else {
        alert(result.message || "Failed to update main image");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  };

  const selectAllImages = () => {
    setSelectedImages(images.map((img) => img.filename));
  };

  const deselectAllImages = () => {
    setSelectedImages([]);
  };

  const handleRotate = async (filename, degrees) => {
    setRotating((prev) => ({ ...prev, [filename]: true }));

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
        // Refresh images
        const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          setData(refreshData);
        }
      } else {
        alert(result.message || "Rotation failed");
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setRotating((prev) => ({ ...prev, [filename]: false }));
    }
  };

  const batchSkus = useMemo(() => {
    const incoming = Array.isArray(location.state?.selectedSkus)
      ? location.state.selectedSkus.filter(Boolean)
      : [];
    const uniq = Array.from(new Set(incoming));
    if (!uniq.includes(sku)) uniq.unshift(sku);
    return uniq;
  }, [location.state, sku]);

  const currentIndex = batchSkus.findIndex((s) => s === sku);

  const goToIndex = (idx) => {
    if (idx < 0 || idx >= batchSkus.length) return;
    const nextSku = batchSkus[idx];
    navigate(`/skus/${encodeURIComponent(nextSku)}`, { state: { selectedSkus: batchSkus } });
  };

  useEffect(() => {
    let alive = true;
    async function run() {
      try {
        setLoading(true);
        setErr("");
        const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
        if (!res.ok) throw new Error(`GET /skus/{sku}/images failed (${res.status})`);
        const json = await res.json();
        if (alive) setData(json);
        
        // Fetch JSON status
        try {
          const statusRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/json/status`);
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            if (alive) setJsonExists(statusData.json_exists);
          }
        } catch (e) {
          // Silently fail, JSON status is optional
        }
        
        // Fetch product details
        try {
          setDetailsLoading(true);
          const detailsRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
          if (detailsRes.ok) {
            const detailsData = await detailsRes.json();
            if (alive) {
              setProductDetails(detailsData);
              // Initialize edited fields from product details
              const initialEdited = {};
              detailsData.categories.forEach(cat => {
                initialEdited[cat.name] = {};
                cat.fields.forEach(field => {
                  initialEdited[cat.name][field.name] = field.value;
                });
              });
              setEditedFields(initialEdited);
            }
          }
        } catch (e) {
          // Silently fail, product details are optional
        } finally {
          if (alive) setDetailsLoading(false);
        }
      } catch (e) {
        if (alive) setErr(String(e.message ?? e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    return () => { alive = false; };
  }, [sku]);

  const images = useMemo(() => {
    if (!data || !Array.isArray(data.images)) return [];
    return data.images;
  }, [data]);

  return (
    <div style={{ display: "flex", gap: 16 }}>
      {/* Main content area */}
      <div style={{ flex: 1 }}>
      <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <Link to="/skus">← Back</Link>
            <h3 style={{ margin: 0 }}>SKU: <span style={{ fontFamily: "ui-monospace" }}>{sku}</span></h3>
            {jsonExists !== null && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 8px", background: jsonExists ? "#e8f5e9" : "#fff3e0", borderRadius: 4, fontSize: "0.85em" }}>
                <span style={{ fontWeight: "bold", color: jsonExists ? "#4caf50" : "#ff9800" }}>
                  {jsonExists ? "✓ JSON" : "✗ No JSON"}
                </span>
                {!jsonExists && (
                  <button
                    onClick={handleGenerateJson}
                    disabled={generatingJson}
                    style={{
                      padding: "4px 6px",
                      fontSize: "0.8em",
                      cursor: generatingJson ? "not-allowed" : "pointer",
                      background: "#ff9800",
                      color: "white",
                      border: "none",
                      borderRadius: 3,
                    }}
                  >
                    {generatingJson ? "Gen..." : "Gen"}
                  </button>
                )}
              </div>
            )}
          </div>
          <div style={{ color: "#666", marginTop: 6 }}>
            {loading ? "Loading..." : `folder_found=${String(data?.folder_found)} • count=${data?.count ?? images.length}`}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          {batchSkus.length > 1 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                onClick={() => goToIndex(currentIndex - 1)}
                disabled={currentIndex <= 0}
              >
                ← Previous
              </button>
              <div style={{ fontSize: 13, color: "#444" }}>
                {currentIndex + 1} / {batchSkus.length}
              </div>
              <button
                onClick={() => goToIndex(currentIndex + 1)}
                disabled={currentIndex >= batchSkus.length - 1}
              >
                Next →
              </button>
            </div>
          )}
          <label style={{ color: "#444", fontSize: 14 }}>
            Grid columns:
            <select
              value={gridCols}
              onChange={(e) => setGridCols(Number(e.target.value))}
              style={{ marginLeft: 6, padding: "4px 6px" }}
            >
              {[2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {err && (
        <div style={{ padding: 12, background: "#fee", border: "1px solid #f99", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))`, gap: 10 }}>
        {images.map((img) => {
          const isRotating = rotating[img.filename];
          const isSelected = selectedImages.includes(img.filename);
          return (
            <div key={img.filename} style={{ border: isSelected ? "3px solid #2196F3" : "1px solid #ddd", borderRadius: 10, overflow: "hidden", position: "relative" }}>
              {/* Selection checkbox */}
              <div style={{ position: "absolute", top: 4, left: 4, zIndex: 10 }}>
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleImageSelection(img.filename)}
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
                onClick={() => setPreview(img)}
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
                  {img.is_main ? <span>Main</span> : null}
                  {img.is_ebay ? <span>eBay</span> : null}
                  {img.source ? <span>{img.source}</span> : null}
                </div>
                <div style={{ marginTop: 6, display: "flex", gap: 4, justifyContent: "center", flexWrap: "wrap" }}>
                  <button
                    onClick={() => handleToggleMainImage(img.filename, img.is_main)}
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
                    onClick={() => handleRotate(img.filename, 90)}
                    disabled={isRotating}
                    style={{ padding: "2px 6px", fontSize: 11, cursor: isRotating ? "not-allowed" : "pointer" }}
                    title="Rotate 90° clockwise"
                  >
                    ↻90°
                  </button>
                  <button
                    onClick={() => handleRotate(img.filename, 180)}
                    disabled={isRotating}
                    style={{ padding: "2px 6px", fontSize: 11, cursor: isRotating ? "not-allowed" : "pointer" }}
                    title="Rotate 180°"
                  >
                    ↻180°
                  </button>
                  <button
                    onClick={() => handleRotate(img.filename, 270)}
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
      </div>

      {/* Right panel - Classification */}
      <div style={{ width: 240, background: "#f9f9f9", padding: 16, borderRadius: 8, height: "fit-content", position: "sticky", top: 16 }}>
        <h4 style={{ margin: "0 0 12px 0", fontSize: 16 }}>Classify Images</h4>
        
        <div style={{ marginBottom: 16, fontSize: 14, color: "#666" }}>
          <div><strong>{selectedImages.length}</strong> selected</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          <button
            onClick={selectAllImages}
            disabled={images.length === 0}
            style={{ padding: "6px 10px", fontSize: 13, cursor: images.length === 0 ? "not-allowed" : "pointer" }}
          >
            Select All
          </button>
          <button
            onClick={deselectAllImages}
            disabled={selectedImages.length === 0}
            style={{ padding: "6px 10px", fontSize: 13, cursor: selectedImages.length === 0 ? "not-allowed" : "pointer" }}
          >
            Deselect All
          </button>
        </div>

        <hr style={{ border: "none", borderTop: "1px solid #ddd", margin: "16px 0" }} />

        <h5 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Classify as:</h5>
        
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            onClick={() => handleClassifyImages("phone")}
            disabled={selectedImages.length === 0 || classifying}
            style={{
              padding: "8px 12px",
              fontSize: 13,
              cursor: selectedImages.length === 0 || classifying ? "not-allowed" : "pointer",
              background: "#2196F3",
              color: "white",
              border: "none",
              borderRadius: 4,
            }}
          >
            📱 Phone
          </button>
          <button
            onClick={() => handleClassifyImages("stock")}
            disabled={selectedImages.length === 0 || classifying}
            style={{
              padding: "8px 12px",
              fontSize: 13,
              cursor: selectedImages.length === 0 || classifying ? "not-allowed" : "pointer",
              background: "#FF9800",
              color: "white",
              border: "none",
              borderRadius: 4,
            }}
          >
            📦 Stock
          </button>
          <button
            onClick={() => handleClassifyImages("enhanced")}
            disabled={selectedImages.length === 0 || classifying}
            style={{
              padding: "8px 12px",
              fontSize: 13,
              cursor: selectedImages.length === 0 || classifying ? "not-allowed" : "pointer",
              background: "#9C27B0",
              color: "white",
              border: "none",
              borderRadius: 4,
            }}
          >
            ✨ Enhanced
          </button>
        </div>

        {classifying && (
          <div style={{ marginTop: 12, fontSize: 12, color: "#666", textAlign: "center" }}>
            Classifying...
          </div>
        )}
      </div>

      <Modal open={!!preview} onClose={() => setPreview(null)}>
        {preview && (
          <div>
            <div style={{ fontFamily: "ui-monospace", marginBottom: 8 }}>{preview.filename}</div>
            <img
              src={preview.preview_url || preview.original_url}
              alt={preview.filename}
              style={{ maxWidth: "85vw", maxHeight: "75vh", display: "block" }}
            />
            <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <a href={preview.original_url} target="_blank" rel="noreferrer">Open original</a>
            </div>
          </div>
        )}
      </Modal>

      {/* Product Details Sidebar */}
      <div style={{ width: 350, borderLeft: "1px solid #e0e0e0", paddingLeft: 16, maxHeight: "90vh", overflowY: "auto" }}>
        <h4 style={{ margin: "0 0 12px 0", fontSize: 14, fontWeight: "bold" }}>Product Details</h4>
        
        {detailsLoading && <div style={{ color: "#666", fontSize: 12 }}>Loading details...</div>}
        
        {productDetails && !editingDetails && (
          <div>
            <div style={{ marginBottom: 12, padding: 8, background: "#f0f0f0", borderRadius: 4 }}>
              <div style={{ fontSize: 11, color: "#666" }}>Completion</div>
              <div style={{ fontSize: 13, fontWeight: "bold", marginTop: 4 }}>
                {productDetails.filled_fields} / {productDetails.total_fields} fields ({productDetails.completion_percentage}%)
              </div>
              <div style={{ marginTop: 8, background: "#ddd", borderRadius: 2, height: 6, overflow: "hidden" }}>
                <div
                  style={{
                    background: "#4CAF50",
                    height: "100%",
                    width: `${productDetails.completion_percentage}%`,
                    transition: "width 0.3s ease"
                  }}
                />
              </div>
            </div>

            {productDetails.categories.map((cat) => (
              <div key={cat.name} style={{ marginBottom: 12, borderBottom: "1px solid #e0e0e0", paddingBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: "bold", color: "#333", marginBottom: 6 }}>{cat.name}</div>
                {cat.fields.map((field) => (
                  <div key={field.name} style={{ marginBottom: 6, fontSize: 11 }}>
                    <div style={{
                      fontWeight: "600",
                      color: field.is_highlighted ? "#d32f2f" : "#666",
                      marginBottom: 2
                    }}>
                      {field.name}
                    </div>
                    <div style={{
                      padding: "4px 6px",
                      background: field.value ? "#f5f5f5" : "#fff",
                      border: "1px solid #e0e0e0",
                      borderRadius: 3,
                      fontSize: 10,
                      color: field.value ? "#333" : "#999",
                      minHeight: 20,
                      wordBreak: "break-word"
                    }}>
                      {field.value || "(empty)"}
                    </div>
                  </div>
                ))}
              </div>
            ))}

            <button
              onClick={() => setEditingDetails(true)}
              style={{
                width: "100%",
                padding: "8px 12px",
                marginTop: 12,
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 12,
                fontWeight: "bold"
              }}
            >
              ✏️ Edit Details
            </button>
          </div>
        )}

        {productDetails && editingDetails && (
          <div>
            {productDetails.categories.map((cat) => (
              <div key={cat.name} style={{ marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e0e0e0" }}>
                <div style={{ fontSize: 10, fontWeight: "bold", color: "#666", marginBottom: 6, textTransform: "uppercase" }}>
                  {cat.name}
                </div>
                {cat.fields.map((field) => (
                  <div key={field.name} style={{ marginBottom: 6 }}>
                    <label style={{
                      fontSize: 10,
                      fontWeight: "600",
                      color: field.is_highlighted ? "#d32f2f" : "#333",
                      display: "block",
                      marginBottom: 2
                    }}>
                      {field.name}
                    </label>
                    <textarea
                      value={editedFields[cat.name]?.[field.name] ?? field.value}
                      onChange={(e) => {
                        setEditedFields(prev => ({
                          ...prev,
                          [cat.name]: {
                            ...(prev[cat.name] || {}),
                            [field.name]: e.target.value
                          }
                        }));
                      }}
                      style={{
                        width: "100%",
                        padding: "4px 6px",
                        border: "1px solid #2196F3",
                        borderRadius: 3,
                        fontSize: 11,
                        fontFamily: "monospace",
                        minHeight: 40,
                        boxSizing: "border-box"
                      }}
                    />
                  </div>
                ))}
              </div>
            ))}

            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button
                onClick={async () => {
                  try {
                    const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        sku,
                        updates: editedFields
                      })
                    });
                    const result = await res.json();
                    if (result.success) {
                      alert(`✅ Saved ${result.updated_fields} field(s)`);
                      setEditingDetails(false);
                      // Refresh product details
                      const detailsRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
                      if (detailsRes.ok) {
                        const detailsData = await detailsRes.json();
                        setProductDetails(detailsData);
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
                  padding: "6px 8px",
                  background: "#4CAF50",
                  color: "white",
                  border: "none",
                  borderRadius: 3,
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: "bold"
                }}
              >
                💾 Save
              </button>
              <button
                onClick={() => setEditingDetails(false)}
                style={{
                  flex: 1,
                  padding: "6px 8px",
                  background: "#999",
                  color: "white",
                  border: "none",
                  borderRadius: 3,
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: "bold"
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>    </div>
  );
}
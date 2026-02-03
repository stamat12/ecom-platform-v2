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

  // eBay state
  const [ebayExpanded, setEbayExpanded] = useState(false);
  const [ebaySchema, setEbaySchema] = useState(null);
  const [ebayFields, setEbayFields] = useState(null);
  const [ebayValidation, setEbayValidation] = useState(null);
  const [ebayEnriching, setEbayEnriching] = useState(false);
  const [ebayValidating, setEbayValidating] = useState(false);
  const [ebayLoading, setEbayLoading] = useState(false);
  const [ebayEditingFields, setEbayEditingFields] = useState(false);
  const [ebayEditedFields, setEbayEditedFields] = useState({});
  const [ebaySavingFields, setEbaySavingFields] = useState(false);
  const [ebayListingData, setEbayListingData] = useState({ price: "", quantity: "1", condition: "1000", ean: "" });
  const [ebayCreatingListing, setEbayCreatingListing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ show: false, message: "", step: 0, total: 0 });
  const [modifiedSku, setModifiedSku] = useState("");
  const [scheduleDate, setScheduleDate] = useState("");

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

  // eBay functions
  const loadEbayData = async () => {
    try {
      setEbayLoading(true);
      // Load schema for SKU
      const schemaRes = await fetch(`/api/ebay/schemas/sku/${encodeURIComponent(sku)}`);
      if (schemaRes.ok) {
        const schemaData = await schemaRes.json();
        setEbaySchema(schemaData);
        
        // Load current eBay fields from JSON
        const fieldsRes = await fetch(`/api/ebay/fields/${encodeURIComponent(sku)}`);
        if (fieldsRes.ok) {
          const fieldsData = await fieldsRes.json();
          console.log(`eBay fields for ${sku}:`, fieldsData);
          setEbayFields(fieldsData);
        } else {
          const errorText = await fieldsRes.text();
          console.error(`Failed to load eBay fields for ${sku}:`, fieldsRes.status, errorText);
          // Set placeholder structure so user knows there was an error
          setEbayFields({ 
            success: false, 
            sku: sku, 
            required_fields: {}, 
            optional_fields: {},
            error_message: `Failed to load eBay fields (${fieldsRes.status}): ${errorText}`,
            category: "Error",
            categoryId: null
          });
        }
        
        // Validate
        await validateEbayFields();
      }
    } catch (e) {
      console.error("Failed to load eBay data:", e);
    } finally {
      setEbayLoading(false);
    }
  };

  const validateEbayFields = async () => {
    try {
      setEbayValidating(true);
      const res = await fetch(`/api/ebay/validate/${encodeURIComponent(sku)}`);
      if (res.ok) {
        const data = await res.json();
        setEbayValidation(data);
      }
    } catch (e) {
      console.error("Validation failed:", e);
    } finally {
      setEbayValidating(false);
    }
  };

  const handleEbayEnrich = async () => {
    try {
      setEbayEnriching(true);
      const res = await fetch("/api/ebay/enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, force: false })
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`✅ Enriched ${data.updated_fields} fields`);
        await loadEbayData();
      } else {
        const err = await res.json();
        alert(`❌ ${err.detail || "Enrichment failed"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayEnriching(false);
    }
  };

  const handleEbayCreateListing = async () => {
    if (!ebayListingData.price) {
      alert("Please enter a price");
      return;
    }
    
    if (!confirm(`Create eBay listing for ${sku} at €${ebayListingData.price}?`)) return;
    
    try {
      setEbayCreatingListing(true);
      setUploadProgress({ show: true, message: "Preparing listing data...", step: 1, total: 4 });
      
      await new Promise(resolve => setTimeout(resolve, 300)); // Brief pause for UI
      setUploadProgress({ show: true, message: "Uploading images to eBay...", step: 2, total: 4 });
      
      const requestBody = {
        sku,
        price: parseFloat(ebayListingData.price),
        quantity: parseInt(ebayListingData.quantity),
        condition: ebayListingData.condition
      };
      
      // Add modified SKU if provided
      if (modifiedSku && modifiedSku.trim()) {
        requestBody.ebay_sku = modifiedSku.trim();
      }
      
      // Add schedule days if date provided
      if (scheduleDate) {
        const scheduleDays = Math.ceil((new Date(scheduleDate) - new Date()) / (1000 * 60 * 60 * 24));
        requestBody.schedule_days = Math.max(0, scheduleDays);
      } else {
        requestBody.schedule_days = 0; // Upload immediately
      }
      
      // Add EAN if provided
      if (ebayListingData.ean && ebayListingData.ean.trim()) {
        requestBody.ean = ebayListingData.ean.trim();
      }
      
      const res = await fetch("/api/ebay/listings/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });
      
      setUploadProgress({ show: true, message: "Creating eBay listing...", step: 3, total: 4 });
      
      if (res.ok) {
        const data = await res.json();
        
        // Build detailed message
        let message = `📦 SKU: ${data.sku}\n\n`;
        
        if (data.success) {
          message += `✅ SUCCESS - Listing Created!\n\n`;
          message += `🔗 eBay Item ID: ${data.item_id}\n`;
          message += `📝 Title: ${data.title}\n`;
          message += `💰 Price: €${data.price}\n`;
          message += `📸 Images uploaded: ${data.image_count}\n`;
          message += `📁 Category ID: ${data.category_id}\n`;
          
          if (data.scheduled_time) {
            message += `📅 Scheduled for: ${new Date(data.scheduled_time).toLocaleString('de-DE')}\n`;
          } else {
            message += `📅 Published: Immediately\n`;
          }
          
          if (data.has_manufacturer_info) {
            message += `✅ Manufacturer info included\n`;
          }
          
          // Show warnings if any
          if (data.warnings && data.warnings.length > 0) {
            message += `\n⚠️ WARNINGS (${data.warnings.length}):\n`;
            data.warnings.forEach((warning, idx) => {
              message += `${idx + 1}. ${warning}\n`;
            });
          }
          
          setUploadProgress({ show: true, message: "✅ Listing created successfully!", step: 4, total: 4 });
          await new Promise(resolve => setTimeout(resolve, 1000));
          alert(message);
          window.open(`https://www.ebay.de/itm/${data.item_id}`, "_blank");
        } else {
          // Failed
          message += `❌ FAILED - Listing Not Created\n\n`;
          
          if (data.errors && data.errors.length > 0) {
            message += `❌ ERRORS (${data.errors.length}):\n`;
            data.errors.forEach((error, idx) => {
              message += `${idx + 1}. ${error}\n`;
            });
          } else {
            message += `Error: ${data.message || 'Unknown error'}\n`;
          }
          
          // Show warnings if any
          if (data.warnings && data.warnings.length > 0) {
            message += `\n⚠️ WARNINGS (${data.warnings.length}):\n`;
            data.warnings.forEach((warning, idx) => {
              message += `${idx + 1}. ${warning}\n`;
            });
          }
          
          setUploadProgress({ show: false, message: "", step: 0, total: 0 });
          alert(message);
        }
      } else {
        const err = await res.json();
        setUploadProgress({ show: false, message: "", step: 0, total: 0 });
        alert(`❌ Server Error\n\n${err.detail || "Listing creation failed"}`);
      }
    } catch (e) {
      setUploadProgress({ show: false, message: "", step: 0, total: 0 });
      alert(`Error: ${e.message}`);
    } finally {
      setEbayCreatingListing(false);
      setTimeout(() => setUploadProgress({ show: false, message: "", step: 0, total: 0 }), 2000);
    }
  };

  const handleSaveEbayFields = async () => {
    try {
      setEbaySavingFields(true);
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-fields`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          required_fields: ebayEditedFields.required || {},
          optional_fields: ebayEditedFields.optional || {}
        })
      });
      
      if (res.ok) {
        alert("✅ eBay fields saved!");
        setEbayEditingFields(false);
        setEbayEditedFields({});
        await loadEbayData();
      } else {
        const err = await res.json();
        alert(`❌ ${err.detail || "Failed to save fields"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbaySavingFields(false);
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

        {/* eBay Section */}
        <div style={{ marginTop: 24, borderTop: "2px solid #e0e0e0", paddingTop: 16 }}>
          <button
            onClick={() => {
              setEbayExpanded(!ebayExpanded);
              if (!ebayExpanded && !ebaySchema) loadEbayData();
            }}
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
            <span style={{ fontSize: 18, transform: ebayExpanded ? "rotate(90deg)" : "rotate(0deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
            ⭐ eBay Integration {ebayValidation && `(${ebayValidation.filled_required}/${ebayValidation.total_required})`}
          </button>

          {ebayExpanded && (
            <div>
              {/* Validation Status */}
              {ebayValidation && (
                <div style={{ 
                  marginBottom: 12, 
                  padding: 8, 
                  background: ebayValidation.valid ? "#f0fff4" : "#fff9e6",
                  border: `1px solid ${ebayValidation.valid ? "#28a745" : "#ffc107"}`,
                  borderRadius: 4 
                }}>
                  <div style={{ fontSize: 11, fontWeight: "bold", color: ebayValidation.valid ? "#28a745" : "#f57c00" }}>
                    {ebayValidation.valid ? "✓ Ready for listing" : "⚠ Missing required fields"}
                  </div>
                  <div style={{ fontSize: 10, color: "#666", marginTop: 4 }}>
                    Required: {ebayValidation.filled_required}/{ebayValidation.total_required} | 
                    Optional: {ebayValidation.filled_optional}/{ebayValidation.total_optional}
                  </div>
                  {ebayValidation.missing_required && ebayValidation.missing_required.length > 0 && (
                    <div style={{ fontSize: 10, color: "#d32f2f", marginTop: 6 }}>
                      Missing: {ebayValidation.missing_required.slice(0, 3).join(", ")}
                      {ebayValidation.missing_required.length > 3 && ` +${ebayValidation.missing_required.length - 3} more`}
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                <button
                  onClick={handleEbayEnrich}
                  disabled={ebayEnriching || ebayEditingFields}
                  style={{
                    padding: "8px 12px",
                    fontSize: 12,
                    background: "#28a745",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: (ebayEnriching || ebayEditingFields) ? "not-allowed" : "pointer",
                    fontWeight: "bold"
                  }}
                >
                  {ebayEnriching ? "🤖 Enriching..." : "🤖 Auto-Fill eBay Fields"}
                </button>
                <button
                  onClick={validateEbayFields}
                  disabled={ebayValidating || ebayEditingFields}
                  title="Check if all required eBay fields are filled"
                  style={{
                    padding: "8px 12px",
                    fontSize: 12,
                    background: "#17a2b8",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: (ebayValidating || ebayEditingFields) ? "not-allowed" : "pointer",
                    fontWeight: "bold"
                  }}
                >
                  {ebayValidating ? "Validating..." : "✓ Validate Fields"}
                </button>
                {!ebayEditingFields ? (
                  <button
                    onClick={() => {
                      setEbayEditingFields(true);
                      setEbayEditedFields({
                        required: { ...(ebayFields?.required_fields || {}) },
                        optional: { ...(ebayFields?.optional_fields || {}) }
                      });
                    }}
                    style={{
                      padding: "8px 12px",
                      fontSize: 12,
                      background: "#ff9800",
                      color: "white",
                      border: "none",
                      borderRadius: 4,
                      cursor: "pointer",
                      fontWeight: "bold"
                    }}
                  >
                    ✏️ Edit Fields
                  </button>
                ) : (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={handleSaveEbayFields}
                      disabled={ebaySavingFields}
                      style={{
                        flex: 1,
                        padding: "8px 12px",
                        fontSize: 12,
                        background: "#4CAF50",
                        color: "white",
                        border: "none",
                        borderRadius: 4,
                        cursor: ebaySavingFields ? "not-allowed" : "pointer",
                        fontWeight: "bold"
                      }}
                    >
                      {ebaySavingFields ? "Saving..." : "💾 Save"}
                    </button>
                    <button
                      onClick={() => {
                        setEbayEditingFields(false);
                        setEbayEditedFields({});
                      }}
                      style={{
                        flex: 1,
                        padding: "8px 12px",
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
                )}
              </div>

              {/* Category Info */}
              {ebayFields && (
                <div style={{ marginBottom: 12, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 10 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 4 }}>{ebayFields.category || ebaySchema?.category_name || "No Category"}</div>
                  <div style={{ color: "#666" }}>ID: {ebayFields.categoryId || ebaySchema?.category_id || "N/A"}</div>
                  {ebayFields.error_message && (
                    <div style={{ color: "#d32f2f", marginTop: 4, fontSize: 9 }}>⚠️ {ebayFields.error_message}</div>
                  )}
                </div>
              )}

              {/* Loading State */}
              {ebayLoading && (
                <div style={{ padding: 12, textAlign: "center", color: "#666", fontSize: 11 }}>
                  Loading eBay fields...
                </div>
              )}

              {/* eBay Fields Display */}
              {!ebayLoading && ebayFields && (
                <div style={{ marginBottom: 12, maxHeight: 400, overflow: "auto" }}>
                  {/* Show message if no fields available */}
                  {(!ebayFields.required_fields || Object.keys(ebayFields.required_fields).length === 0) && 
                   (!ebayFields.optional_fields || Object.keys(ebayFields.optional_fields).length === 0) && (
                    <div style={{ padding: 12, background: "#fff9e6", border: "1px solid #ffc107", borderRadius: 4, fontSize: 10, color: "#666", marginBottom: 12 }}>
                      ⚠️ No eBay fields schema loaded. {ebayFields.message || "Please check if the category is set correctly and has a valid schema."}
                    </div>
                  )}
                  {/* Required Fields */}
                  {ebayFields.required_fields && Object.keys(ebayFields.required_fields).length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 10, fontWeight: "bold", color: "#d32f2f", marginBottom: 6 }}>
                        Required Fields
                      </div>
                      {Object.entries(ebayFields.required_fields).map(([name, value]) => (
                        <div key={name} style={{ marginBottom: 6, padding: 6, background: "#fff8f8", borderRadius: 3 }}>
                          <div style={{ fontSize: 9, fontWeight: "600", color: "#d32f2f", marginBottom: 3 }}>{name}</div>
                          {ebayEditingFields ? (
                            <input
                              type="text"
                              value={ebayEditedFields.required?.[name] ?? value}
                              onChange={(e) => setEbayEditedFields(prev => ({
                                ...prev,
                                required: { ...(prev.required || {}), [name]: e.target.value }
                              }))}
                              style={{
                                width: "100%",
                                padding: "4px 6px",
                                fontSize: 9,
                                border: "1px solid #d32f2f",
                                borderRadius: 3,
                                fontFamily: "monospace"
                              }}
                            />
                          ) : (
                            <div style={{ fontSize: 9, color: "#333", marginTop: 2 }}>{value || <em style={{ color: "#999" }}>empty</em>}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Optional Fields */}
                  {ebayFields.optional_fields && Object.keys(ebayFields.optional_fields).length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, fontWeight: "bold", color: "#1976d2", marginBottom: 6 }}>
                        Optional Fields ({Object.keys(ebayFields.optional_fields).length})
                      </div>
                      {Object.entries(ebayFields.optional_fields).map(([name, value]) => (
                        <div key={name} style={{ marginBottom: 6, padding: 6, background: "#f8f8ff", borderRadius: 3 }}>
                          <div style={{ fontSize: 9, fontWeight: "600", color: "#1976d2", marginBottom: 3 }}>{name}</div>
                          {ebayEditingFields ? (
                            <input
                              type="text"
                              value={ebayEditedFields.optional?.[name] ?? value}
                              onChange={(e) => setEbayEditedFields(prev => ({
                                ...prev,
                                optional: { ...(prev.optional || {}), [name]: e.target.value }
                              }))}
                              style={{
                                width: "100%",
                                padding: "4px 6px",
                                fontSize: 9,
                                border: "1px solid #1976d2",
                                borderRadius: 3,
                                fontFamily: "monospace"
                              }}
                            />
                          ) : (
                            <div style={{ fontSize: 9, color: "#333", marginTop: 2 }}>{value || <em style={{ color: "#999" }}>empty</em>}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Create Listing Section */}
              <div style={{ marginTop: 16, borderTop: "1px solid #e0e0e0", paddingTop: 12 }}>
                <div style={{ fontSize: 11, fontWeight: "bold", marginBottom: 8 }}>Create eBay Listing</div>
                
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>Price (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={ebayListingData.price}
                    onChange={(e) => setEbayListingData({...ebayListingData, price: e.target.value})}
                    style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                    placeholder="29.99"
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8, marginBottom: 12 }}>
                  <div>
                    <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>Quantity</label>
                    <input
                      type="number"
                      min="1"
                      value={ebayListingData.quantity}
                      onChange={(e) => setEbayListingData({...ebayListingData, quantity: e.target.value})}
                      style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>Condition</label>
                    <select
                      value={ebayListingData.condition}
                      onChange={(e) => setEbayListingData({...ebayListingData, condition: e.target.value})}
                      style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                    >
                      <option value="">-- Select Condition --</option>
                      <option value="1000">1000 - New</option>
                      <option value="1500">1500 - New other</option>
                      <option value="1750">1750 - New with defects</option>
                      <option value="2000">2000 - Certified Refurbished</option>
                      <option value="2500">2500 - Seller Refurbished</option>
                      <option value="2750">2750 - Like New</option>
                      <option value="3000">3000 - Used</option>
                      <option value="4000">4000 - Very Good</option>
                      <option value="5000">5000 - Good</option>
                      <option value="6000">6000 - Acceptable</option>
                      <option value="7000">7000 - For parts / not working</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>EAN <span style={{ color: "#999", fontWeight: "normal" }}>(opt)</span></label>
                    <input
                      type="text"
                      value={ebayListingData.ean}
                      onChange={(e) => setEbayListingData({...ebayListingData, ean: e.target.value})}
                      style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                      placeholder="e.g. 4005900071439"
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>Modified SKU <span style={{ color: "#999", fontWeight: "normal" }}>(opt)</span></label>
                    <input
                      type="text"
                      value={modifiedSku}
                      onChange={(e) => setModifiedSku(e.target.value)}
                      style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                      placeholder={sku}
                      title={`Default: ${sku}`}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4 }}>Schedule Upload <span style={{ color: "#999", fontWeight: "normal" }}>(optional - leave empty for immediate upload)</span></label>
                  <input
                    type="datetime-local"
                    value={scheduleDate}
                    onChange={(e) => setScheduleDate(e.target.value)}
                    style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #ddd", borderRadius: 3 }}
                  />
                </div>

                {uploadProgress.show && (
                  <div style={{
                    padding: "12px",
                    background: "#f0f8ff",
                    border: "1px solid #4a90e2",
                    borderRadius: 4,
                    marginBottom: 10
                  }}>
                    <div style={{ fontSize: 11, fontWeight: "bold", marginBottom: 6, color: "#2c5282" }}>
                      {uploadProgress.message}
                    </div>
                    <div style={{ background: "#e0e0e0", borderRadius: 10, height: 20, overflow: "hidden" }}>
                      <div style={{
                        background: "linear-gradient(90deg, #4a90e2, #357abd)",
                        height: "100%",
                        width: `${(uploadProgress.step / uploadProgress.total) * 100}%`,
                        transition: "width 0.3s ease",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "white",
                        fontSize: 10,
                        fontWeight: "bold"
                      }}>
                        {uploadProgress.step}/{uploadProgress.total}
                      </div>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleEbayCreateListing}
                  disabled={ebayCreatingListing || !ebayListingData.price}
                  style={{
                    width: "100%",
                    padding: "10px",
                    fontSize: 12,
                    background: "#ff6b00",
                    color: "white",
                    border: "none",
                    borderRadius: 4,
                    cursor: (ebayCreatingListing || !ebayListingData.price) ? "not-allowed" : "pointer",
                    fontWeight: "bold"
                  }}
                >
                  {ebayCreatingListing ? "Creating..." : "📤 Create eBay Listing"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>    </div>
  );
}
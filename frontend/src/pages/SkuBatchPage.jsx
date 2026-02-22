import React, { useEffect, useMemo, useRef, useState } from "react";
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
  const [previewEan, setPreviewEan] = useState(""); // EAN value in preview modal
  const [previewOp, setPreviewOp] = useState(""); // OP value in preview modal
  const [previewSaving, setPreviewSaving] = useState(false); // Saving state for preview modal
  const [rotating, setRotating] = useState({}); // { "sku/filename": true }
  const [jsonStatus, setJsonStatus] = useState({}); // { sku: true/false }
  const [generatingJson, setGeneratingJson] = useState({}); // { sku: true/false }
  const [selectedImages, setSelectedImages] = useState({}); // { sku: [filenames] }
  const [classifying, setClassifying] = useState({});
  const [batchClassifying, setBatchClassifying] = useState(false);
  const [enhancePrompts, setEnhancePrompts] = useState([]); // [{ key, label }]
  const [enhanceModel, setEnhanceModel] = useState("");
  const [geminiModels, setGeminiModels] = useState([]); // Available Gemini models
  const [selectedGeminiModel, setSelectedGeminiModel] = useState(null); // Selected Gemini model
  const [enhanceLoading, setEnhanceLoading] = useState(false);
  const [enhancingImages, setEnhancingImages] = useState({}); // { "sku/filename": boolean }
  const [imagePromptSelection, setImagePromptSelection] = useState({}); // { "sku/filename": promptKey }

  // Product details state
  const [productDetails, setProductDetails] = useState({}); // { sku: ProductDetailResponse }
  const [detailsLoading, setDetailsLoading] = useState({}); // { sku: boolean }
  const [expandedDetails, setExpandedDetails] = useState({}); // { sku: boolean }
  const [editingDetails, setEditingDetails] = useState({}); // { sku: boolean }
  const [editedFieldsState, setEditedFieldsState] = useState({}); // { sku: { category: { field: value } } }
  const [selectedSkusForProductDetailsEdit, setSelectedSkusForProductDetailsEdit] = useState(new Set());
  const [bulkProductDetailsOpen, setBulkProductDetailsOpen] = useState(false);
  const [bulkProductDetailsSaving, setBulkProductDetailsSaving] = useState(false);
  const [bulkProductDetailsEdits, setBulkProductDetailsEdits] = useState({}); // { sku: { fieldName: value } }

  // AI Enrichment state
  const [selectedSkusForEnrichment, setSelectedSkusForEnrichment] = useState(new Set()); // Set of SKUs to enrich
  const [enrichmentInProgress, setEnrichmentInProgress] = useState(false);
  const [enrichmentResults, setEnrichmentResults] = useState(null); // null | { total, succeeded, failed, results }

  // eBay Enrichment state
  const [ebayEnrichmentInProgress, setEbayEnrichmentInProgress] = useState(false);
  const [ebayEnrichmentResults, setEbayEnrichmentResults] = useState(null);

  // eBay listing bulk edit state
  const [selectedSkusForEbayListingEdit, setSelectedSkusForEbayListingEdit] = useState(new Set());
  const [bulkEbayListingOpen, setBulkEbayListingOpen] = useState(false);
  const [bulkEbayListingSaving, setBulkEbayListingSaving] = useState(false);
  const [bulkEbayListingCreating, setBulkEbayListingCreating] = useState(false);

  // eBay state
  const [ebayExpanded, setEbayExpanded] = useState({}); // { sku: boolean }
  const [ebaySchemas, setEbaySchemas] = useState({}); // { sku: schema }
  const [ebayFields, setEbayFields] = useState({}); // { sku: fields }
  const [ebayImageOrders, setEbayImageOrders] = useState({}); // { sku: { filename: order_number } }
  const [ebayValidations, setEbayValidations] = useState({}); // { sku: validation }
  const [ebayEnriching, setEbayEnriching] = useState({}); // { sku: boolean }
  const [ebaySeoEnriching, setEbaySeoEnriching] = useState({}); // { sku: boolean }
  const [ebayEditingFields, setEbayEditingFields] = useState({}); // { sku: boolean }
  const [ebayEditedFields, setEbayEditedFields] = useState({}); // { sku: { required: {}, optional: {} } }
  const [ebaySavingFields, setEbaySavingFields] = useState({}); // { sku: boolean }
  const [ebayListingData, setEbayListingData] = useState({}); // { sku: { price, quantity, condition, ean, modified_sku, schedule_date } }
  const [ebayCreatingListing, setEbayCreatingListing] = useState({}); // { sku: boolean }
  const [ebayConditionNoteLoading, setEbayConditionNoteLoading] = useState({}); // { sku: boolean }
  const [uploadProgress, setUploadProgress] = useState({}); // { sku: { show, message, step, total } }
  const [ebayListingStatus, setEbayListingStatus] = useState({}); // { sku: true/false/null }
  const [ebayCategorySuggestions, setEbayCategorySuggestions] = useState({}); // { sku: [items] }
  const [ebayCategoryLoading, setEbayCategoryLoading] = useState({}); // { sku: boolean }
  const categorySearchTimers = useRef({});

  // eBay subsection expansion state
  const [ebaySubsectionExpanded, setEbaySubsectionExpanded] = useState({}); // { "sku/section": boolean }
  // eBay SEO fields state
  const [ebaySeoFields, setEbaySeoFields] = useState({}); // { sku: { product_type, product_model, keyword_1, keyword_2, keyword_3 } }
  const [ebayEditingSeo, setEbayEditingSeo] = useState({}); // { sku: boolean }
  const [ebaySavingSeo, setEbaySavingSeo] = useState({}); // { sku: boolean }

  // Filter state
  const [showFilters, setShowFilters] = useState(false);
  const [selectedStatusFilters, setSelectedStatusFilters] = useState(new Set());
  const [selectedLagerFilters, setSelectedLagerFilters] = useState(new Set());
  const [selectedBrandFilters, setSelectedBrandFilters] = useState(new Set());
  const [completionFilter, setCompletionFilter] = useState(null); // null | "empty" | "low" | "medium" | "high" | "complete"

  const conditionLabelById = {
    "1000": "New",
    "1500": "New other",
    "1750": "New with defects",
    "2000": "Certified Refurbished",
    "2500": "Seller Refurbished",
    "2750": "Like New",
    "3000": "Used",
    "4000": "Very Good",
    "5000": "Good",
    "6000": "Acceptable",
    "7000": "For parts / not working",
  };

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

  const getPromptKeyForImage = (sku, filename) => {
    const key = `${sku}/${filename}`;
    return imagePromptSelection[key] || enhancePrompts[0]?.key || "";
  };

  const handleEnhanceImage = async (sku, filename) => {
    const promptKey = getPromptKeyForImage(sku, filename);
    if (!promptKey) {
      alert("No enhancement prompt available");
      return;
    }

    const key = `${sku}/${filename}`;
    setEnhancingImages(prev => ({ ...prev, [key]: true }));
    try {
      const res = await fetch("/api/images/enhance-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          images: [{ sku, filename }],
          prompt_key: promptKey,
          upscale: true,
          target_size_mb: 8.0,
          gemini_model: selectedGeminiModel,
        })
      });
      const data = await res.json();
      const hasSuccess = Array.isArray(data.results)
        ? data.results.some((result) => result && result.success)
        : Boolean(data.success);
      if (!res.ok || !hasSuccess) {
        throw new Error(data.detail || data.message || "Enhancement failed");
      }

      const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setItems((prev) =>
          prev.map((item) =>
            item.sku === sku ? { ...item, data: refreshData, error: null } : item
          )
        );
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEnhancingImages(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleDeleteImage = async (sku, filename) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${filename}"?\n\nThis will remove it from both the folder and metadata.`
    );
    
    if (!confirmed) return;

    try {
      const res = await fetch(`/api/images/${encodeURIComponent(sku)}/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || "Delete failed");
      }

      // Refresh the images list
      const refreshRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/images`);
      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setItems((prev) =>
          prev.map((item) =>
            item.sku === sku ? { ...item, data: refreshData, error: null } : item
          )
        );
      }
      
      alert(`Image "${filename}" deleted successfully`);
    } catch (e) {
      alert(`Error deleting image: ${e.message}`);
    }
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

  const handleBulkGenerateMissingJson = async () => {
    const selected = Array.from(selectedSkusForEnrichment);
    if (selected.length === 0) {
      alert("No SKUs selected");
      return;
    }

    const targets = selected.filter((sku) => jsonStatus[sku] === false);
    if (targets.length === 0) {
      alert("All selected SKUs already have JSON");
      return;
    }

    setGeneratingJson((prev) => {
      const next = { ...prev };
      targets.forEach((sku) => {
        next[sku] = true;
      });
      return next;
    });

    const results = await Promise.all(
      targets.map(async (sku) => {
        try {
          const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/json/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          });
          const result = await res.json();
          if (result.success) {
            setJsonStatus((prev) => ({ ...prev, [sku]: true }));
            return { sku, success: true };
          }
          return { sku, success: false, message: result.message || "Failed to create JSON" };
        } catch (e) {
          return { sku, success: false, message: e.message };
        } finally {
          setGeneratingJson((prev) => ({ ...prev, [sku]: false }));
        }
      })
    );

    const failed = results.filter((r) => !r.success);
    if (failed.length > 0) {
      alert(`Generated JSON for ${results.length - failed.length}/${results.length}. Failed: ${failed.length}`);
    } else {
      alert(`Generated JSON for ${results.length} SKU(s).`);
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
    try {
      if (selectedSkus.length > 0) {
        const resListings = await fetch(`/api/skus/ebay-listings/has?skus=${encodeURIComponent(selectedSkus.join(","))}`);
        if (resListings.ok) {
          const listingsData = await resListings.json();
          setEbayListingStatus(listingsData.skus || {});
        }
      }
    } catch (e) {
      console.error("Error loading eBay listing status:", e);
    }

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
        
        // Load eBay image orders for this SKU
        loadEbayImageOrders(sku);
        
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
    if (productDetails[sku]) return productDetails[sku]; // Already loaded, return cached

    setDetailsLoading((prev) => ({ ...prev, [sku]: true }));
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
      if (res.ok) {
        const data = await res.json();
        setProductDetails((prev) => ({ ...prev, [sku]: data }));
        return data;
      }
    } catch (e) {
      console.error(`Failed to load details for ${sku}:`, e);
    } finally {
      setDetailsLoading((prev) => ({ ...prev, [sku]: false }));
    }
    return null;
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

  const getDetailValue = (sku, categoryName, fieldName) => {
    const details = productDetails[sku];
    if (!details?.categories) return "";
    const category = details.categories.find(cat => cat.name === categoryName);
    if (!category?.fields) return "";
    const field = category.fields.find(f => f.name === fieldName);
    return field?.value ?? "";
  };

  const bulkProductDetailFields = [
    { name: "Supplier Title", editable: false },
    { name: "Category", editable: true },
    { name: "Condition", editable: true },
    { name: "Gender", editable: true },
    { name: "Brand", editable: true },
    { name: "Color", editable: true },
    { name: "Size", editable: true },
    { name: "More details", editable: true, multiline: true },
    { name: "Keywords", editable: true, multiline: true },
    { name: "Materials", editable: true, multiline: true },
    { name: "OP", editable: true },
    { name: "Status", editable: true },
    { name: "Lager", editable: true },
  ];

  const findDetailFieldInDetails = (details, fieldName) => {
    if (!details?.categories) return null;
    for (const category of details.categories) {
      if (!Array.isArray(category.fields)) continue;
      const field = category.fields.find((f) => f.name === fieldName);
      if (field) {
        return { categoryName: category.name, value: field.value ?? "" };
      }
    }
    return null;
  };

  const getDetailValueByName = (sku, fieldName) => {
    const details = productDetails[sku];
    const found = findDetailFieldInDetails(details, fieldName);
    return found?.value ?? "";
  };

  // Get unique Status values from all productDetails
  const getAvailableStatusValues = useMemo(() => {
    const statuses = new Set();
    Object.values(productDetails).forEach((details) => {
      if (details?.categories) {
        for (const category of details.categories) {
          if (!Array.isArray(category.fields)) continue;
          const statusField = category.fields.find((f) => f.name === "Status");
          if (statusField?.value) {
            statuses.add(statusField.value);
          }
        }
      }
    });
    // Add "empty" option if some SKUs have no status
    const allSkusHaveStatus = items.every(item => {
      const status = getDetailValueByName(item.sku, "Status");
      return status && status.trim() !== "";
    });
    if (!allSkusHaveStatus) {
      statuses.add("empty");
    }
    return Array.from(statuses).sort();
  }, [productDetails, items]);

  // Get unique values for a field
  const getAvailableFieldValues = (fieldName) => {
    const values = new Set();
    Object.values(productDetails).forEach((details) => {
      if (details?.categories) {
        for (const category of details.categories) {
          if (!Array.isArray(category.fields)) continue;
          const field = category.fields.find((f) => f.name === fieldName);
          if (field?.value) {
            values.add(field.value);
          }
        }
      }
    });
    return Array.from(values).sort();
  };

  // Get available Lager values
  const getAvailableLagerValues = useMemo(() => {
    return getAvailableFieldValues("Lager");
  }, [productDetails]);

  // Get available Brand values
  const getAvailableBrandValues = useMemo(() => {
    return getAvailableFieldValues("Brand");
  }, [productDetails]);

  // Check if SKU passes current filters
  const passesFilters = (sku) => {
    // Status filter
    if (selectedStatusFilters.size > 0) {
      const status = getDetailValueByName(sku, "Status") || "empty";
      if (!selectedStatusFilters.has(status)) {
        return false;
      }
    }

    // Lager filter
    if (selectedLagerFilters && selectedLagerFilters.size > 0) {
      const lager = getDetailValueByName(sku, "Lager") || "empty";
      if (!selectedLagerFilters.has(lager)) {
        return false;
      }
    }

    // Brand filter
    if (selectedBrandFilters && selectedBrandFilters.size > 0) {
      const brand = getDetailValueByName(sku, "Brand") || "empty";
      if (!selectedBrandFilters.has(brand)) {
        return false;
      }
    }

    // Completion filter
    if (completionFilter !== null) {
      const completion = productDetails[sku]?.completion_percentage || 0;
      switch (completionFilter) {
        case "empty":
          if (completion !== 0) return false;
          break;
        case "low":
          if (completion === 0 || completion >= 33) return false;
          break;
        case "medium":
          if (completion < 33 || completion >= 66) return false;
          break;
        case "high":
          if (completion < 66 || completion === 100) return false;
          break;
        case "complete":
          if (completion !== 100) return false;
          break;
        default:
          break;
      }
    }

    return true;
  };

  // Filter items based on current filters
  const filteredItems = useMemo(() => {
    if (selectedStatusFilters.size === 0 && selectedLagerFilters.size === 0 && selectedBrandFilters.size === 0 && completionFilter === null) {
      return items;
    }
    return items.filter((item) => passesFilters(item.sku));
  }, [items, selectedStatusFilters, selectedLagerFilters, selectedBrandFilters, completionFilter, productDetails]);

  const applyProductCategorySelection = (sku, item) => {
    setBulkProductDetailsEdits((prev) => {
      const updates = { ...(prev[sku] || {}) };
      updates.Category = item.label || "";

      const details = productDetails[sku];
      if (details?.categories) {
        const categoryWithField = details.categories.find(cat =>
          Array.isArray(cat.fields) && cat.fields.some(f => f.name === "Category")
        );
        const idField = categoryWithField?.fields?.find((f) => {
          const n = String(f.name || "").toLowerCase();
          return n.includes("category") && n.includes("id");
        });
        if (idField && item.category_id) {
          updates[idField.name] = String(item.category_id);
        }
      }

      return { ...prev, [sku]: updates };
    });
    setEbayCategorySuggestions((prev) => ({ ...prev, [sku]: [] }));
  };

  const openImagePreview = (sku, img, context = "bulk") => {
    const allImages = items.find(item => item.sku === sku)?.data?.images || [];
    const startIndex = allImages.findIndex((i) => i.filename === img?.filename);
    setPreview({
      sku,
      img,
      images: allImages,
      index: startIndex >= 0 ? startIndex : 0,
      context,
    });
  };

  const toNumber = (value) => {
    if (value === null || value === undefined) return 0;
    const cleaned = String(value).replace(/[^0-9,.-]/g, "").replace(",", ".");
    const parsed = parseFloat(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const searchEbayCategories = (sku, query) => {
    const q = String(query || "").trim();
    if (categorySearchTimers.current[sku]) {
      clearTimeout(categorySearchTimers.current[sku]);
    }
    if (q.length < 2) {
      setEbayCategorySuggestions((prev) => ({ ...prev, [sku]: [] }));
      return;
    }
    categorySearchTimers.current[sku] = setTimeout(async () => {
      setEbayCategoryLoading((prev) => ({ ...prev, [sku]: true }));
      try {
        const res = await fetch(`/api/ebay/categories/search?query=${encodeURIComponent(q)}&limit=25`);
        if (res.ok) {
          const data = await res.json();
          setEbayCategorySuggestions((prev) => ({ ...prev, [sku]: data.items || [] }));
        }
      } catch (e) {
        console.error("Error searching eBay categories:", e);
      } finally {
        setEbayCategoryLoading((prev) => ({ ...prev, [sku]: false }));
      }
    }, 250);
  };

  const applyEbayCategorySelection = (sku, categoryName, fieldName, item) => {
    setEditedFieldsState((prev) => {
      const current = prev[sku] || {};
      const categoryFields = current[categoryName] || {};
      const updated = {
        ...current,
        [categoryName]: {
          ...categoryFields,
          [fieldName]: item.label || "",
        },
      };

      const idField = Object.keys(categoryFields).find((name) => {
        const n = name.toLowerCase();
        return n.includes("category") && n.includes("id");
      });
      if (idField && item.category_id) {
        updated[categoryName][idField] = item.category_id;
      }

      return { ...prev, [sku]: updated };
    });
    setEbayCategorySuggestions((prev) => ({ ...prev, [sku]: [] }));
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

  const toggleSkuForEbayListingEdit = (sku) => {
    const newSet = new Set(selectedSkusForEbayListingEdit);
    if (newSet.has(sku)) {
      newSet.delete(sku);
    } else {
      newSet.add(sku);
    }
    setSelectedSkusForEbayListingEdit(newSet);
  };

  const toggleSkuForProductDetailsEdit = (sku) => {
    const newSet = new Set(selectedSkusForProductDetailsEdit);
    if (newSet.has(sku)) {
      newSet.delete(sku);
    } else {
      newSet.add(sku);
    }
    setSelectedSkusForProductDetailsEdit(newSet);
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

  const handleEbayEnrichAll = async () => {
    if (selectedSkusForEnrichment.size === 0) {
      alert("No SKUs selected for eBay enrichment");
      return;
    }

    setEbayEnrichmentInProgress(true);
    const results = {};
    let succeeded = 0;
    let failed = 0;

    try {
      for (const sku of selectedSkusForEnrichment) {
        try {
          const res = await fetch(`/api/ebay/enrich`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sku }),
          });
          const result = await res.json();
          
          if (res.ok && result.required_fields) {
            results[sku] = { success: true, message: "Enriched" };
            succeeded++;
          } else {
            results[sku] = { success: false, message: result.detail || "Failed" };
            failed++;
          }
        } catch (e) {
          results[sku] = { success: false, message: e.message };
          failed++;
        }
      }

      setEbayEnrichmentResults({ total: selectedSkusForEnrichment.size, succeeded, failed, results, mode: "fields" });
      setTimeout(() => setEbayEnrichmentResults(null), 10000);
      setSelectedSkusForEnrichment(new Set());
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayEnrichmentInProgress(false);
    }
  };

  const handleEbaySeoEnrichAll = async () => {
    if (selectedSkusForEnrichment.size === 0) {
      alert("No SKUs selected for eBay SEO enrichment");
      return;
    }

    setEbayEnrichmentInProgress(true);
    const results = {};
    let succeeded = 0;
    let failed = 0;

    try {
      for (const sku of selectedSkusForEnrichment) {
        try {
          const res = await fetch(`/api/ebay/enrich-seo`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sku }),
          });
          const result = await res.json();

          if (res.ok && result.success) {
            results[sku] = { success: true, message: `SEO +${result.updated_seo_fields || 0}` };
            succeeded++;
          } else {
            results[sku] = { success: false, message: result.detail || "Failed" };
            failed++;
          }
        } catch (e) {
          results[sku] = { success: false, message: e.message };
          failed++;
        }
      }

      setEbayEnrichmentResults({ total: selectedSkusForEnrichment.size, succeeded, failed, results, mode: "seo" });
      setTimeout(() => setEbayEnrichmentResults(null), 10000);
      setSelectedSkusForEnrichment(new Set());
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayEnrichmentInProgress(false);
    }
  };

  const loadEbayListingData = async (sku) => {
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-listing`);
      if (res.ok) {
        const data = await res.json();
        if (data?.data) {
          setEbayListingData((prev) => ({
            ...prev,
            [sku]: {
              ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }),
              ...data.data,
            },
          }));
        }
      }
    } catch (e) {
      console.error("Failed to load eBay listing data:", e);
    }
  };

  const handleBulkEbayListingSaveTable = async () => {
    const skus = Array.from(selectedSkusForEbayListingEdit);
    if (skus.length === 0) {
      alert("No SKUs selected for bulk listing edit");
      return;
    }

    const listings = {};
    skus.forEach((sku) => {
      const listingData = ebayListingData[sku] || {};
      listings[sku] = {
        price: listingData.price ?? "",
        shipping_costs_net: listingData.shipping_costs_net ?? "",
        quantity: listingData.quantity ?? "",
        condition_id: listingData.condition_id ?? "",
        condition_description: listingData.condition_description ?? "",
        ean: listingData.ean ?? "",
        modified_sku: listingData.modified_sku ?? "",
        schedule_date: listingData.schedule_date ?? "",
      };
    });

    try {
      setBulkEbayListingSaving(true);
      const res = await fetch("/api/ebay/listing/bulk-save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listings }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Bulk save failed");
      }

      await Promise.all(skus.map((sku) => loadEbayListingData(sku)));
      setBulkEbayListingOpen(false);
      alert("✅ Bulk listing fields saved");
    } catch (e) {
      alert(`❌ ${e.message}`);
    } finally {
      setBulkEbayListingSaving(false);
    }
  };

  const handleBulkEbayCreateListings = async () => {
    const skus = Array.from(selectedSkusForEbayListingEdit);
    if (skus.length === 0) {
      alert("No SKUs selected for bulk listing creation");
      return;
    }

    const listings = [];
    const missingPrice = [];

    skus.forEach((sku) => {
      const listingData = ebayListingData[sku] || {};
      if (!listingData.price) {
        missingPrice.push(sku);
        return;
      }

      let conditionId = listingData.condition_id || listingData.condition || "1000";
      if (typeof conditionId === "string") {
        conditionId = conditionId.trim();
      }
      conditionId = parseInt(conditionId, 10);
      if (Number.isNaN(conditionId)) {
        conditionId = 1000;
      }

      const requestBody = {
        sku,
        price: parseFloat(listingData.price),
        quantity: parseInt(listingData.quantity || "1"),
        condition_id: conditionId,
        schedule_days: 0,
      };

      if (listingData.condition_description && listingData.condition_description.trim()) {
        requestBody.condition_description = listingData.condition_description.trim();
      }
      if (listingData.modified_sku && listingData.modified_sku.trim()) {
        requestBody.ebay_sku = listingData.modified_sku.trim();
      }
      if (listingData.schedule_date) {
        const scheduleDays = Math.ceil((new Date(listingData.schedule_date) - new Date()) / (1000 * 60 * 60 * 24));
        requestBody.schedule_days = Math.max(0, scheduleDays);
      }
      if (listingData.ean && listingData.ean.trim()) {
        requestBody.ean = listingData.ean.trim();
      }

      listings.push(requestBody);
    });

    if (missingPrice.length > 0) {
      alert(`Missing price for: ${missingPrice.join(", ")}`);
      return;
    }

    if (!confirm(`Create ${listings.length} eBay listings now?`)) return;

    setBulkEbayListingCreating(true);
    try {
      const res = await fetch("/api/ebay/listings/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ listings })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Batch create failed");
      }

      const data = await res.json();
      alert(`✅ Created ${data.successful_count} listings, ${data.failed_count} failed`);
    } catch (e) {
      alert(`❌ ${e.message}`);
    } finally {
      setBulkEbayListingCreating(false);
    }
  };

  const handleBulkEbayListingSaveAndCreate = async () => {
    // First save all changes
    await handleBulkEbayListingSaveTable();
    // Then immediately create listings with the saved data
    setTimeout(() => handleBulkEbayCreateListings(), 500);
  };

  const handleBulkProductDetailsSave = async () => {
    const skus = Array.from(selectedSkusForProductDetailsEdit);
    if (skus.length === 0) {
      alert("No SKUs selected for bulk product details edit");
      return;
    }

    setBulkProductDetailsSaving(true);
    let succeeded = 0;
    let failed = 0;
    const missingFieldsBySku = {};

    for (const sku of skus) {
      const details = productDetails[sku] || await loadProductDetails(sku);
      if (!details) {
        failed++;
        continue;
      }

      const updates = {};
      const missingFields = [];

      bulkProductDetailFields.filter(field => field.editable).forEach((field) => {
        const editedValue = bulkProductDetailsEdits[sku]?.[field.name];
        const found = findDetailFieldInDetails(details, field.name);
        if (!found?.categoryName) {
          missingFields.push(field.name);
          return;
        }
        if (!updates[found.categoryName]) updates[found.categoryName] = {};
        updates[found.categoryName][field.name] = editedValue ?? "";
      });

      if (missingFields.length > 0) {
        missingFieldsBySku[sku] = missingFields;
      }

      if (Object.keys(updates).length === 0) {
        failed++;
        continue;
      }

      try {
        const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sku, updates })
        });
        const result = await res.json();
        if (res.ok && result.success) {
          succeeded++;
          const detailsRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
          if (detailsRes.ok) {
            const detailsData = await detailsRes.json();
            setProductDetails(prev => ({ ...prev, [sku]: detailsData }));
          }
        } else {
          failed++;
        }
      } catch (e) {
        failed++;
      }
    }

    setBulkProductDetailsSaving(false);
    if (Object.keys(missingFieldsBySku).length > 0) {
      const message = Object.entries(missingFieldsBySku)
        .map(([sku, fields]) => `${sku}: ${fields.join(", ")}`)
        .join("\n");
      alert(`Missing fields in Product Details schema:\n${message}`);
    }
    alert(`✅ Saved product details for ${succeeded} SKU(s). ${failed} failed.`);
    setBulkProductDetailsOpen(false);
  };

  useEffect(() => {
    if (!bulkEbayListingOpen) return;
    const skus = Array.from(selectedSkusForEbayListingEdit);
    skus.forEach((sku) => {
      // Load listing data
      loadEbayListingData(sku);
      // Load product details for cost and OP calculations
      loadProductDetails(sku);
      // Load eBay image orders for validation
      loadEbayImageOrders(sku);
      // Load eBay schema for fee information
      const cacheBust = Date.now();
      fetch(`/api/ebay/schemas/sku/${encodeURIComponent(sku)}?t=${cacheBust}`)
        .then(res => res.ok ? res.json() : null)
        .then(schemaData => {
          if (schemaData) {
            setEbaySchemas(prev => ({ ...prev, [sku]: schemaData }));
          }
        })
        .catch(e => console.error("Failed to load schema:", e));
    });
  }, [bulkEbayListingOpen, selectedSkusForEbayListingEdit]);

  useEffect(() => {
    if (!bulkProductDetailsOpen) return;
    const skus = Array.from(selectedSkusForProductDetailsEdit);
    const init = async () => {
      for (const sku of skus) {
        const details = await loadProductDetails(sku);
        loadEbayImageOrders(sku);
        if (details) {
          const fieldMap = {};
          bulkProductDetailFields.forEach((field) => {
            const found = findDetailFieldInDetails(details, field.name);
            fieldMap[field.name] = found?.value ?? "";
          });
          setBulkProductDetailsEdits((prev) => ({
            ...prev,
            [sku]: { ...(prev[sku] || {}), ...fieldMap }
          }));
        }
      }
    };
    init();
  }, [bulkProductDetailsOpen, selectedSkusForProductDetailsEdit]);

  // eBay functions
  const loadEbayData = async (sku) => {
    try {
      // Load product details first (needed for Total Cost Net and OP calculations)
      await loadProductDetails(sku);
      
      // Load eBay image orders
      await loadEbayImageOrders(sku);

      // Load eBay listing draft data
      await loadEbayListingData(sku);
      
      // Load eBay SEO fields
      await loadEbaySeoFields(sku);
      
      // Load schema for SKU (with cache bust)
      const cacheBust = Date.now();
      const schemaRes = await fetch(`/api/ebay/schemas/sku/${encodeURIComponent(sku)}?t=${cacheBust}`);
      if (schemaRes.ok) {
        const schemaData = await schemaRes.json();
        setEbaySchemas(prev => ({ ...prev, [sku]: schemaData }));
        
        // Load current eBay fields from JSON (with cache bust)
        const fieldsRes = await fetch(`/api/ebay/fields/${encodeURIComponent(sku)}?t=${cacheBust}`);
        if (fieldsRes.ok) {
          const fieldsData = await fieldsRes.json();
          console.log(`eBay fields for ${sku}:`, fieldsData);
          console.log(`  - has required_fields: ${!!fieldsData.required_fields}`);
          console.log(`  - required_fields keys: ${fieldsData.required_fields ? Object.keys(fieldsData.required_fields).length : 0}`);
          console.log(`  - has optional_fields: ${!!fieldsData.optional_fields}`);
          console.log(`  - optional_fields keys: ${fieldsData.optional_fields ? Object.keys(fieldsData.optional_fields).length : 0}`);
          setEbayFields(prev => ({ ...prev, [sku]: fieldsData }));
        } else {
          const errorText = await fieldsRes.text();
          console.error(`Failed to load eBay fields for ${sku}:`, fieldsRes.status, errorText);
          // Set placeholder structure so user knows there was an error
          setEbayFields(prev => ({ 
            ...prev, 
            [sku]: { 
              success: false, 
              sku: sku, 
              required_fields: {}, 
              optional_fields: {},
              error_message: `Failed to load eBay fields (${fieldsRes.status}): ${errorText}`,
              category: "Error",
              categoryId: null
            } 
          }));
        }
        
        // Validate
        await validateEbayFields(sku);
      }
    } catch (e) {
      console.error("Failed to load eBay data:", e);
    }
  };

  const validateEbayFields = async (sku) => {
    try {
      const res = await fetch(`/api/ebay/validate/${encodeURIComponent(sku)}`);
      if (res.ok) {
        const data = await res.json();
        setEbayValidations(prev => ({ ...prev, [sku]: data }));
      }
    } catch (e) {
      console.error("Validation failed:", e);
    }
  };

  const handleEbayImageOrderClick = async (sku, filename, orderNumber) => {
    try {
      const currentOrders = ebayImageOrders[sku] || {};
      
      // If this image already has this order, remove it
      if (currentOrders[filename] === orderNumber) {
        const updated = { ...currentOrders };
        delete updated[filename];
        setEbayImageOrders(prev => ({ ...prev, [sku]: updated }));
        
        // Save to backend
        await saveEbayImageOrders(sku, updated);
      } else {
        // Check if another image has this order number
        const existingFilename = Object.keys(currentOrders).find(fn => currentOrders[fn] === orderNumber);
        
        const updated = { ...currentOrders };
        // Remove order from other image if exists
        if (existingFilename) {
          delete updated[existingFilename];
        }
        // Assign order to this image
        updated[filename] = orderNumber;
        
        setEbayImageOrders(prev => ({ ...prev, [sku]: updated }));
        
        // Save to backend
        await saveEbayImageOrders(sku, updated);
      }
    } catch (e) {
      console.error("Failed to update eBay image order:", e);
      alert(`Error: ${e.message}`);
    }
  };

  const saveEbayImageOrders = async (sku, orders) => {
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-images`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ orders })
      });
      
      if (!res.ok) {
        throw new Error(`Failed to save eBay image orders: ${res.status}`);
      }
    } catch (e) {
      console.error("Failed to save eBay image orders:", e);
      throw e;
    }
  };

  const loadEbayImageOrders = async (sku) => {
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-images`);
      if (res.ok) {
        const data = await res.json();
        setEbayImageOrders(prev => ({ ...prev, [sku]: data.orders || {} }));
      }
    } catch (e) {
      console.error("Failed to load eBay image orders:", e);
    }
  };

  const handleEbayEnrich = async (sku) => {
    try {
      setEbayEnriching(prev => ({ ...prev, [sku]: true }));
      const res = await fetch("/api/ebay/enrich", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, force: false })
      });
      
      if (res.ok) {
        const data = await res.json();
        alert(`✅ ${sku}: Enriched ${data.updated_fields} fields`);
        // Give the backend a moment to write the file
        await new Promise(resolve => setTimeout(resolve, 500));
        await loadEbayData(sku);
      } else {
        const err = await res.json();
        alert(`❌ ${sku}: ${err.detail || "Enrichment failed"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayEnriching(prev => ({ ...prev, [sku]: false }));
    }
  };

  const handleEbaySeoEnrich = async (sku) => {
    try {
      setEbaySeoEnriching(prev => ({ ...prev, [sku]: true }));
      const res = await fetch("/api/ebay/enrich-seo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sku, force: false })
      });

      if (res.ok) {
        const data = await res.json();
        alert(`✅ ${sku}: SEO enriched (${data.updated_seo_fields || 0} fields)`);
        await new Promise(resolve => setTimeout(resolve, 300));
        await loadEbaySeoFields(sku);
      } else {
        const err = await res.json();
        alert(`❌ ${sku}: ${err.detail || "SEO enrichment failed"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbaySeoEnriching(prev => ({ ...prev, [sku]: false }));
    }
  };

  const handleConditionNoteAi = async (sku) => {
    const listingData = ebayListingData[sku] || {};
    let conditionId = listingData.condition_id || listingData.condition || "1000";
    if (typeof conditionId === "string") {
      conditionId = conditionId.trim();
    }
    conditionId = parseInt(conditionId, 10);
    if (Number.isNaN(conditionId)) {
      conditionId = 1000;
    }

    try {
      setEbayConditionNoteLoading(prev => ({ ...prev, [sku]: true }));
      const res = await fetch("/api/ebay/condition-note", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          condition_id: conditionId,
          condition_label: conditionLabelById[String(conditionId)] || "",
          existing_description: listingData.condition_description || "",
        })
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || "AI generation failed");
      }

      setEbayListingData(prev => ({
        ...prev,
        [sku]: {
          ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }),
          condition_description: data.condition_description || "",
        }
      }));
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayConditionNoteLoading(prev => ({ ...prev, [sku]: false }));
    }
  };

  const handleEbayCreateListing = async (sku) => {
    const listingData = ebayListingData[sku] || {};
    if (!listingData.price) {
      alert("Please enter a price");
      return;
    }
    
    if (!confirm(`Create eBay listing for ${sku} at €${listingData.price}?`)) return;
    
    try {
      setEbayCreatingListing(prev => ({ ...prev, [sku]: true }));
      setUploadProgress(prev => ({ ...prev, [sku]: { show: true, message: "Preparing listing data...", step: 1, total: 4 } }));
      
      await new Promise(resolve => setTimeout(resolve, 300));
      setUploadProgress(prev => ({ ...prev, [sku]: { show: true, message: "Uploading images to eBay...", step: 2, total: 4 } }));
      
      let conditionId = listingData.condition_id || listingData.condition || "1000";
      if (typeof conditionId === "string") {
        conditionId = conditionId.trim();
      }
      conditionId = parseInt(conditionId, 10);
      if (Number.isNaN(conditionId)) {
        conditionId = 1000;
      }

      const requestBody = {
        sku,
        price: parseFloat(listingData.price),
        quantity: parseInt(listingData.quantity || "1"),
        condition_id: conditionId
      };

      if (listingData.condition_description && listingData.condition_description.trim()) {
        requestBody.condition_description = listingData.condition_description.trim();
      }
      
      // Add modified SKU if provided
      if (listingData.modified_sku && listingData.modified_sku.trim()) {
        requestBody.ebay_sku = listingData.modified_sku.trim();
      }
      
      // Add schedule days if date provided
      if (listingData.schedule_date) {
        const scheduleDays = Math.ceil((new Date(listingData.schedule_date) - new Date()) / (1000 * 60 * 60 * 24));
        requestBody.schedule_days = Math.max(0, scheduleDays);
      } else {
        requestBody.schedule_days = 0; // Upload immediately
      }
      
      // Add EAN if provided
      if (listingData.ean && listingData.ean.trim()) {
        requestBody.ean = listingData.ean.trim();
      }
      
      const res = await fetch("/api/ebay/listings/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });
      
      setUploadProgress(prev => ({ ...prev, [sku]: { show: true, message: "Creating eBay listing...", step: 3, total: 4 } }));
      
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
          
          setUploadProgress(prev => ({ ...prev, [sku]: { show: true, message: "✅ Listing created successfully!", step: 4, total: 4 } }));
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
          
          setUploadProgress(prev => ({ ...prev, [sku]: { show: false, message: "", step: 0, total: 0 } }));
          alert(message);
        }
      } else {
        const err = await res.json();
        setUploadProgress(prev => ({ ...prev, [sku]: { show: false, message: "", step: 0, total: 0 } }));
        alert(`❌ Server Error\n\n${err.detail || "Listing creation failed"}`);
      }
    } catch (e) {
      setUploadProgress(prev => ({ ...prev, [sku]: { show: false, message: "", step: 0, total: 0 } }));
      alert(`Error: ${e.message}`);
    } finally {
      setEbayCreatingListing(prev => ({ ...prev, [sku]: false }));
      setTimeout(() => {
        setUploadProgress(prev => ({ ...prev, [sku]: { show: false, message: "", step: 0, total: 0 } }));
      }, 2000);
    }
  };

  const handleSaveEbayFields = async (sku) => {
    try {
      setEbaySavingFields(prev => ({ ...prev, [sku]: true }));
      
      // Extract just the values from the edited fields
      const extractValues = (fields) => {
        const values = {};
        for (const [key, field] of Object.entries(fields)) {
          // If it's an object with a 'value' property, extract the value
          if (field && typeof field === 'object' && 'value' in field) {
            values[key] = field.value;
          } else {
            // Otherwise use it directly
            values[key] = field;
          }
        }
        return values;
      };
      
      const requiredValues = extractValues(ebayEditedFields[sku]?.required || {});
      const optionalValues = extractValues(ebayEditedFields[sku]?.optional || {});
      
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-fields`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          required_fields: requiredValues,
          optional_fields: optionalValues
        })
      });
      
      if (res.ok) {
        alert(`✅ ${sku}: eBay fields saved!`);
        setEbayEditingFields(prev => ({ ...prev, [sku]: false }));
        setEbayEditedFields(prev => {
          const newState = { ...prev };
          delete newState[sku];
          return newState;
        });
        await loadEbayData(sku);
      } else {
        const err = await res.json();
        alert(`❌ ${err.detail || "Failed to save fields"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbaySavingFields(prev => ({ ...prev, [sku]: false }));
    }
  };

  const loadEbaySeoFields = async (sku) => {
    try {
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-seo?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        setEbaySeoFields(prev => ({ ...prev, [sku]: data }));
      } else {
        // Initialize with empty fields if not found
        setEbaySeoFields(prev => ({ ...prev, [sku]: { product_type: "", product_model: "", keyword_1: "", keyword_2: "", keyword_3: "" } }));
      }
    } catch (e) {
      console.error("Failed to load eBay SEO fields:", e);
    }
  };

  const handleSaveEbaySeoFields = async (sku) => {
    try {
      setEbaySavingSeo(prev => ({ ...prev, [sku]: true }));
      const currentData = ebaySeoFields[sku] || {};
      
      const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/ebay-seo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_type: currentData.product_type || "",
          product_model: currentData.product_model || "",
          keyword_1: currentData.keyword_1 || "",
          keyword_2: currentData.keyword_2 || "",
          keyword_3: currentData.keyword_3 || ""
        })
      });
      
      if (res.ok) {
        alert(`✅ ${sku}: eBay SEO fields saved!`);
        setEbayEditingSeo(prev => ({ ...prev, [sku]: false }));
      } else {
        const err = await res.json();
        alert(`❌ ${err.detail || "Failed to save SEO fields"}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbaySavingSeo(prev => ({ ...prev, [sku]: false }));
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

  useEffect(() => {
    let cancelled = false;
    async function loadPrompts() {
      setEnhanceLoading(true);
      try {
        const [promptsRes, modelsRes] = await Promise.all([
          fetch("/api/images/enhance/prompts"),
          fetch("/api/images/enhance/models"),
        ]);
        
        if (promptsRes.ok) {
          const data = await promptsRes.json();
          if (!cancelled) {
            setEnhanceModel(data.model || "");
            setEnhancePrompts(data.prompts || []);
          }
        }
        
        if (modelsRes.ok) {
          const data = await modelsRes.json();
          if (!cancelled) {
            setGeminiModels(data.models || []);
            // Set first model as default
            if (data.models && data.models.length > 0) {
              setSelectedGeminiModel(data.models[0].id);
            }
          }
        }
      } finally {
        if (!cancelled) setEnhanceLoading(false);
      }
    }
    loadPrompts();
    return () => {
      cancelled = true;
    };
  }, []);

  // Preload product details for all SKUs to populate filters
  useEffect(() => {
    if (items.length === 0) return;
    items.forEach(item => {
      if (!productDetails[item.sku]) {
        loadProductDetails(item.sku);
      }
    });
  }, [items]);

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

  // Calculate top padding for fixed ribbons
  const topPadding = (() => {
    const hasImageRibbon = totalSelectedImages > 0;
    const hasEnrichmentRibbon = selectedSkusForEnrichment.size > 0;
    const hasProductDetailsRibbon = selectedSkusForProductDetailsEdit.size > 0;
    const hasEbayListingRibbon = selectedSkusForEbayListingEdit.size > 0;

    const ribbonCount = [hasImageRibbon, hasEnrichmentRibbon, hasProductDetailsRibbon, hasEbayListingRibbon].filter(Boolean).length;
    return ribbonCount * 50;
  })();

  return (
    <div style={{ width: "100%", maxWidth: "2200px", margin: "0 auto", padding: "0 16px", boxSizing: "border-box", paddingTop: topPadding, transition: "padding-top 0.2s ease" }}>
      <Modal open={bulkEbayListingOpen} onClose={() => setBulkEbayListingOpen(false)}>
        <div style={{ width: "95vw", maxWidth: "1400px" }}>
          <div style={{ fontSize: 16, fontWeight: "bold", marginBottom: 8 }}>Bulk Edit eBay Listing Fields</div>
          <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
            Edit prices, shipping, quantities, conditions, and other fields for {selectedSkusForEbayListingEdit.size} selected SKU(s)
          </div>

          {/* Warning for SKUs without eBay image orders */}
          {(() => {
            const skusWithoutImages = Array.from(selectedSkusForEbayListingEdit).filter(sku => {
              const ebayImages = ebayImageOrders[sku] || {};
              return Object.keys(ebayImages).length === 0;
            });
            return skusWithoutImages.length > 0 ? (
              <div style={{ padding: 10, background: "#ffebee", border: "1px solid #ef5350", borderRadius: 4, marginBottom: 12, color: "#d32f2f", fontSize: 11 }}>
                <span style={{ fontWeight: "bold" }}>⚠️ {skusWithoutImages.length} SKU(s) without eBay image orders:</span> {skusWithoutImages.join(", ")} — These images have not been marked with eBay sequence numbers yet.
              </div>
            ) : null;
          })()}

          <div style={{ overflowX: "auto", marginBottom: 12, border: "1px solid #e0e0e0", borderRadius: 6, maxHeight: "65vh", overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr style={{ background: "#f5f5f5", borderBottom: "2px solid #e0e0e0", position: "sticky", top: 0 }}>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", minWidth: 80 }}>Image</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>SKU</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", background: "#f0f8ff" }}>Total Cost</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", background: "#f0f8ff" }}>OP</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", background: "#f0f8ff" }}>Fee</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", background: "#f0f8ff" }}>Comm%</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", color: "#1976d2" }}>Price</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", color: "#1976d2" }}>Shipping</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", color: "#2e7d32" }}>Net Profit</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", color: "#2e7d32" }}>Margin%</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Qty</th>
                  <th style={{ padding: 6, textAlign: "center", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Cond</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Cond Note</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>EAN</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Mod SKU</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", whiteSpace: "nowrap" }}>Schedule</th>
                </tr>
              </thead>
              <tbody>
                {Array.from(selectedSkusForEbayListingEdit).map((sku) => {
                  const listingData = ebayListingData[sku] || {};
                  const totalCostNet = toNumber(getDetailValue(sku, "Price Data", "Total Cost Net"));
                  const opValue = toNumber(getDetailValue(sku, "OP", "OP"));
                  const fees = ebaySchemas[sku]?.metadata?.fees || {};
                  const paymentFee = toNumber(fees.payment_fee);
                  const salesCommission = toNumber(fees.sales_commission_percentage);
                  const sellingPrice = toNumber(listingData.price || 0);
                  const shippingCosts = toNumber(listingData.shipping_costs_net || 0);
                  const netProfit = (sellingPrice / 1.19) - (sellingPrice * salesCommission) - paymentFee - shippingCosts - totalCostNet;
                  const netProfitMargin = totalCostNet > 0 ? (netProfit / totalCostNet) * 100 : 0;
                  
                  // Check if SKU has images with eBay order numbers
                  const ebayImages = ebayImageOrders[sku] || {};
                  const hasValidImages = Object.keys(ebayImages).length > 0;
                  const firstImagePath = items.find(item => item.sku === sku)?.data?.images?.[0]?.filename;
                  const allImages = items.find(item => item.sku === sku)?.data?.images || [];
                  
                  // Find image with eBay order 1
                  const ebayOrders = ebayImageOrders[sku] || {};
                  const imageWithOrder1 = allImages.find(img => ebayOrders[img.filename] === 1);
                  const displayImage = imageWithOrder1 || allImages[0]; // Fallback to first image
                  
                  return (
                    <tr key={sku} style={{ borderBottom: "1px solid #e0e0e0", background: hasValidImages ? "white" : "#fff8f8" }}>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center" }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                          {displayImage?.thumb_url ? (
                            <img
                              src={displayImage.thumb_url}
                              alt={displayImage.filename}
                              style={{ width: 60, height: 60, objectFit: "cover", borderRadius: 3, border: "1px solid #ddd", cursor: "pointer" }}
                              onClick={() => openImagePreview(sku, displayImage, "bulk")}
                              onError={(e) => { e.target.style.display = "none"; }}
                              title={`${displayImage.filename} (Order: ${ebayOrders[displayImage.filename] || 'N/A'})`}
                            />
                          ) : (
                            <div style={{ width: 60, height: 60, background: "#f0f0f0", borderRadius: 3, display: "flex", alignItems: "center", justifyContent: "center", color: "#999", fontSize: 10 }}>
                              No img
                            </div>
                          )}
                          {!hasValidImages && (
                            <span style={{ fontSize: 8, color: "#d32f2f", fontWeight: "bold", background: "#ffebee", padding: "2px 4px", borderRadius: 2 }}>
                              No eBay orders
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: 6, fontWeight: "bold", borderRight: "1px solid #e0e0e0", fontSize: 10 }}>{sku}</td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 9, background: "#f0f8ff" }}>
                        € {Number.isFinite(totalCostNet) ? totalCostNet.toFixed(2) : "0.00"}
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 9, background: "#f0f8ff" }}>
                        {Number.isFinite(opValue) ? opValue.toFixed(2) : "0.00"}
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 9, background: "#f0f8ff" }}>
                        € {Number.isFinite(paymentFee) ? paymentFee.toFixed(2) : "0.00"}
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 9, background: "#f0f8ff" }}>
                        {Number.isFinite(salesCommission) ? (salesCommission * 100).toFixed(1) : "0.0"}%
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 70 }}>
                        <input
                          type="number"
                          step="0.01"
                          value={listingData.price ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), price: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #1976d2", borderRadius: 2, boxSizing: "border-box", fontSize: 10 }}
                        />
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 70 }}>
                        <input
                          type="number"
                          step="0.01"
                          value={listingData.shipping_costs_net ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), shipping_costs_net: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #1976d2", borderRadius: 2, boxSizing: "border-box", fontSize: 10 }}
                        />
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 10, fontWeight: "bold", color: netProfit >= 0 ? "#2e7d32" : "#d32f2f", background: "#fff" }}>
                        € {Number.isFinite(netProfit) ? netProfit.toFixed(2) : "0.00"}
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center", fontSize: 10, fontWeight: "bold", color: netProfitMargin >= 0 ? "#2e7d32" : "#d32f2f", background: "#fff" }}>
                        {Number.isFinite(netProfitMargin) ? netProfitMargin.toFixed(1) : "0.0"}%
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 50 }}>
                        <input
                          type="number"
                          min="1"
                          value={listingData.quantity ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), quantity: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 10 }}
                        />
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 50 }}>
                        <select
                          value={listingData.condition_id ?? "1000"}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), condition_id: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 9 }}
                        >
                          <option value="">-- Select --</option>
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
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 100 }}>
                        <input
                          type="text"
                          value={listingData.condition_description ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), condition_description: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 9 }}
                        />
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 70 }}>
                        <input
                          type="text"
                          value={listingData.ean ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), ean: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 9 }}
                        />
                      </td>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", minWidth: 80 }}>
                        <input
                          type="text"
                          value={listingData.modified_sku ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), modified_sku: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 9 }}
                        />
                      </td>
                      <td style={{ padding: 4, minWidth: 140 }}>
                        <input
                          type="datetime-local"
                          value={listingData.schedule_date ?? ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || {}), schedule_date: e.target.value }
                          }))}
                          style={{ width: "100%", padding: 3, border: "1px solid #ddd", borderRadius: 2, boxSizing: "border-box", fontSize: 8 }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={() => setBulkEbayListingOpen(false)}
              disabled={bulkEbayListingSaving || bulkEbayListingCreating}
              style={{ padding: "8px 12px", opacity: (bulkEbayListingSaving || bulkEbayListingCreating) ? 0.6 : 1 }}
            >
              Cancel
            </button>
            <button
              onClick={handleBulkEbayListingSaveTable}
              disabled={bulkEbayListingSaving || bulkEbayListingCreating}
              style={{ padding: "8px 12px", background: "#ff6b00", color: "white", border: "none", borderRadius: 4, cursor: (bulkEbayListingSaving || bulkEbayListingCreating) ? "not-allowed" : "pointer" }}
            >
              {bulkEbayListingSaving ? "Saving..." : "Save All"}
            </button>
            <button
              onClick={handleBulkEbayListingSaveAndCreate}
              disabled={bulkEbayListingSaving || bulkEbayListingCreating}
              style={{ padding: "8px 12px", background: "#4CAF50", color: "white", border: "none", borderRadius: 4, cursor: (bulkEbayListingSaving || bulkEbayListingCreating) ? "not-allowed" : "pointer" }}
            >
              {bulkEbayListingSaving ? "Saving..." : bulkEbayListingCreating ? "Creating..." : "Save & Create All"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={bulkProductDetailsOpen} onClose={() => setBulkProductDetailsOpen(false)}>
        <div style={{ width: "95vw", maxWidth: "1600px" }}>
          <div style={{ fontSize: 16, fontWeight: "bold", marginBottom: 8 }}>Bulk Edit Product Details</div>
          <div style={{ fontSize: 12, color: "#666", marginBottom: 12 }}>
            Edit product details for {selectedSkusForProductDetailsEdit.size} selected SKU(s)
          </div>

          <div style={{ overflowX: "auto", marginBottom: 12, border: "1px solid #e0e0e0", borderRadius: 6, maxHeight: "65vh", overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr style={{ background: "#f5f5f5", borderBottom: "2px solid #e0e0e0", position: "sticky", top: 0 }}>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap", minWidth: 80 }}>Image</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>SKU</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Supplier Title</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Category</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Condition</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Gender</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Brand</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Color</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Size</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>More details</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Keywords</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Materials</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>OP</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", borderRight: "1px solid #e0e0e0", whiteSpace: "nowrap" }}>Status</th>
                  <th style={{ padding: 6, textAlign: "left", fontWeight: "bold", whiteSpace: "nowrap" }}>Lager</th>
                </tr>
              </thead>
              <tbody>
                {Array.from(selectedSkusForProductDetailsEdit).map((sku) => {
                  const allImages = items.find(item => item.sku === sku)?.data?.images || [];
                  const ebayOrders = ebayImageOrders[sku] || {};
                  const imageWithOrder1 = allImages.find(img => ebayOrders[img.filename] === 1);
                  const displayImage = imageWithOrder1 || allImages[0];
                  const getValue = (fieldName) => {
                    const override = bulkProductDetailsEdits[sku]?.[fieldName];
                    return override !== undefined ? override : getDetailValueByName(sku, fieldName);
                  };
                  const setValue = (fieldName, value) => {
                    setBulkProductDetailsEdits((prev) => ({
                      ...prev,
                      [sku]: {
                        ...(prev[sku] || {}),
                        [fieldName]: value,
                      }
                    }));
                  };
                  return (
                    <tr key={sku} style={{ borderBottom: "1px solid #e0e0e0" }}>
                      <td style={{ padding: 4, borderRight: "1px solid #e0e0e0", textAlign: "center" }}>
                        {displayImage?.thumb_url ? (
                          <img
                            src={displayImage.thumb_url}
                            alt={displayImage.filename}
                            style={{ width: 60, height: 60, objectFit: "cover", borderRadius: 3, border: "1px solid #ddd", cursor: "pointer" }}
                            onClick={() => openImagePreview(sku, displayImage, "bulk")}
                            onError={(e) => { e.target.style.display = "none"; }}
                            title={displayImage.filename}
                          />
                        ) : (
                          <div style={{ width: 60, height: 60, background: "#f0f0f0", borderRadius: 3, display: "flex", alignItems: "center", justifyContent: "center", color: "#999", fontSize: 10 }}>
                            No img
                          </div>
                        )}
                      </td>
                      <td style={{ padding: 6, fontWeight: "bold", borderRight: "1px solid #e0e0e0", fontSize: 10 }}>{sku}</td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 200 }}>
                        <div style={{ background: "#f9f9f9", border: "1px solid #e0e0e0", borderRadius: 3, padding: "6px 8px", color: "#666" }}>
                          {getValue("Supplier Title") || "(empty)"}
                        </div>
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 160 }}>
                        <div style={{ position: "relative" }}>
                          <input
                            value={getValue("Category")}
                            onChange={(e) => {
                              setValue("Category", e.target.value);
                              searchEbayCategories(sku, e.target.value);
                            }}
                            onFocus={(e) => searchEbayCategories(sku, e.target.value)}
                            onBlur={() => setTimeout(() => {
                              setEbayCategorySuggestions((prev) => ({ ...prev, [sku]: [] }));
                            }, 150)}
                            style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                          />
                          {(ebayCategorySuggestions[sku] || []).length > 0 && (
                            <div
                              style={{
                                position: "absolute",
                                top: "100%",
                                left: 0,
                                right: 0,
                                zIndex: 30,
                                background: "white",
                                border: "1px solid #e0e0e0",
                                borderTop: "none",
                                maxHeight: 200,
                                overflowY: "auto",
                                boxShadow: "0 4px 10px rgba(0,0,0,0.08)",
                              }}
                            >
                              {(ebayCategorySuggestions[sku] || []).map((item, idx) => (
                                <div
                                  key={`${item.category_id || item.label}-${idx}`}
                                  onMouseDown={() => applyProductCategorySelection(sku, item)}
                                  style={{
                                    padding: "6px 8px",
                                    cursor: "pointer",
                                    fontSize: 11,
                                    borderTop: "1px solid #f0f0f0"
                                  }}
                                >
                                  <div style={{ fontWeight: 600, color: "#333" }}>{item.label}</div>
                                  {item.category_id && (
                                    <div style={{ fontSize: 10, color: "#777" }}>ID: {item.category_id}</div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Condition")}
                          onChange={(e) => setValue("Condition", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Gender")}
                          onChange={(e) => setValue("Gender", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Brand")}
                          onChange={(e) => setValue("Brand", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Color")}
                          onChange={(e) => setValue("Color", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Size")}
                          onChange={(e) => setValue("Size", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 220 }}>
                        <textarea
                          value={getValue("More details")}
                          onChange={(e) => setValue("More details", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, minHeight: 48, boxSizing: "border-box", resize: "vertical" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 180 }}>
                        <textarea
                          value={getValue("Keywords")}
                          onChange={(e) => setValue("Keywords", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, minHeight: 48, boxSizing: "border-box", resize: "vertical" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 180 }}>
                        <textarea
                          value={getValue("Materials")}
                          onChange={(e) => setValue("Materials", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, minHeight: 48, boxSizing: "border-box", resize: "vertical" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 90 }}>
                        <input
                          value={getValue("OP")}
                          onChange={(e) => setValue("OP", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, borderRight: "1px solid #e0e0e0", minWidth: 120 }}>
                        <input
                          value={getValue("Status")}
                          onChange={(e) => setValue("Status", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                      <td style={{ padding: 6, minWidth: 120 }}>
                        <input
                          value={getValue("Lager")}
                          onChange={(e) => setValue("Lager", e.target.value)}
                          style={{ width: "100%", padding: 4, border: "1px solid #2196F3", borderRadius: 2, fontSize: 11, boxSizing: "border-box" }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={() => setBulkProductDetailsOpen(false)}
              disabled={bulkProductDetailsSaving}
              style={{ padding: "8px 12px", opacity: bulkProductDetailsSaving ? 0.6 : 1 }}
            >
              Cancel
            </button>
            <button
              onClick={handleBulkProductDetailsSave}
              disabled={bulkProductDetailsSaving}
              style={{ padding: "8px 12px", background: "#2196F3", color: "white", border: "none", borderRadius: 4, cursor: bulkProductDetailsSaving ? "not-allowed" : "pointer" }}
            >
              {bulkProductDetailsSaving ? "Saving..." : "Save All"}
            </button>
          </div>
        </div>
      </Modal>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <Link to="/skus">← Back to list</Link>
        <h3 style={{ margin: 0 }}>Batch view ({selectedSkus.length} SKUs)</h3>
        <button
          onClick={() => {
            const allSelected = selectedSkusForEnrichment.size === filteredItems.length;
            if (allSelected) {
              setSelectedSkusForEnrichment(new Set());
            } else {
              const allSkus = new Set(filteredItems.map(item => item.sku));
              setSelectedSkusForEnrichment(allSkus);
            }
          }}
          style={{
            padding: "6px 12px",
            fontSize: 13,
            background: (selectedSkusForEnrichment.size === filteredItems.length) ? "#666" : "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          {(selectedSkusForEnrichment.size === filteredItems.length) ? "✓ Deselect All SKUs" : "Select All SKUs"}
        </button>
        <button
          onClick={handleBulkGenerateMissingJson}
          disabled={selectedSkusForEnrichment.size === 0}
          style={{
            padding: "6px 12px",
            fontSize: 13,
            background: selectedSkusForEnrichment.size === 0 ? "#e0e0e0" : "#9c27b0",
            color: selectedSkusForEnrichment.size === 0 ? "#666" : "white",
            border: "none",
            borderRadius: 4,
            cursor: selectedSkusForEnrichment.size === 0 ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {(() => {
            const missingCount = Array.from(selectedSkusForEnrichment).filter(
              (sku) => jsonStatus[sku] === false
            ).length;
            return missingCount > 0
              ? `Gen JSON (${missingCount} missing)`
              : "Gen JSON (missing)";
          })()}
        </button>
        <button
          onClick={() => {
            // Calculate total available images from filtered items
            const allImages = {};
            filteredItems.forEach(item => {
              if (item.data && item.data.images) {
                allImages[item.sku] = item.data.images.map(img => img.filename);
              }
            });
            
            // Check if all images are selected
            const currentTotal = Object.values(selectedImages).reduce((sum, files) => sum + files.length, 0);
            const maxTotal = Object.values(allImages).reduce((sum, files) => sum + files.length, 0);
            const allSelected = currentTotal === maxTotal && maxTotal > 0;
            
            if (allSelected) {
              // Deselect all
              setSelectedImages({});
            } else {
              // Select all
              setSelectedImages(allImages);
            }
          }}
          style={{
            padding: "6px 12px",
            fontSize: 13,
            background: totalSelectedImages > 0 ? "#2196F3" : "#e0e0e0",
            color: totalSelectedImages > 0 ? "white" : "#666",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          {(() => {
            const maxTotal = filteredItems.reduce((sum, item) => 
              sum + (item.data?.images?.length || 0), 0
            );
            const allSelected = totalSelectedImages === maxTotal && maxTotal > 0;
            return allSelected ? "✓ Deselect All Images" : "Select All Images";
          })()}
        </button>
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
          padding: 6,
          borderRadius: 0,
          marginBottom: 8,
          border: "none",
          borderBottom: "2px solid #2196F3",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 4, fontSize: 11 }}>
            Batch Classify: {totalSelectedImages} image(s) selected across {Object.keys(selectedImages).filter(sku => selectedImages[sku].length > 0).length} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button
              onClick={() => handleBatchClassifyAll("phone")}
              disabled={batchClassifying}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
              }}
            >
              📱 Phone
            </button>
            <button
              onClick={() => handleBatchClassifyAll("stock")}
              disabled={batchClassifying}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#FF9800",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
              }}
            >
              📦 Stock
            </button>
            <button
              onClick={() => handleBatchClassifyAll("enhanced")}
              disabled={batchClassifying}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#9C27B0",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
              }}
            >
              ✨ Enhanced
            </button>
            <button
              onClick={handleBatchMarkAsMain}
              disabled={batchClassifying}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: batchClassifying ? "not-allowed" : "pointer",
                background: "#FFD700",
                color: "#000",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
              }}
            >
              ⭐ Mark as Main
            </button>
            <button
              onClick={() => setSelectedImages({})}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: "pointer",
                background: "#666",
                color: "white",
                border: "none",
                borderRadius: 3,
              }}
            >
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* AI Enrichment Panel */}
      {selectedSkusForEnrichment.size > 0 && (
        <div style={{
          position: "fixed",
          top: totalSelectedImages > 0 ? 50 : 0,
          left: 0,
          right: 0,
          zIndex: 99,
          background: "#e8f5e9",
          padding: 6,
          borderRadius: 0,
          marginBottom: 8,
          border: "none",
          borderBottom: "2px solid #4CAF50",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 4, fontSize: 11 }}>
            🤖 AI + ⭐ eBay Enrichment: {selectedSkusForEnrichment.size} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
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
                padding: "4px 8px",
                fontSize: 11,
                background: "#388E3C",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              {selectedSkusForEnrichment.size === items.length ? "Deselect All" : "Select All"}
            </button>
            <button
              onClick={handleEnrichAll}
              disabled={enrichmentInProgress || selectedSkusForEnrichment.size === 0}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: enrichmentInProgress ? "#ccc" : "#4CAF50",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
                cursor: enrichmentInProgress || selectedSkusForEnrichment.size === 0 ? "not-allowed" : "pointer",
              }}
            >
              {enrichmentInProgress ? "Enriching..." : "✨ Enrich"}
            </button>
            <button
              onClick={handleEbayEnrichAll}
              disabled={ebayEnrichmentInProgress || selectedSkusForEnrichment.size === 0}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: ebayEnrichmentInProgress ? "#ccc" : "#FF9800",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
                cursor: ebayEnrichmentInProgress || selectedSkusForEnrichment.size === 0 ? "not-allowed" : "pointer",
              }}
            >
              {ebayEnrichmentInProgress ? "Enriching..." : "⭐ eBay Fields"}
            </button>
            <button
              onClick={handleEbaySeoEnrichAll}
              disabled={ebayEnrichmentInProgress || selectedSkusForEnrichment.size === 0}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: ebayEnrichmentInProgress ? "#ccc" : "#8e24aa",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
                cursor: ebayEnrichmentInProgress || selectedSkusForEnrichment.size === 0 ? "not-allowed" : "pointer",
              }}
            >
              {ebayEnrichmentInProgress ? "Enriching..." : "🔍 SEO Only"}
            </button>
            <button
              onClick={() => setSelectedSkusForEnrichment(new Set())}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: "pointer",
                background: "#666",
                color: "white",
                border: "none",
                borderRadius: 3,
              }}
            >
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* Product Details Bulk Edit Panel */}
      {selectedSkusForProductDetailsEdit.size > 0 && (
        <div style={{
          position: "fixed",
          top: (() => {
            let offset = 0;
            if (totalSelectedImages > 0) offset += 50;
            if (selectedSkusForEnrichment.size > 0) offset += 50;
            return offset;
          })(),
          left: 0,
          right: 0,
          zIndex: 98,
          background: "#e3f2fd",
          padding: 6,
          borderRadius: 0,
          marginBottom: 8,
          border: "none",
          borderBottom: "2px solid #1976d2",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 4, fontSize: 11 }}>
            📋 Product Details: {selectedSkusForProductDetailsEdit.size} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button
              onClick={() => {
                if (selectedSkusForProductDetailsEdit.size === items.length) {
                  setSelectedSkusForProductDetailsEdit(new Set());
                } else {
                  const allSkus = new Set(items.map(item => item.sku));
                  setSelectedSkusForProductDetailsEdit(allSkus);
                }
              }}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#1976d2",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              {selectedSkusForProductDetailsEdit.size === items.length ? "Deselect All" : "Select All"}
            </button>
            <button
              onClick={() => setBulkProductDetailsOpen(true)}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              ✏️ Bulk Edit
            </button>
            <button
              onClick={() => setSelectedSkusForProductDetailsEdit(new Set())}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: "pointer",
                background: "#666",
                color: "white",
                border: "none",
                borderRadius: 3,
              }}
            >
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* eBay Listing Bulk Edit Panel */}
      {selectedSkusForEbayListingEdit.size > 0 && (
        <div style={{
          position: "fixed",
          top: (() => {
            let offset = 0;
            if (totalSelectedImages > 0) offset += 50;
            if (selectedSkusForEnrichment.size > 0) offset += 50;
            if (selectedSkusForProductDetailsEdit.size > 0) offset += 50;
            return offset;
          })(),
          left: 0,
          right: 0,
          zIndex: 98,
          background: "#fff3e0",
          padding: 6,
          borderRadius: 0,
          marginBottom: 8,
          border: "none",
          borderBottom: "2px solid #ff6b00",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 4, fontSize: 11 }}>
            📦 eBay Listing Drafts: {selectedSkusForEbayListingEdit.size} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button
              onClick={() => {
                if (selectedSkusForEbayListingEdit.size === items.length) {
                  setSelectedSkusForEbayListingEdit(new Set());
                } else {
                  const allSkus = new Set(items.map(item => item.sku));
                  setSelectedSkusForEbayListingEdit(allSkus);
                }
              }}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#ef6c00",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              {selectedSkusForEbayListingEdit.size === items.length ? "Deselect All" : "Select All"}
            </button>
            <button
              onClick={() => setBulkEbayListingOpen(true)}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#ff6b00",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              ✏️ Bulk Edit
            </button>
            <button
              onClick={handleBulkEbayCreateListings}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#d84315",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              📤 Bulk Create
            </button>
            <button
              onClick={() => setSelectedSkusForEbayListingEdit(new Set())}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                cursor: "pointer",
                background: "#666",
                color: "white",
                border: "none",
                borderRadius: 3,
              }}
            >
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* Enrichment results */}
      {enrichmentResults && (
        <div style={{
          background: "white",
          padding: 12,
          borderRadius: 4,
          marginBottom: 16,
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

      {/* eBay Enrichment results */}
      {ebayEnrichmentResults && (
        <div style={{
          background: "white",
          padding: 12,
          borderRadius: 4,
          marginBottom: 16,
          border: `2px solid ${ebayEnrichmentResults.failed === 0 ? "#FF9800" : "#FF5722"}`,
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 8 }}>
            {ebayEnrichmentResults.failed === 0 ? "✅" : "⚠️"} {ebayEnrichmentResults.mode === "seo" ? "eBay SEO Enrichment" : "eBay Fields Enrichment"}: {ebayEnrichmentResults.succeeded} succeeded, {ebayEnrichmentResults.failed} failed
          </div>
          {Object.entries(ebayEnrichmentResults.results).map(([s, res]) => (
            <div key={s} style={{ fontSize: 12, padding: "4px 0", color: res.success ? "#FF9800" : "#FF3D00" }}>
              {s}: {res.success ? res.message : res.message}
            </div>
          ))}
        </div>
      )}

      {/* Filter Panel */}
      <div style={{
        background: "#f9f9f9",
        padding: 12,
        borderRadius: 8,
        marginBottom: 16,
        border: "2px solid #e0e0e0",
      }}>
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
            🔍 Filters {(selectedStatusFilters.size > 0 || selectedLagerFilters.size > 0 || selectedBrandFilters.size > 0 || completionFilter !== null) && `(${selectedStatusFilters.size + selectedLagerFilters.size + selectedBrandFilters.size + (completionFilter !== null ? 1 : 0)} active)`}
          </button>
          <div style={{ fontSize: 12, color: "#666" }}>
            Showing {filteredItems.length} / {items.length} SKU(s)
          </div>
        </div>

        {showFilters && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
            {/* Status Filter */}
            <div>
              <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Status</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {getAvailableStatusValues.map((status) => (
                  <label key={status} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                    <input
                      type="checkbox"
                      checked={selectedStatusFilters.has(status)}
                      onChange={(e) => {
                        const newFilters = new Set(selectedStatusFilters);
                        if (e.target.checked) {
                          newFilters.add(status);
                        } else {
                          newFilters.delete(status);
                        }
                        setSelectedStatusFilters(newFilters);
                      }}
                      style={{ cursor: "pointer" }}
                    />
                    <span>{status}</span>
                  </label>
                ))}
                {getAvailableStatusValues.length === 0 && (
                  <div style={{ fontSize: 11, color: "#999" }}>(No statuses assigned)</div>
                )}
              </div>
            </div>

            {/* Lager Filter */}
            <div>
              <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Lager</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {getAvailableLagerValues.map((lager) => (
                  <label key={lager} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                    <input
                      type="checkbox"
                      checked={selectedLagerFilters.has(lager)}
                      onChange={(e) => {
                        const newFilters = new Set(selectedLagerFilters);
                        if (e.target.checked) {
                          newFilters.add(lager);
                        } else {
                          newFilters.delete(lager);
                        }
                        setSelectedLagerFilters(newFilters);
                      }}
                      style={{ cursor: "pointer" }}
                    />
                    <span>{lager}</span>
                  </label>
                ))}
                {getAvailableLagerValues.length === 0 && (
                  <div style={{ fontSize: 11, color: "#999" }}>(No lager values assigned)</div>
                )}
              </div>
            </div>

            {/* Brand Filter */}
            <div>
              <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Brand</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {getAvailableBrandValues.map((brand) => (
                  <label key={brand} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                    <input
                      type="checkbox"
                      checked={selectedBrandFilters.has(brand)}
                      onChange={(e) => {
                        const newFilters = new Set(selectedBrandFilters);
                        if (e.target.checked) {
                          newFilters.add(brand);
                        } else {
                          newFilters.delete(brand);
                        }
                        setSelectedBrandFilters(newFilters);
                      }}
                      style={{ cursor: "pointer" }}
                    />
                    <span>{brand}</span>
                  </label>
                ))}
                {getAvailableBrandValues.length === 0 && (
                  <div style={{ fontSize: 11, color: "#999" }}>(No brands assigned)</div>
                )}
              </div>
            </div>

            {/* Completion Filter */}
            <div>
              <div style={{ fontWeight: "bold", marginBottom: 8, fontSize: 12, color: "#333" }}>Completion</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === null}
                    onChange={() => setCompletionFilter(null)}
                    style={{ cursor: "pointer" }}
                  />
                  <span>All</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === "empty"}
                    onChange={() => setCompletionFilter("empty")}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Empty (0%)</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === "low"}
                    onChange={() => setCompletionFilter("low")}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Low (1-32%)</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === "medium"}
                    onChange={() => setCompletionFilter("medium")}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Medium (33-65%)</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === "high"}
                    onChange={() => setCompletionFilter("high")}
                    style={{ cursor: "pointer" }}
                  />
                  <span>High (66-99%)</span>
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
                  <input
                    type="radio"
                    name="completion"
                    checked={completionFilter === "complete"}
                    onChange={() => setCompletionFilter("complete")}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Complete (100%)</span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Clear filters button */}
        {(selectedStatusFilters.size > 0 || selectedLagerFilters.size > 0 || selectedBrandFilters.size > 0 || completionFilter !== null) && (
          <button
            onClick={() => {
              setSelectedStatusFilters(new Set());
              setSelectedLagerFilters(new Set());
              setSelectedBrandFilters(new Set());
              setCompletionFilter(null);
            }}
            style={{
              marginTop: 12,
              padding: "6px 12px",
              fontSize: 12,
              background: "#ff6b6b",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            Clear All Filters
          </button>
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

      {filteredItems.map(({ sku, data, error }) => {
        const images = Array.isArray(data?.images) ? data.images : [];
        const conditionFromProduct = getDetailValue(sku, "Product Condition", "Condition");
        const totalCostNet = toNumber(getDetailValue(sku, "Price Data", "Total Cost Net"));
        const opValue = toNumber(getDetailValue(sku, "OP", "OP"));
        const fees = ebaySchemas[sku]?.metadata?.fees || {};
        const paymentFee = toNumber(fees.payment_fee);
        const salesCommission = toNumber(fees.sales_commission_percentage);
        const sellingPriceTotal = toNumber(ebayListingData[sku]?.price || 0);
        const shippingCostsNet = toNumber(ebayListingData[sku]?.shipping_costs_net || 0);
        const netProfit = (sellingPriceTotal / 1.19) - (sellingPriceTotal * salesCommission) - paymentFee - shippingCostsNet - totalCostNet;
        const netProfitMargin = totalCostNet > 0 ? (netProfit / totalCostNet) * 100 : 0;
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
                    title="Select for AI Product Details & eBay Fields enrichment"
                  />
                  <input
                    type="checkbox"
                    checked={selectedSkusForProductDetailsEdit.has(sku)}
                    onChange={() => toggleSkuForProductDetailsEdit(sku)}
                    style={{ width: 18, height: 18, cursor: "pointer" }}
                    title="Select for bulk product details edit"
                  />
                  <input
                    type="checkbox"
                    checked={selectedSkusForEbayListingEdit.has(sku)}
                    onChange={() => toggleSkuForEbayListingEdit(sku)}
                    style={{ width: 18, height: 18, cursor: "pointer" }}
                    title="Select for bulk eBay listing edit"
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
                  {ebayListingStatus[sku] !== undefined && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        padding: "4px 8px",
                        background:
                          ebayListingStatus[sku] === true
                            ? "#e3f2fd"
                            : ebayListingStatus[sku] === false
                            ? "#f3f4f6"
                            : "#fff8e1",
                        borderRadius: 4,
                        fontSize: "0.85em",
                      }}
                      title={
                        ebayListingStatus[sku] === true
                          ? "Active eBay listing found"
                          : ebayListingStatus[sku] === false
                          ? "No active eBay listing"
                          : "eBay listing cache not available"
                      }
                    >
                      <span
                        style={{
                          fontWeight: "bold",
                          color:
                            ebayListingStatus[sku] === true
                              ? "#1976d2"
                              : ebayListingStatus[sku] === false
                              ? "#6b7280"
                              : "#f57c00",
                        }}
                      >
                        {ebayListingStatus[sku] === true
                          ? "✓ eBay"
                          : ebayListingStatus[sku] === false
                          ? "✗ eBay"
                          : "? eBay"}
                      </span>
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
                            {productDetails[sku].categories.filter(cat => cat.name !== "eBay Fields").map((cat) => (
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
                              productDetails[sku].categories.filter(cat => cat.name !== "eBay Fields").forEach(cat => {
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
                            {productDetails[sku].categories.filter(cat => cat.name !== "eBay Fields").map((cat) => (
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
                                    {cat.name === "Ebay Category" && field.name === "Category" ? (
                                      <div style={{ position: "relative" }}>
                                        <input
                                          type="text"
                                          value={editedFieldsState[sku]?.[cat.name]?.[field.name] ?? field.value}
                                          onChange={(e) => {
                                            const value = e.target.value;
                                            setEditedFieldsState(prev => ({
                                              ...prev,
                                              [sku]: {
                                                ...(prev[sku] || {}),
                                                [cat.name]: {
                                                  ...(prev[sku]?.[cat.name] || {}),
                                                  [field.name]: value
                                                }
                                              }
                                            }));
                                            searchEbayCategories(sku, value);
                                          }}
                                          placeholder="Type to search eBay categories..."
                                          style={{
                                            width: "100%",
                                            padding: "6px 8px",
                                            border: "1px solid #2196F3",
                                            borderRadius: 3,
                                            fontSize: 12,
                                            fontFamily: "monospace",
                                            boxSizing: "border-box"
                                          }}
                                        />
                                        {(ebayCategoryLoading[sku] || (ebayCategorySuggestions[sku] && ebayCategorySuggestions[sku].length > 0)) && (
                                          <div
                                            style={{
                                              position: "absolute",
                                              top: "100%",
                                              left: 0,
                                              right: 0,
                                              zIndex: 50,
                                              background: "white",
                                              border: "1px solid #e0e0e0",
                                              borderTop: "none",
                                              maxHeight: 220,
                                              overflowY: "auto",
                                              boxShadow: "0 4px 10px rgba(0,0,0,0.08)",
                                            }}
                                          >
                                            {ebayCategoryLoading[sku] && (
                                              <div style={{ padding: 8, fontSize: 11, color: "#666" }}>Searching...</div>
                                            )}
                                            {(ebayCategorySuggestions[sku] || []).map((item, idx) => (
                                              <div
                                                key={`${item.category_id || item.label}-${idx}`}
                                                onClick={() => applyEbayCategorySelection(sku, cat.name, field.name, item)}
                                                style={{
                                                  padding: "6px 8px",
                                                  cursor: "pointer",
                                                  fontSize: 11,
                                                  borderTop: "1px solid #f0f0f0"
                                                }}
                                              >
                                                <div style={{ fontWeight: 600, color: "#333" }}>{item.label}</div>
                                                {item.category_id && (
                                                  <div style={{ fontSize: 10, color: "#777" }}>ID: {item.category_id}</div>
                                                )}
                                              </div>
                                            ))}
                                            {!ebayCategoryLoading[sku] && (ebayCategorySuggestions[sku] || []).length === 0 && (
                                              <div style={{ padding: 8, fontSize: 11, color: "#999" }}>No matches</div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    ) : (
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
                                    )}
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

              {/* eBay Collapsible Section */}
              <div style={{ marginTop: 16, borderTop: "2px solid #e0e0e0", paddingTop: 16 }}>
                <button
                  onClick={() => {
                    setEbayExpanded(prev => ({ ...prev, [sku]: !prev[sku] }));
                    if (!ebayExpanded[sku] && !ebaySchemas[sku]) loadEbayData(sku);
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
                  <span style={{ fontSize: 18, transform: ebayExpanded[sku] ? "rotate(90deg)" : "rotate(0deg)", display: "inline-block", transition: "transform 0.2s" }}>▶</span>
                  ⭐ eBay Integration {ebayValidations[sku] && `(${ebayValidations[sku].filled_required}/${ebayValidations[sku].total_required})`}
                </button>

                {ebayExpanded[sku] && (
                  <div style={{ padding: 12, background: "white" }}>
                    {/* Validation Status */}
                    {ebayValidations[sku] && (
                      <div style={{
                        marginBottom: 12,
                        padding: 8,
                        background: ebayValidations[sku].valid ? "#f0fff4" : "#fff9e6",
                        border: `1px solid ${ebayValidations[sku].valid ? "#28a745" : "#ffc107"}`,
                        borderRadius: 4
                      }}>
                        <div style={{ fontSize: 11, fontWeight: "bold", color: ebayValidations[sku].valid ? "#28a745" : "#f57c00" }}>
                          {ebayValidations[sku].valid ? "✓ Ready for listing" : "⚠ Missing required fields"}
                        </div>
                        <div style={{ fontSize: 10, color: "#666", marginTop: 4 }}>
                          Required: {ebayValidations[sku].filled_required}/{ebayValidations[sku].total_required} |
                          Optional: {ebayValidations[sku].filled_optional}/{ebayValidations[sku].total_optional}
                        </div>
                        {ebayValidations[sku].missing_required && ebayValidations[sku].missing_required.length > 0 && (
                          <div style={{ fontSize: 10, color: "#d32f2f", marginTop: 6 }}>
                            Missing: {ebayValidations[sku].missing_required.slice(0, 3).join(", ")}
                            {ebayValidations[sku].missing_required.length > 3 && ` +${ebayValidations[sku].missing_required.length - 3} more`}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
                      <button
                        onClick={() => handleEbayEnrich(sku)}
                        disabled={ebayEnriching[sku] || ebaySeoEnriching[sku] || ebayEditingFields[sku]}
                        style={{
                          flex: 1,
                          minWidth: 120,
                          padding: "8px 12px",
                          fontSize: 11,
                          background: "#28a745",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: (ebayEnriching[sku] || ebaySeoEnriching[sku] || ebayEditingFields[sku]) ? "not-allowed" : "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        {ebayEnriching[sku] ? "🤖 Enriching..." : "🤖 Auto-Fill"}
                      </button>
                      <button
                        onClick={() => handleEbaySeoEnrich(sku)}
                        disabled={ebaySeoEnriching[sku] || ebayEnriching[sku] || ebayEditingFields[sku]}
                        style={{
                          flex: 1,
                          minWidth: 140,
                          padding: "8px 12px",
                          fontSize: 11,
                          background: "#8e24aa",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: (ebaySeoEnriching[sku] || ebayEnriching[sku] || ebayEditingFields[sku]) ? "not-allowed" : "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        {ebaySeoEnriching[sku] ? "🔍 SEO..." : "🔍 SEO Only"}
                      </button>
                      <button
                        onClick={() => validateEbayFields(sku)}
                        disabled={ebayEditingFields[sku]}
                        title="Check if all required eBay fields are filled"
                        style={{
                          flex: 1,
                          minWidth: 100,
                          padding: "8px 12px",
                          fontSize: 11,
                          background: "#17a2b8",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: ebayEditingFields[sku] ? "not-allowed" : "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        ✓ Validate
                      </button>
                      {!ebayEditingFields[sku] ? (
                        <button
                          onClick={() => {
                            const normalizeFields = (fields = {}) => Object.fromEntries(
                              Object.entries(fields).map(([key, value]) => {
                                if (value && typeof value === "object" && "value" in value) {
                                  return [key, value.value ?? ""];
                                }
                                return [key, value ?? ""];
                              })
                            );
                            const requiredValues = normalizeFields(ebayFields[sku]?.required_fields || {});
                            const optionalValues = normalizeFields(ebayFields[sku]?.optional_fields || {});
                            setEbayEditingFields(prev => ({ ...prev, [sku]: true }));
                            setEbayEditedFields(prev => ({
                              ...prev,
                              [sku]: {
                                required: requiredValues,
                                optional: optionalValues
                              }
                            }));
                          }}
                          style={{
                            flex: 1,
                            minWidth: 100,
                            padding: "8px 12px",
                            fontSize: 11,
                            background: "#ff9800",
                            color: "white",
                            border: "none",
                            borderRadius: 4,
                            cursor: "pointer",
                            fontWeight: "bold"
                          }}
                        >
                          ✏️ Edit
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => handleSaveEbayFields(sku)}
                            disabled={ebaySavingFields[sku]}
                            style={{
                              flex: 1,
                              minWidth: 80,
                              padding: "8px 12px",
                              fontSize: 11,
                              background: "#4CAF50",
                              color: "white",
                              border: "none",
                              borderRadius: 4,
                              cursor: ebaySavingFields[sku] ? "not-allowed" : "pointer",
                              fontWeight: "bold"
                            }}
                          >
                            {ebaySavingFields[sku] ? "Saving..." : "💾 Save"}
                          </button>
                          <button
                            onClick={() => {
                              setEbayEditingFields(prev => ({ ...prev, [sku]: false }));
                              setEbayEditedFields(prev => {
                                const newState = { ...prev };
                                delete newState[sku];
                                return newState;
                              });
                            }}
                            style={{
                              flex: 1,
                              minWidth: 80,
                              padding: "8px 12px",
                              fontSize: 11,
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
                        </>
                      )}
                    </div>

                    <div style={{ marginBottom: 12, border: "1px solid #e0e0e0", borderRadius: 6, overflow: "hidden" }}>
                      <button
                        onClick={() => setEbaySubsectionExpanded(prev => ({
                          ...prev,
                          [`${sku}/ebay-fields`]: !(prev[`${sku}/ebay-fields`] !== false)
                        }))}
                        style={{
                          width: "100%",
                          background: "#f8f9fa",
                          border: "none",
                          borderBottom: "1px solid #e0e0e0",
                          cursor: "pointer",
                          padding: "10px 12px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          fontWeight: "bold",
                          color: "#d32f2f",
                          fontSize: 12,
                        }}
                      >
                        <span>1. eBay Fields</span>
                        <span style={{ transform: (ebaySubsectionExpanded[`${sku}/ebay-fields`] !== false) ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>▶</span>
                      </button>

                      {(ebaySubsectionExpanded[`${sku}/ebay-fields`] !== false) && (
                        <div style={{ padding: 10, background: "#fff" }}>
                          {/* Category Info */}
                          {ebayFields[sku] && (
                            <div style={{ marginBottom: 12, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 10 }}>
                              <div style={{ fontWeight: "bold", marginBottom: 4 }}>{ebayFields[sku].category || "No Category"}</div>
                              <div style={{ color: "#666" }}>ID: {ebayFields[sku].categoryId || "N/A"}</div>
                              {ebayFields[sku].error_message && (
                                <div style={{ color: "#d32f2f", marginTop: 4, fontSize: 9 }}>⚠️ {ebayFields[sku].error_message}</div>
                              )}
                            </div>
                          )}

                          {/* eBay Fields Display */}
                          {ebayFields[sku] && (
                            <div style={{ marginBottom: 12 }}>
                              {/* Show message if no fields available */}
                              {(!ebayFields[sku].required_fields || Object.keys(ebayFields[sku].required_fields).length === 0) &&
                               (!ebayFields[sku].optional_fields || Object.keys(ebayFields[sku].optional_fields).length === 0) && (
                                <div style={{ padding: 12, background: "#fff9e6", border: "1px solid #ffc107", borderRadius: 4, fontSize: 10, color: "#666" }}>
                                  ⚠️ No eBay fields schema loaded. {ebayFields[sku].message || "Please check if the category is set correctly and has a valid schema."}
                                </div>
                              )}
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 12 }}>
                                {/* Required Fields */}
                                {ebayFields[sku].required_fields && Object.keys(ebayFields[sku].required_fields).length > 0 && (
                                  <div>
                                    <div style={{ fontSize: 10, fontWeight: "bold", color: "#d32f2f", marginBottom: 6 }}>
                                      Required Fields ({Object.keys(ebayFields[sku].required_fields).length})
                                    </div>
                                    <div style={{ maxHeight: 300, overflow: "auto" }}>
                                      {Object.entries(ebayFields[sku].required_fields).map(([name, fieldObj]) => {
                                        const fieldValue = typeof fieldObj === 'object' ? fieldObj.value : fieldObj;
                                        const fieldDescription = typeof fieldObj === 'object' ? fieldObj.description : '';
                                        const fieldOptions = typeof fieldObj === 'object' ? fieldObj.options : [];
                                        return (
                                          <div key={name} style={{ marginBottom: 6, padding: 6, background: "#fff8f8", borderRadius: 3 }}>
                                            <div style={{ fontSize: 9, fontWeight: "600", color: "#d32f2f", marginBottom: 3 }}>{name}</div>
                                            {fieldDescription && (
                                              <div style={{ fontSize: 8, color: "#999", marginBottom: 3, fontStyle: "italic" }}>{fieldDescription}</div>
                                            )}
                                            {ebayEditingFields[sku] ? (
                                              fieldOptions && fieldOptions.length > 0 ? (
                                                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                                                  <select
                                                    value={(() => {
                                                      const currentVal = ebayEditedFields[sku]?.required?.hasOwnProperty(name)
                                                        ? ebayEditedFields[sku]?.required?.[name]
                                                        : (fieldValue ?? "");
                                                      return fieldOptions.includes(currentVal) ? currentVal : "";
                                                    })()}
                                                    onChange={(e) => setEbayEditedFields(prev => ({
                                                      ...prev,
                                                      [sku]: {
                                                        ...(prev[sku] || {}),
                                                        required: { ...(prev[sku]?.required || {}), [name]: e.target.value }
                                                      }
                                                    }))}
                                                    style={{
                                                      width: "45%",
                                                      padding: "4px 6px",
                                                      fontSize: 9,
                                                      border: "1px solid #d32f2f",
                                                      borderRadius: 3,
                                                      fontFamily: "monospace"
                                                    }}
                                                  >
                                                    <option value="">-- Custom --</option>
                                                    {fieldOptions.map(opt => (
                                                      <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                  </select>
                                                  <input
                                                    type="text"
                                                    value={ebayEditedFields[sku]?.required?.hasOwnProperty(name) ? ebayEditedFields[sku]?.required?.[name] : (fieldValue ?? '')}
                                                    onChange={(e) => setEbayEditedFields(prev => ({
                                                      ...prev,
                                                      [sku]: {
                                                        ...(prev[sku] || {}),
                                                        required: { ...(prev[sku]?.required || {}), [name]: e.target.value }
                                                      }
                                                    }))}
                                                    placeholder="Custom value"
                                                    style={{
                                                      width: "55%",
                                                      padding: "4px 6px",
                                                      fontSize: 9,
                                                      border: "1px solid #d32f2f",
                                                      borderRadius: 3,
                                                      fontFamily: "monospace"
                                                    }}
                                                  />
                                                </div>
                                              ) : (
                                                <input
                                                  type="text"
                                                  value={ebayEditedFields[sku]?.required?.hasOwnProperty(name) ? ebayEditedFields[sku]?.required?.[name] : (fieldValue ?? '')}
                                                  onChange={(e) => setEbayEditedFields(prev => ({
                                                    ...prev,
                                                    [sku]: {
                                                      ...(prev[sku] || {}),
                                                      required: { ...(prev[sku]?.required || {}), [name]: e.target.value }
                                                    }
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
                                              )
                                            ) : (
                                              <div style={{ fontSize: 9, color: "#333", marginTop: 2 }}>{fieldValue || <em style={{ color: "#999" }}>empty</em>}</div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}

                                {/* Optional Fields */}
                                {ebayFields[sku].optional_fields && Object.keys(ebayFields[sku].optional_fields).length > 0 && (
                                  <div>
                                    <div style={{ fontSize: 10, fontWeight: "bold", color: "#1976d2", marginBottom: 6 }}>
                                      Optional Fields ({Object.keys(ebayFields[sku].optional_fields).length})
                                    </div>
                                    <div style={{ maxHeight: 300, overflow: "auto" }}>
                                      {Object.entries(ebayFields[sku].optional_fields).map(([name, fieldObj]) => {
                                        const fieldValue = typeof fieldObj === 'object' ? fieldObj.value : fieldObj;
                                        const fieldDescription = typeof fieldObj === 'object' ? fieldObj.description : '';
                                        const fieldOptions = typeof fieldObj === 'object' ? fieldObj.options : [];
                                        return (
                                          <div key={name} style={{ marginBottom: 6, padding: 6, background: "#f8f8ff", borderRadius: 3 }}>
                                            <div style={{ fontSize: 9, fontWeight: "600", color: "#1976d2", marginBottom: 3 }}>{name}</div>
                                            {fieldDescription && (
                                              <div style={{ fontSize: 8, color: "#999", marginBottom: 3, fontStyle: "italic" }}>{fieldDescription}</div>
                                            )}
                                            {ebayEditingFields[sku] ? (
                                              fieldOptions && fieldOptions.length > 0 ? (
                                                <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                                                  <select
                                                    value={(() => {
                                                      const currentVal = ebayEditedFields[sku]?.optional?.hasOwnProperty(name)
                                                        ? ebayEditedFields[sku]?.optional?.[name]
                                                        : (fieldValue ?? "");
                                                      return fieldOptions.includes(currentVal) ? currentVal : "";
                                                    })()}
                                                    onChange={(e) => setEbayEditedFields(prev => ({
                                                      ...prev,
                                                      [sku]: {
                                                        ...(prev[sku] || {}),
                                                        optional: { ...(prev[sku]?.optional || {}), [name]: e.target.value }
                                                      }
                                                    }))}
                                                    style={{
                                                      width: "45%",
                                                      padding: "4px 6px",
                                                      fontSize: 9,
                                                      border: "1px solid #1976d2",
                                                      borderRadius: 3,
                                                      fontFamily: "monospace"
                                                    }}
                                                  >
                                                    <option value="">-- Custom --</option>
                                                    {fieldOptions.map(opt => (
                                                      <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                  </select>
                                                  <input
                                                    type="text"
                                                    value={ebayEditedFields[sku]?.optional?.hasOwnProperty(name) ? ebayEditedFields[sku]?.optional?.[name] : (fieldValue ?? '')}
                                                    onChange={(e) => setEbayEditedFields(prev => ({
                                                      ...prev,
                                                      [sku]: {
                                                        ...(prev[sku] || {}),
                                                        optional: { ...(prev[sku]?.optional || {}), [name]: e.target.value }
                                                      }
                                                    }))}
                                                    placeholder="Custom value"
                                                    style={{
                                                      width: "55%",
                                                      padding: "4px 6px",
                                                      fontSize: 9,
                                                      border: "1px solid #1976d2",
                                                      borderRadius: 3,
                                                      fontFamily: "monospace"
                                                    }}
                                                  />
                                                </div>
                                              ) : (
                                                <input
                                                  type="text"
                                                  value={ebayEditedFields[sku]?.optional?.hasOwnProperty(name) ? ebayEditedFields[sku]?.optional?.[name] : (fieldValue ?? '')}
                                                  onChange={(e) => setEbayEditedFields(prev => ({
                                                    ...prev,
                                                    [sku]: {
                                                      ...(prev[sku] || {}),
                                                      optional: { ...(prev[sku]?.optional || {}), [name]: e.target.value }
                                                    }
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
                                              )
                                            ) : (
                                              <div style={{ fontSize: 9, color: "#333", marginTop: 2 }}>{fieldValue || <em style={{ color: "#999" }}>empty</em>}</div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div style={{ marginBottom: 12, border: "1px solid #e0e0e0", borderRadius: 6, overflow: "hidden" }}>
                      <button
                        onClick={() => setEbaySubsectionExpanded(prev => ({
                          ...prev,
                          [`${sku}/ebay-seo`]: !(prev[`${sku}/ebay-seo`] !== false)
                        }))}
                        style={{
                          width: "100%",
                          background: "#f8f9fa",
                          border: "none",
                          borderBottom: "1px solid #e0e0e0",
                          cursor: "pointer",
                          padding: "10px 12px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          fontWeight: "bold",
                          color: "#7b1fa2",
                          fontSize: 12,
                        }}
                      >
                        <span>2. eBay SEO</span>
                        <span style={{ transform: (ebaySubsectionExpanded[`${sku}/ebay-seo`] !== false) ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>▶</span>
                      </button>

                      {(ebaySubsectionExpanded[`${sku}/ebay-seo`] !== false) && (
                        <div style={{ padding: 10, background: "#fff" }}>
                          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                            {!ebayEditingSeo[sku] ? (
                              <button
                                onClick={() => setEbayEditingSeo(prev => ({ ...prev, [sku]: true }))}
                                style={{
                                  padding: "7px 12px",
                                  fontSize: 11,
                                  background: "#ff9800",
                                  color: "white",
                                  border: "none",
                                  borderRadius: 4,
                                  cursor: "pointer",
                                  fontWeight: "bold"
                                }}
                              >
                                ✏️ Edit SEO
                              </button>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleSaveEbaySeoFields(sku)}
                                  disabled={ebaySavingSeo[sku]}
                                  style={{
                                    padding: "7px 12px",
                                    fontSize: 11,
                                    background: "#4CAF50",
                                    color: "white",
                                    border: "none",
                                    borderRadius: 4,
                                    cursor: ebaySavingSeo[sku] ? "not-allowed" : "pointer",
                                    fontWeight: "bold"
                                  }}
                                >
                                  {ebaySavingSeo[sku] ? "Saving..." : "💾 Save SEO"}
                                </button>
                                <button
                                  onClick={() => {
                                    setEbayEditingSeo(prev => ({ ...prev, [sku]: false }));
                                    loadEbaySeoFields(sku);
                                  }}
                                  style={{
                                    padding: "7px 12px",
                                    fontSize: 11,
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
                              </>
                            )}
                          </div>

                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                            {[
                              { key: "product_type", label: "Product Type" },
                              { key: "product_model", label: "Product Model" },
                              { key: "keyword_1", label: "Keyword 1" },
                              { key: "keyword_2", label: "Keyword 2" },
                              { key: "keyword_3", label: "Keyword 3" },
                            ].map(({ key, label }) => (
                              <div key={key} style={{ padding: 8, background: "#faf5ff", borderRadius: 4 }}>
                                <label style={{ fontSize: 10, fontWeight: "600", display: "block", marginBottom: 4, color: "#7b1fa2" }}>{label}</label>
                                {ebayEditingSeo[sku] ? (
                                  <input
                                    type="text"
                                    value={ebaySeoFields[sku]?.[key] || ""}
                                    onChange={(e) => setEbaySeoFields(prev => ({
                                      ...prev,
                                      [sku]: {
                                        ...(prev[sku] || {}),
                                        [key]: e.target.value
                                      }
                                    }))}
                                    style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ce93d8", borderRadius: 3 }}
                                  />
                                ) : (
                                  <div style={{ fontSize: 10, color: "#333", minHeight: 18 }}>
                                    {ebaySeoFields[sku]?.[key] || <em style={{ color: "#999" }}>empty</em>}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div style={{ marginBottom: 12, border: "1px solid #e0e0e0", borderRadius: 6, overflow: "hidden" }}>
                      <button
                        onClick={() => setEbaySubsectionExpanded(prev => ({
                          ...prev,
                          [`${sku}/create-ebay-listing-fields`]: !(prev[`${sku}/create-ebay-listing-fields`] !== false)
                        }))}
                        style={{
                          width: "100%",
                          background: "#f8f9fa",
                          border: "none",
                          borderBottom: "1px solid #e0e0e0",
                          cursor: "pointer",
                          padding: "10px 12px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          fontWeight: "bold",
                          color: "#ff6b00",
                          fontSize: 12,
                        }}
                      >
                        <span>3. eBay Listing</span>
                        <span style={{ transform: (ebaySubsectionExpanded[`${sku}/create-ebay-listing-fields`] !== false) ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>▶</span>
                      </button>

                      {(ebaySubsectionExpanded[`${sku}/create-ebay-listing-fields`] !== false) && (
                      <div style={{ paddingTop: 12, paddingLeft: 10, paddingRight: 10, paddingBottom: 10 }}>
                      <div style={{ fontSize: 11, fontWeight: "bold", marginBottom: 8, color: "#ff6b00" }}>
                        {ebayListingData[sku]?.de_listing_title || "—"}
                      </div>

                      <div style={{ background: "#f4f8ff", padding: 8, borderRadius: 6, border: "1px solid #e3ecff", marginBottom: 8 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#666" }}>Condition</label>
                            <input
                              readOnly
                              value={conditionFromProduct || "—"}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3, background: "#fafafa" }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#666" }}>Total Cost Net</label>
                            <input
                              readOnly
                              value={`€ ${Number.isFinite(totalCostNet) ? totalCostNet.toFixed(2) : "0.00"}`}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3, background: "#fafafa" }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#666" }}>OP</label>
                            <input
                              readOnly
                              value={Number.isFinite(opValue) ? opValue.toFixed(2) : "0.00"}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3, background: "#fafafa" }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#666" }}>Payment Fee</label>
                            <input
                              readOnly
                              value={`€ ${Number.isFinite(paymentFee) ? paymentFee.toFixed(2) : "0.00"}`}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3, background: "#fafafa" }}
                            />
                          </div>

                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#666" }}>Sales Commission %</label>
                            <input
                              readOnly
                              value={`${Number.isFinite(salesCommission) ? (salesCommission * 100).toFixed(1) : "0.0"}%`}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3, background: "#fafafa" }}
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#1976d2" }}>Shipping Costs Net</label>
                            <input
                              type="number"
                              step="0.01"
                              value={ebayListingData[sku]?.shipping_costs_net ?? ""}
                              onChange={(e) => setEbayListingData(prev => ({
                                ...prev,
                                [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }), shipping_costs_net: e.target.value }
                              }))}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #1976d2", borderRadius: 3 }}
                              placeholder="0.00"
                            />
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#1976d2" }}>Selling Price Total</label>
                            <input
                              type="number"
                              step="0.01"
                              value={ebayListingData[sku]?.price || ""}
                              onChange={(e) => setEbayListingData(prev => ({
                                ...prev,
                                [sku]: { ...(prev[sku] || { quantity: "1", condition_id: "1000" }), price: e.target.value }
                              }))}
                              style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #1976d2", borderRadius: 3 }}
                              placeholder="29.99"
                            />
                          </div>
                          <div />

                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#2e7d32" }}>Net Profit</label>
                            <div style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #a5d6a7", borderRadius: 3, background: "#fff", color: "#2e7d32", fontWeight: "bold" }}>
                              € {Number.isFinite(netProfit) ? netProfit.toFixed(2) : "0.00"}
                            </div>
                          </div>
                          <div>
                            <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4, color: "#2e7d32" }}>Net Profit Margin</label>
                            <div style={{ width: "100%", padding: "6px", fontSize: 11, border: "1px solid #a5d6a7", borderRadius: 3, background: "#fff", color: "#2e7d32", fontWeight: "bold" }}>
                              {Number.isFinite(netProfitMargin) ? netProfitMargin.toFixed(1) : "0.0"}%
                            </div>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", gap: 8, alignItems: "end", marginBottom: 12 }}>
                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>Qty</label>
                          <input
                            type="number"
                            min="1"
                            value={ebayListingData[sku]?.quantity || "1"}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", condition_id: conditionFromProduct || "1000" }), quantity: e.target.value }
                            }))}
                            style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                          />
                        </div>

                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>Condition</label>
                          <select
                            value={ebayListingData[sku]?.condition_id || conditionFromProduct || "1000"}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1" }), condition_id: e.target.value }
                            }))}
                            style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
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
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>
                            Condition Note <span style={{ color: "#999", fontWeight: "normal" }}>(required if not new)</span>
                          </label>
                          <div style={{ display: "flex", gap: 6 }}>
                            <input
                              type="text"
                              value={ebayListingData[sku]?.condition_description || ""}
                              onChange={(e) => setEbayListingData(prev => ({
                                ...prev,
                                [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }), condition_description: e.target.value }
                              }))}
                              style={{ flex: 1, padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                              placeholder="Short condition details"
                            />
                            <button
                              onClick={() => handleConditionNoteAi(sku)}
                              disabled={ebayConditionNoteLoading[sku]}
                              style={{
                                padding: "6px 8px",
                                fontSize: 10,
                                border: "1px solid #bbb",
                                borderRadius: 3,
                                background: ebayConditionNoteLoading[sku] ? "#eee" : "#fff",
                                cursor: ebayConditionNoteLoading[sku] ? "not-allowed" : "pointer"
                              }}
                              title="Generate condition note from main images"
                            >
                              {ebayConditionNoteLoading[sku] ? "..." : "AI"}
                            </button>
                          </div>
                        </div>

                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>
                            EAN <span style={{ color: "#999", fontWeight: "normal" }}>(opt)</span>
                          </label>
                          <input
                            type="text"
                            value={ebayListingData[sku]?.ean || ""}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }), ean: e.target.value }
                            }))}
                            style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                            placeholder="e.g. 4005900071439"
                          />
                        </div>

                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>
                            Modified SKU <span style={{ color: "#999", fontWeight: "normal" }}>(opt)</span>
                          </label>
                          <input
                            type="text"
                            value={ebayListingData[sku]?.modified_sku || ""}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition_id: "1000" }), modified_sku: e.target.value }
                            }))}
                            style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                            placeholder={sku}
                            title={`Default: ${sku}`}
                          />
                        </div>
                      </div>

                      <div style={{ marginBottom: 12 }}>
                        <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>
                          Schedule Upload <span style={{ color: "#999", fontWeight: "normal" }}>(optional)</span>
                        </label>
                        <input
                          type="datetime-local"
                          value={ebayListingData[sku]?.schedule_date || ""}
                          onChange={(e) => setEbayListingData(prev => ({
                            ...prev,
                            [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition: "Neu" }), schedule_date: e.target.value }
                          }))}
                          style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                        />
                      </div>

                      {uploadProgress[sku]?.show && (
                        <div style={{
                          padding: "10px",
                          background: "#f0f8ff",
                          border: "1px solid #4a90e2",
                          borderRadius: 4,
                          marginBottom: 8,
                          marginTop: 8
                        }}>
                          <div style={{ fontSize: 10, fontWeight: "bold", marginBottom: 5, color: "#2c5282" }}>
                            {uploadProgress[sku].message}
                          </div>
                          <div style={{ background: "#e0e0e0", borderRadius: 8, height: 16, overflow: "hidden" }}>
                            <div style={{
                              background: "linear-gradient(90deg, #4a90e2, #357abd)",
                              height: "100%",
                              width: `${(uploadProgress[sku].step / uploadProgress[sku].total) * 100}%`,
                              transition: "width 0.3s ease",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              color: "white",
                              fontSize: 9,
                              fontWeight: "bold"
                            }}>
                              {uploadProgress[sku].step}/{uploadProgress[sku].total}
                            </div>
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => handleEbayCreateListing(sku)}
                        disabled={ebayCreatingListing[sku] || !ebayListingData[sku]?.price}
                        style={{
                          padding: "8px 12px",
                          fontSize: 11,
                          background: "#ff6b00",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: (ebayCreatingListing[sku] || !ebayListingData[sku]?.price) ? "not-allowed" : "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        {ebayCreatingListing[sku] ? "Creating..." : "📤 Create Listing"}
                      </button>
                      </div>
                      )}
                    </div>
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
                    const promptKey = getPromptKeyForImage(sku, img.filename);
                    const enhancingKey = `${sku}/${img.filename}`;
                    const isEnhancing = !!enhancingImages[enhancingKey];
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
                          onClick={async () => {
                            // Load current EAN and OP values
                            const details = await loadProductDetails(sku);
                            let ean = "";
                            let op = "";
                            
                            if (details?.categories) {
                              const eanCat = details.categories.find(c => c.name === "EAN");
                              if (eanCat) {
                                const eanField = eanCat.fields.find(f => f.name === "EAN");
                                ean = eanField?.value || "";
                              }
                              
                              const opCat = details.categories.find(c => c.name === "OP");
                              if (opCat) {
                                const opField = opCat.fields.find(f => f.name === "OP");
                                op = opField?.value || "";
                              }
                            }
                            
                            setPreviewEan(ean);
                            setPreviewOp(op);
                            openImagePreview(sku, img, "grid");
                          }}
                          style={{ all: "unset", cursor: "pointer", display: "block", position: "relative" }}
                          title={img.filename}
                        >
                          <img
                            src={img.thumb_url}
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
                          <div style={{ fontSize: 10, color: "#999", marginTop: 2, marginBottom: 4 }}>
                            {img.file_size_str || "N/A"}
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
                            <button
                              onClick={() => handleDeleteImage(sku, img.filename)}
                              style={{ 
                                padding: "2px 6px", 
                                fontSize: 11, 
                                cursor: "pointer",
                                background: "#dc3545",
                                color: "white",
                                border: "none",
                                borderRadius: 3,
                              }}
                              title="Delete image"
                            >
                              🗑️ Delete
                            </button>
                          </div>
                          {enhancePrompts.length > 0 && (
                            <div style={{ marginTop: 8, paddingTop: 6, borderTop: "1px dashed #e0e0e0" }}>
                              <div style={{ fontSize: 10, color: "#666", marginBottom: 4, textAlign: "center" }}>
                                Enhance {enhanceModel ? `(${enhanceModel})` : ""}
                              </div>
                              <div style={{ display: "flex", gap: 4, justifyContent: "center", flexWrap: "wrap", marginBottom: 6 }}>
                                {geminiModels.length > 1 && (
                                  <select
                                    value={selectedGeminiModel || ""}
                                    onChange={(e) => setSelectedGeminiModel(e.target.value)}
                                    style={{
                                      padding: "2px 6px",
                                      fontSize: 10,
                                      border: "1px solid #999",
                                      borderRadius: 3,
                                      background: "#f9f9f9",
                                      fontWeight: "500"
                                    }}
                                    title="Choose Gemini model for image generation"
                                  >
                                    {geminiModels.map(m => (
                                      <option key={m.id} value={m.id}>{m.name}</option>
                                    ))}
                                  </select>
                                )}
                                <select
                                  value={promptKey}
                                  onChange={(e) => {
                                    const key = `${sku}/${img.filename}`;
                                    setImagePromptSelection(prev => ({ ...prev, [key]: e.target.value }));
                                  }}
                                  style={{
                                    padding: "2px 6px",
                                    fontSize: 10,
                                    border: "1px solid #ccc",
                                    borderRadius: 3,
                                    maxWidth: 150
                                  }}
                                >
                                  {enhancePrompts.map(p => (
                                    <option key={p.key} value={p.key}>{p.label || p.key}</option>
                                  ))}
                                </select>
                                <button
                                  onClick={() => handleEnhanceImage(sku, img.filename)}
                                  disabled={isEnhancing || enhanceLoading}
                                  style={{
                                    padding: "2px 6px",
                                    fontSize: 10,
                                    cursor: (isEnhancing || enhanceLoading) ? "not-allowed" : "pointer",
                                    background: "#6a1b9a",
                                    color: "white",
                                    border: "none",
                                    borderRadius: 3
                                  }}
                                >
                                  {isEnhancing ? "Enhancing..." : "Enhance"}
                                </button>
                              </div>
                            </div>
                          )}
                          {/* eBay Image Order Numbers */}
                          <div style={{ marginTop: 8, paddingTop: 6, borderTop: "1px solid #e0e0e0" }}>
                            <div style={{ fontSize: 10, color: "#666", marginBottom: 4, textAlign: "center" }}>eBay Order</div>
                            <div style={{ display: "flex", gap: 3, justifyContent: "center", flexWrap: "wrap" }}>
                              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(num => {
                                const currentOrders = ebayImageOrders[sku] || {};
                                const isSelected = currentOrders[img.filename] === num;
                                const isUsedByOther = Object.keys(currentOrders).some(fn => fn !== img.filename && currentOrders[fn] === num);
                                
                                return (
                                  <button
                                    key={num}
                                    onClick={() => handleEbayImageOrderClick(sku, img.filename, num)}
                                    style={{
                                      width: 24,
                                      height: 24,
                                      padding: 0,
                                      fontSize: 10,
                                      fontWeight: isSelected ? "bold" : "normal",
                                      cursor: "pointer",
                                      background: isSelected ? "#2196F3" : isUsedByOther ? "#e0e0e0" : "white",
                                      color: isSelected ? "white" : isUsedByOther ? "#999" : "#333",
                                      border: isSelected ? "2px solid #1976d2" : "1px solid #ccc",
                                      borderRadius: 3,
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "center"
                                    }}
                                    title={isUsedByOther ? "Already assigned to another image" : isSelected ? "Click to unassign" : `Assign order ${num}`}
                                  >
                                    {num}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );
      })}

      <Modal open={!!preview} onClose={() => setPreview(null)}>
        {preview && (() => {
          const images = preview.images?.length
            ? preview.images
            : (items.find(item => item.sku === preview.sku)?.data?.images || []);
          const safeIndex = Math.max(0, Math.min(preview.index ?? 0, Math.max(images.length - 1, 0)));
          const currentImage = images[safeIndex] || preview.img;
          const order = currentImage ? (ebayImageOrders[preview.sku]?.[currentImage.filename] || "N/A") : "N/A";
          const openOriginal = currentImage?.original_url || currentImage?.full_url || currentImage?.preview_url || currentImage?.thumb_url;

          return (
            <div>
              <div style={{ fontFamily: "ui-monospace", marginBottom: 8, fontWeight: "bold" }}>
                {preview.sku} • {currentImage?.filename || "(no image)"} • Order: {order}
              </div>

              {currentImage ? (
                <img
                  src={currentImage.full_url || currentImage.preview_url || currentImage.original_url || currentImage.thumb_url}
                  alt={currentImage.filename}
                  style={{ maxWidth: "85vw", maxHeight: "60vh", display: "block" }}
                />
              ) : (
                <div style={{ padding: 20, color: "#999" }}>No image available</div>
              )}

              <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <button
                  onClick={() => setPreview(prev => ({ ...prev, index: Math.max(0, (prev?.index ?? 0) - 1) }))}
                  disabled={(preview.index ?? 0) <= 0}
                  style={{ padding: "4px 10px", fontSize: 12, cursor: (preview.index ?? 0) <= 0 ? "not-allowed" : "pointer" }}
                >
                  Prev
                </button>
                <button
                  onClick={() => setPreview(prev => ({ ...prev, index: Math.min((images.length || 1) - 1, (prev?.index ?? 0) + 1) }))}
                  disabled={(preview.index ?? 0) >= (images.length - 1)}
                  style={{ padding: "4px 10px", fontSize: 12, cursor: (preview.index ?? 0) >= (images.length - 1) ? "not-allowed" : "pointer" }}
                >
                  Next
                </button>
                <div style={{ fontSize: 12, color: "#666" }}>
                  {images.length > 0 ? `${safeIndex + 1} / ${images.length}` : "0 / 0"}
                </div>
                {openOriginal && (
                  <a href={openOriginal} target="_blank" rel="noreferrer" style={{ padding: "4px 10px", fontSize: 12 }}>
                    Open original
                  </a>
                )}
              </div>

              {images.length > 1 && (
                <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {images.map((img, idx) => (
                    <img
                      key={`${img.filename}-${idx}`}
                      src={img.thumb_url || img.preview_url || img.original_url}
                      alt={img.filename}
                      onClick={() => setPreview(prev => ({ ...prev, index: idx }))}
                      style={{
                        width: 60,
                        height: 60,
                        objectFit: "cover",
                        borderRadius: 4,
                        border: idx === safeIndex ? "2px solid #1976d2" : "1px solid #ddd",
                        cursor: "pointer"
                      }}
                    />
                  ))}
                </div>
              )}

              {preview.context === "grid" && (
                <div style={{ marginTop: 16, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
                  <div style={{ flex: "1 1 200px" }}>
                    <label style={{ display: "block", fontSize: 12, marginBottom: 4, fontWeight: "bold" }}>EAN:</label>
                    <input
                      type="text"
                      value={previewEan}
                      onChange={(e) => setPreviewEan(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 8px",
                        fontSize: 14,
                        border: "1px solid #ccc",
                        borderRadius: 4
                      }}
                      placeholder="Enter EAN"
                    />
                  </div>
                  <div style={{ flex: "1 1 200px" }}>
                    <label style={{ display: "block", fontSize: 12, marginBottom: 4, fontWeight: "bold" }}>OP:</label>
                    <input
                      type="text"
                      value={previewOp}
                      onChange={(e) => setPreviewOp(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "6px 8px",
                        fontSize: 14,
                        border: "1px solid #ccc",
                        borderRadius: 4
                      }}
                      placeholder="Enter OP"
                    />
                  </div>
                  <button
                    onClick={async () => {
                      setPreviewSaving(true);
                      try {
                        const sku = preview.sku;
                        const updates = {};
                        if (previewEan !== "") updates.EAN = { EAN: previewEan };
                        if (previewOp !== "") updates.OP = { OP: previewOp };

                        if (Object.keys(updates).length === 0) {
                          alert("No changes to save");
                          setPreviewSaving(false);
                          return;
                        }

                        const res = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ sku, updates })
                        });
                        const result = await res.json();

                        if (result.success) {
                          alert("✅ Saved successfully");
                          const detailsRes = await fetch(`/api/skus/${encodeURIComponent(sku)}/details`);
                          if (detailsRes.ok) {
                            const detailsData = await detailsRes.json();
                            setProductDetails(prev => ({ ...prev, [sku]: detailsData }));
                          }

                          setPreview(null);
                        } else {
                          alert(result.message || "Failed to save");
                        }
                      } catch (e) {
                        alert(`Error: ${e.message}`);
                      } finally {
                        setPreviewSaving(false);
                      }
                    }}
                    disabled={previewSaving}
                    style={{
                      padding: "6px 16px",
                      fontSize: 14,
                      background: previewSaving ? "#ccc" : "#4CAF50",
                      color: "white",
                      border: "none",
                      borderRadius: 4,
                      cursor: previewSaving ? "not-allowed" : "pointer",
                      fontWeight: "bold"
                    }}
                  >
                    {previewSaving ? "Saving..." : "💾 Save"}
                  </button>
                </div>
              )}
            </div>
          );
        })()}
      </Modal>
    </div>
  );
}

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

  // eBay Enrichment state
  const [selectedSkusForEbayEnrichment, setSelectedSkusForEbayEnrichment] = useState(new Set()); // Set of SKUs for eBay enrichment
  const [ebayEnrichmentInProgress, setEbayEnrichmentInProgress] = useState(false);
  const [ebayEnrichmentResults, setEbayEnrichmentResults] = useState(null);

  // eBay state
  const [ebayExpanded, setEbayExpanded] = useState({}); // { sku: boolean }
  const [ebaySchemas, setEbaySchemas] = useState({}); // { sku: schema }
  const [ebayFields, setEbayFields] = useState({}); // { sku: fields }
  const [ebayImageOrders, setEbayImageOrders] = useState({}); // { sku: { filename: order_number } }
  const [ebayValidations, setEbayValidations] = useState({}); // { sku: validation }
  const [ebayEnriching, setEbayEnriching] = useState({}); // { sku: boolean }
  const [ebayEditingFields, setEbayEditingFields] = useState({}); // { sku: boolean }
  const [ebayEditedFields, setEbayEditedFields] = useState({}); // { sku: { required: {}, optional: {} } }
  const [ebaySavingFields, setEbaySavingFields] = useState({}); // { sku: boolean }
  const [ebayListingData, setEbayListingData] = useState({}); // { sku: { price, quantity, condition, ean, modified_sku, schedule_date } }
  const [ebayCreatingListing, setEbayCreatingListing] = useState({}); // { sku: boolean }
  const [uploadProgress, setUploadProgress] = useState({}); // { sku: { show, message, step, total } }

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

  const toNumber = (value) => {
    if (value === null || value === undefined) return 0;
    const cleaned = String(value).replace(/[^0-9,.-]/g, "").replace(",", ".");
    const parsed = parseFloat(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const toggleSkuForEnrichment = (sku) => {
    const newSet = new Set(selectedSkusForEnrichment);
    const newEbaySet = new Set(selectedSkusForEbayEnrichment);
    
    if (newSet.has(sku)) {
      newSet.delete(sku);
      newEbaySet.delete(sku);
    } else {
      newSet.add(sku);
      newEbaySet.add(sku);
    }
    
    setSelectedSkusForEnrichment(newSet);
    setSelectedSkusForEbayEnrichment(newEbaySet);
  };

  const toggleSkuForEbayEnrichment = (sku) => {
    const newSet = new Set(selectedSkusForEbayEnrichment);
    if (newSet.has(sku)) {
      newSet.delete(sku);
    } else {
      newSet.add(sku);
    }
    setSelectedSkusForEbayEnrichment(newSet);
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
    if (selectedSkusForEbayEnrichment.size === 0) {
      alert("No SKUs selected for eBay enrichment");
      return;
    }

    setEbayEnrichmentInProgress(true);
    const results = {};
    let succeeded = 0;
    let failed = 0;

    try {
      for (const sku of selectedSkusForEbayEnrichment) {
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

      setEbayEnrichmentResults({ total: selectedSkusForEbayEnrichment.size, succeeded, failed, results });
      setTimeout(() => setEbayEnrichmentResults(null), 10000);
      setSelectedSkusForEbayEnrichment(new Set());
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setEbayEnrichmentInProgress(false);
    }
  };

  // eBay functions
  const loadEbayData = async (sku) => {
    try {
      // Load product details first (needed for Total Cost Net and OP calculations)
      await loadProductDetails(sku);
      
      // Load eBay image orders
      await loadEbayImageOrders(sku);
      
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
      
      const requestBody = {
        sku,
        price: parseFloat(listingData.price),
        quantity: parseInt(listingData.quantity || "1"),
        condition: listingData.condition || "1000"
      };
      
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
        if (data.listing_id) {
          setUploadProgress(prev => ({ ...prev, [sku]: { show: true, message: "✅ Listing created successfully!", step: 4, total: 4 } }));
          await new Promise(resolve => setTimeout(resolve, 1000));
          alert(`✅ Listing created! ID: ${data.listing_id}`);
          window.open(`https://www.ebay.de/itm/${data.listing_id}`, "_blank");
        }
      } else {
        const err = await res.json();
        setUploadProgress(prev => ({ ...prev, [sku]: { show: false, message: "", step: 0, total: 0 } }));
        alert(`❌ ${err.detail || "Listing creation failed"}`);
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

  // Calculate top padding for fixed ribbons
  const topPadding = (() => {
    const hasImageRibbon = totalSelectedImages > 0;
    const hasEnrichmentRibbon = selectedSkusForEnrichment.size > 0;
    const hasEbayRibbon = selectedSkusForEbayEnrichment.size > 0;
    
    const ribbonCount = [hasImageRibbon, hasEnrichmentRibbon, hasEbayRibbon].filter(Boolean).length;
    return ribbonCount * 50;
  })();

  return (
    <div style={{ width: "100%", maxWidth: "2200px", margin: "0 auto", padding: "0 16px", boxSizing: "border-box", paddingTop: topPadding, transition: "padding-top 0.2s ease" }}>
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
            🤖 AI Product Details: {selectedSkusForEnrichment.size} SKU(s)
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

      {/* eBay Enrichment Panel */}
      {selectedSkusForEbayEnrichment.size > 0 && (
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
          background: "#fff3e0",
          padding: 6,
          borderRadius: 0,
          marginBottom: 8,
          border: "none",
          borderBottom: "2px solid #FF9800",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: 4, fontSize: 11 }}>
            ⭐ eBay Fields: {selectedSkusForEbayEnrichment.size} SKU(s)
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button
              onClick={() => {
                if (selectedSkusForEbayEnrichment.size === items.length) {
                  setSelectedSkusForEbayEnrichment(new Set());
                } else {
                  const allSkus = new Set(items.map(item => item.sku));
                  setSelectedSkusForEbayEnrichment(allSkus);
                }
              }}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: "#F57C00",
                color: "white",
                border: "none",
                borderRadius: 3,
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              {selectedSkusForEbayEnrichment.size === items.length ? "Clear" : "All"}
            </button>
            <button
              onClick={handleEbayEnrichAll}
              disabled={ebayEnrichmentInProgress || selectedSkusForEbayEnrichment.size === 0}
              style={{
                padding: "4px 8px",
                fontSize: 11,
                background: ebayEnrichmentInProgress ? "#ccc" : "#FF9800",
                color: "white",
                border: "none",
                borderRadius: 3,
                fontWeight: "bold",
                cursor: ebayEnrichmentInProgress || selectedSkusForEbayEnrichment.size === 0 ? "not-allowed" : "pointer",
              }}
            >
              {ebayEnrichmentInProgress ? "Enriching..." : "⭐ Enrich"}
            </button>
            <button
              onClick={() => setSelectedSkusForEbayEnrichment(new Set())}
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
              Clear
            </button>
          </div>
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
            {ebayEnrichmentResults.failed === 0 ? "✅" : "⚠️"} eBay Enrichment: {ebayEnrichmentResults.succeeded} succeeded, {ebayEnrichmentResults.failed} failed
          </div>
          {Object.entries(ebayEnrichmentResults.results).map(([s, res]) => (
            <div key={s} style={{ fontSize: 12, padding: "4px 0", color: res.success ? "#FF9800" : "#FF3D00" }}>
              {s}: {res.success ? res.message : res.message}
            </div>
          ))}
        </div>
      )}

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
                        disabled={ebayEnriching[sku] || ebayEditingFields[sku]}
                        style={{
                          flex: 1,
                          minWidth: 120,
                          padding: "8px 12px",
                          fontSize: 11,
                          background: "#28a745",
                          color: "white",
                          border: "none",
                          borderRadius: 4,
                          cursor: (ebayEnriching[sku] || ebayEditingFields[sku]) ? "not-allowed" : "pointer",
                          fontWeight: "bold"
                        }}
                      >
                        {ebayEnriching[sku] ? "🤖 Enriching..." : "🤖 Auto-Fill"}
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
                                          <select
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
                                          >
                                            <option value="">-- Select --</option>
                                            {fieldOptions.map(opt => (
                                              <option key={opt} value={opt}>{opt}</option>
                                            ))}
                                          </select>
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
                                          <select
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
                                          >
                                            <option value="">-- Select --</option>
                                            {fieldOptions.map(opt => (
                                              <option key={opt} value={opt}>{opt}</option>
                                            ))}
                                          </select>
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

                    {/* Create Listing Section */}
                    <div style={{ borderTop: "1px solid #e0e0e0", paddingTop: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: "bold", marginBottom: 8, color: "#ff6b00" }}>Create eBay Listing</div>

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
                                [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition: "1000" }), shipping_costs_net: e.target.value }
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
                                [sku]: { ...(prev[sku] || { quantity: "1", condition: "1000" }), price: e.target.value }
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

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8, alignItems: "end", marginBottom: 12 }}>
                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>Qty</label>
                          <input
                            type="number"
                            min="1"
                            value={ebayListingData[sku]?.quantity || "1"}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", condition: conditionFromProduct || "1000" }), quantity: e.target.value }
                            }))}
                            style={{ width: "100%", padding: "6px", fontSize: 10, border: "1px solid #ddd", borderRadius: 3 }}
                          />
                        </div>

                        <div>
                          <label style={{ fontSize: 9, fontWeight: "600", display: "block", marginBottom: 4 }}>Condition</label>
                          <select
                            value={ebayListingData[sku]?.condition || conditionFromProduct || "1000"}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1" }), condition: e.target.value }
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
                            EAN <span style={{ color: "#999", fontWeight: "normal" }}>(opt)</span>
                          </label>
                          <input
                            type="text"
                            value={ebayListingData[sku]?.ean || ""}
                            onChange={(e) => setEbayListingData(prev => ({
                              ...prev,
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition: "1000" }), ean: e.target.value }
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
                              [sku]: { ...(prev[sku] || { price: "", quantity: "1", condition: "1000" }), modified_sku: e.target.value }
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

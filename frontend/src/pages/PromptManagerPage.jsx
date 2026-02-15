import React, { useEffect, useMemo, useState } from "react";

export default function PromptManagerPage() {
  const [prompts, setPrompts] = useState([]);
  const [model, setModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const promptKeys = useMemo(() => prompts.map((p) => p.key), [prompts]);

  const loadPrompts = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/images/enhance/prompts/manage");
      if (!res.ok) {
        throw new Error("Failed to load prompts");
      }
      const data = await res.json();
      setModel(data.model || "");
      setPrompts(Array.isArray(data.prompts) ? data.prompts : []);
    } catch (e) {
      setError(e.message || "Failed to load prompts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrompts();
  }, []);

  const addPrompt = () => {
    let i = 1;
    while (promptKeys.includes(`prompt ${i}`)) {
      i += 1;
    }
    setPrompts((prev) => [...prev, { key: `prompt ${i}`, label: `Prompt ${i}`, text: "" }]);
  };

  const removePrompt = (index) => {
    setPrompts((prev) => prev.filter((_, i) => i !== index));
  };

  const movePrompt = (index, direction) => {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= prompts.length) return;
    setPrompts((prev) => {
      const next = [...prev];
      const temp = next[index];
      next[index] = next[nextIndex];
      next[nextIndex] = temp;
      return next;
    });
  };

  const updatePrompt = (index, field, value) => {
    setPrompts((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const validatePrompts = () => {
    const trimmed = prompts.map((p) => ({
      key: String(p.key || "").trim(),
      text: String(p.text || "").trim(),
    }));

    if (trimmed.length === 0) {
      return "Add at least one prompt";
    }

    const keys = trimmed.map((p) => p.key);
    const uniqueKeys = new Set(keys);
    if (keys.some((k) => !k)) {
      return "Each prompt must have a key";
    }
    if (uniqueKeys.size !== keys.length) {
      return "Prompt keys must be unique";
    }
    if (trimmed.some((p) => !p.text)) {
      return "Each prompt must have text";
    }

    return "";
  };

  const savePrompts = async () => {
    const validationError = validatePrompts();
    if (validationError) {
      alert(validationError);
      return;
    }

    setSaving(true);
    setError("");
    try {
      const payload = {
        prompts: prompts.map((p) => ({
          key: String(p.key || "").trim(),
          text: String(p.text || "").trim(),
        })),
      };

      const res = await fetch("/api/images/enhance/prompts/manage", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || "Failed to save prompts");
      }

      const data = await res.json();
      setModel(data.model || "");
      setPrompts(Array.isArray(data.prompts) ? data.prompts : []);
    } catch (e) {
      setError(e.message || "Failed to save prompts");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <h3 style={{ marginTop: 0 }}>Prompt Manager</h3>
      <div style={{ color: "#666", marginBottom: 12 }}>
        Model: {model || "unknown"}
      </div>

      {error && (
        <div style={{ marginBottom: 12, color: "#b00020" }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={addPrompt} disabled={loading || saving}>
          Add Prompt
        </button>
        <button onClick={savePrompts} disabled={loading || saving}>
          {saving ? "Saving..." : "Save Prompts"}
        </button>
        <button onClick={loadPrompts} disabled={loading || saving}>
          Reload
        </button>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {prompts.map((prompt, index) => (
            <div
              key={`${prompt.key}-${index}`}
              style={{
                border: "1px solid #ddd",
                padding: 12,
                borderRadius: 6,
                background: "#fafafa",
              }}
            >
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <input
                  type="text"
                  value={prompt.key || ""}
                  onChange={(e) => updatePrompt(index, "key", e.target.value)}
                  style={{ flex: 1, padding: 6 }}
                  placeholder="prompt key"
                />
                <button onClick={() => movePrompt(index, -1)} disabled={index === 0}>
                  Up
                </button>
                <button
                  onClick={() => movePrompt(index, 1)}
                  disabled={index === prompts.length - 1}
                >
                  Down
                </button>
                <button onClick={() => removePrompt(index)}>
                  Delete
                </button>
              </div>
              <textarea
                value={prompt.text || ""}
                onChange={(e) => updatePrompt(index, "text", e.target.value)}
                rows={6}
                style={{ width: "100%", padding: 8, resize: "vertical" }}
                placeholder="Prompt text"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

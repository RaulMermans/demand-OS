"use client";

import { useEffect, useState } from "react";
import { getStoredApiKey, setStoredApiKey, clearStoredApiKey } from "@/lib/apiKey";

export default function ApiKeyInput() {
  const [key, setKey] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setKey(getStoredApiKey());
  }, []);

  const handleSave = () => {
    if (key.trim()) {
      setStoredApiKey(key.trim());
    } else {
      clearStoredApiKey();
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClear = () => {
    clearStoredApiKey();
    setKey("");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "24px",
      }}
    >
      <div style={{ fontWeight: 600, fontSize: "13px", marginBottom: "4px" }}>
        API Key (optional)
      </div>
      <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "12px" }}>
        Only required when <code>DEMANDOS_API_KEY</code> is set on the backend.
        Stored in sessionStorage only — cleared when this tab closes.
      </div>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Enter API key…"
          style={{
            flex: 1,
            padding: "6px 10px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--text-primary)",
            fontSize: "13px",
            fontFamily: "monospace",
          }}
        />
        <button
          onClick={handleSave}
          style={{
            padding: "6px 14px",
            borderRadius: "6px",
            fontSize: "12px",
            cursor: "pointer",
            border: "1px solid var(--accent)",
            background: "var(--accent)",
            color: "#fff",
            fontWeight: 600,
          }}
        >
          {saved ? "Saved" : "Save"}
        </button>
        {key && (
          <button
            onClick={handleClear}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              fontSize: "12px",
              cursor: "pointer",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-secondary)",
            }}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

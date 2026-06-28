"use client";

import { useState, useRef } from "react";
import PageHeader from "@/components/PageHeader";
import ApiKeyInput from "@/components/ApiKeyInput";
import StatusBadge from "@/components/StatusBadge";
import { getStoredApiKey } from "@/lib/apiKey";

const ENTITY_TYPES = [
  "products",
  "stores",
  "suppliers",
  "orders",
  "inventory_snapshots",
  "promotions",
  "purchase_orders",
];

interface UploadError {
  row: number;
  field: string;
  message: string;
}

interface ValidationResult {
  entity_type: string;
  filename: string;
  row_count: number;
  valid_row_count: number;
  invalid_row_count: number;
  errors: UploadError[];
  warnings: UploadError[];
  is_valid: boolean;
}

interface UploadRun {
  upload_id: string;
  entity_type: string;
  filename: string;
  status: string;
  row_count: number;
  valid_row_count: number;
  invalid_row_count: number;
  created_at: string;
}

interface UploadResult {
  records_inserted: number;
  upload_id: string;
}

export default function CsvUploadPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const [entityType, setEntityType] = useState("products");
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [history, setHistory] = useState<UploadRun[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadHistory() {
    const r = await fetch(`${base}/api/csv/uploads`);
    if (r.ok) {
      const d = await r.json();
      setHistory(d.uploads || []);
      setHistoryLoaded(true);
    }
  }

  async function handleValidate() {
    if (!file) return;
    setValidating(true);
    setError("");
    setValidation(null);
    setUploadResult(null);
    const fd = new FormData();
    fd.append("entity_type", entityType);
    fd.append("file", file);
    try {
      const r = await fetch(`${base}/api/csv/validate`, { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok) {
        setError(d.detail || "Validation failed");
      } else {
        setValidation(d);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setValidating(false);
    }
  }

  async function handleUpload() {
    if (!file || !validation?.is_valid) return;
    setUploading(true);
    setError("");
    const fd = new FormData();
    fd.append("entity_type", entityType);
    fd.append("file", file);
    const headers: Record<string, string> = {};
    const apiKey = getStoredApiKey();
    if (apiKey) headers["X-DemandOS-API-Key"] = apiKey;
    try {
      const r = await fetch(`${base}/api/csv/upload`, {
        method: "POST",
        body: fd,
        headers,
      });
      const d = await r.json();
      if (!r.ok) {
        setError(
          typeof d.detail === "string"
            ? d.detail
            : d.detail?.message || "Upload failed"
        );
      } else {
        setUploadResult(d);
        loadHistory();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setUploading(false);
    }
  }

  const pill = (text: string, color: string) => (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "10px",
        fontSize: "11px",
        fontWeight: 600,
        background: color,
        color: "#fff",
      }}
    >
      {text}
    </span>
  );

  return (
    <div>
      <PageHeader
        title="CSV Upload"
        subtitle="Import raw operational records for validation and pipeline processing. Derived forecasts, risk scores, and recommendations are rejected."
        badge="Raw records only · 2 MB prototype limit"
      />
      <div className="notice notice-warning" style={{ marginBottom: "20px" }}>
        Derived or precomputed fields—features, forecasts, risk scores, safety stock,
        or reorder quantities—are rejected. Download the selected entity template first.
      </div>
      <ApiKeyInput />

      {/* Entity selector */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <label style={{ fontWeight: 600, fontSize: "13px", display: "block", marginBottom: "8px" }}>
          Entity Type
        </label>
        <select
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setValidation(null);
            setUploadResult(null);
          }}
          style={{
            padding: "8px 12px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--text-primary)",
            fontSize: "13px",
            marginBottom: "12px",
          }}
        >
          {ENTITY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace("_", " ")}
            </option>
          ))}
        </select>

        <a
          href={`${base}/api/csv/templates/${entityType}`}
          target="_blank"
          rel="noreferrer"
          style={{ fontSize: "12px", color: "var(--accent)", display: "block" }}
        >
          View template for {entityType} →
        </a>
      </div>

      {/* File upload */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <label style={{ fontWeight: 600, fontSize: "13px", display: "block", marginBottom: "8px" }}>
          CSV File (max 2 MB)
        </label>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] || null);
            setValidation(null);
            setUploadResult(null);
          }}
          style={{ marginBottom: "12px", fontSize: "13px" }}
        />

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={handleValidate}
            disabled={!file || validating}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "13px",
              cursor: file && !validating ? "pointer" : "not-allowed",
            }}
          >
            {validating ? "Validating…" : "Validate"}
          </button>

          <button
            onClick={handleUpload}
            disabled={!validation?.is_valid || uploading}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: validation?.is_valid ? "var(--accent)" : "var(--surface-2)",
              border: "none",
              color: validation?.is_valid ? "#fff" : "var(--text-secondary)",
              fontSize: "13px",
              cursor: validation?.is_valid && !uploading ? "pointer" : "not-allowed",
            }}
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>

      </div>

      {error && (
        <div
          style={{
            background: "var(--danger-soft)",
            border: "1px solid #fecdd3",
            borderRadius: "6px",
            padding: "12px 16px",
            marginBottom: "16px",
            fontSize: "13px",
            color: "var(--danger)",
          }}
        >
          {error}
        </div>
      )}

      {/* Validation summary */}
      {validation && (
        <div
          style={{
            background: "var(--surface)",
            border: `1px solid ${validation.is_valid ? "#2a5a2a" : "#5a2a2a"}`,
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "20px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "10px" }}>
            Validation Result{" "}
            {validation.is_valid
              ? <StatusBadge value="completed" label="Valid" />
              : <StatusBadge value="failed" label="Invalid" />}
          </div>
          <div style={{ display: "flex", gap: "24px", fontSize: "13px", marginBottom: "10px" }}>
            <span>Rows: <strong>{validation.row_count}</strong></span>
            <span style={{ color: "var(--success)" }}>Valid: <strong>{validation.valid_row_count}</strong></span>
            {validation.invalid_row_count > 0 && (
              <span style={{ color: "var(--danger)" }}>Invalid: <strong>{validation.invalid_row_count}</strong></span>
            )}
          </div>
          {validation.errors.length > 0 && (
            <>
              <div style={{ fontWeight: 600, fontSize: "12px", marginBottom: "6px" }}>
                Errors ({validation.errors.length})
              </div>
              <table style={{ width: "100%", fontSize: "11px", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>Row</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>Field</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.errors.slice(0, 50).map((e, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "4px 8px", color: "var(--text-secondary)" }}>{e.row}</td>
                      <td style={{ padding: "4px 8px" }}>{e.field}</td>
                      <td style={{ padding: "4px 8px", color: "var(--danger)" }}>{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}

      {/* Upload result */}
      {uploadResult && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid #2a5a2a",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "20px",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "8px" }}>
            Upload Complete {pill("SUCCESS", "#2a7a2a")}
          </div>
          <div style={{ fontSize: "13px", display: "flex", gap: "24px" }}>
            <span>Records inserted: <strong>{uploadResult.records_inserted}</strong></span>
            <span>Upload ID: <code style={{ fontSize: "11px" }}>{uploadResult.upload_id}</code></span>
          </div>
        </div>
      )}

      {/* Upload history */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "16px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ fontWeight: 600, fontSize: "14px" }}>Upload History</div>
          <button
            onClick={loadHistory}
            style={{
              fontSize: "12px",
              padding: "4px 10px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            Refresh
          </button>
        </div>

        {!historyLoaded ? (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
            Click Refresh to load upload history.
          </p>
        ) : history.length === 0 ? (
          <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
            No uploads yet.
          </p>
        ) : (
          <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Entity</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>File</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Status</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>Rows</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => (
                <tr key={r.upload_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "6px 8px" }}>{r.entity_type}</td>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)" }}>{r.filename}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {r.status === "completed"
                      ? pill("completed", "#2a7a2a")
                      : r.status === "failed"
                      ? pill("failed", "#8b2222")
                      : pill(r.status, "#555")}
                  </td>
                  <td style={{ padding: "6px 8px", textAlign: "right" }}>{r.row_count}</td>
                  <td style={{ padding: "6px 8px", color: "var(--text-secondary)" }}>
                    {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

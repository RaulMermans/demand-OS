"use client";

import { useState } from "react";

interface PipelineControlButtonProps {
  label: string;
  onClick?: () => Promise<void>;
  onRun?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
  running?: boolean;
  status?: string;
  result?: string | null;
  error?: string | null;
}

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  primary: {
    background: "var(--accent)",
    color: "#fff",
    border: "1px solid var(--accent)",
  },
  secondary: {
    background: "var(--surface)",
    color: "var(--text-primary)",
    border: "1px solid var(--border)",
  },
  danger: {
    background: "var(--danger)",
    color: "#fff",
    border: "1px solid var(--danger)",
  },
};

const STATUS_COLORS: Record<string, string> = {
  completed: "#15803d",
  success:   "#15803d",
  not_run:   "var(--text-secondary)",
  running:   "#a16207",
  failed:    "#dc2626",
  unknown:   "var(--text-secondary)",
};

export default function PipelineControlButton({
  label,
  onClick,
  onRun,
  disabled = false,
  variant = "primary",
  running: externalRunning,
  status,
  result,
  error: externalError,
}: PipelineControlButtonProps) {
  const [internalRunning, setInternalRunning] = useState(false);
  const [internalError, setInternalError] = useState<string | null>(null);

  const isAsync = typeof onClick === "function";
  const running = isAsync ? internalRunning : (externalRunning ?? false);
  const error = isAsync ? internalError : externalError;

  const handleClick = async () => {
    if (running || disabled) return;
    if (isAsync) {
      setInternalRunning(true);
      setInternalError(null);
      try {
        await onClick();
      } catch (err) {
        setInternalError(err instanceof Error ? err.message : "An error occurred.");
      } finally {
        setInternalRunning(false);
      }
    } else if (onRun) {
      onRun();
    }
  };

  if (status !== undefined) {
    const statusColor = STATUS_COLORS[status ?? "not_run"] ?? "var(--text-secondary)";
    const dot =
      status === "completed" || status === "success" ? "✓" :
      status === "failed" ? "✗" :
      status === "running" ? "…" : "○";

    return (
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "16px",
          marginBottom: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "16px", color: statusColor, width: "20px", textAlign: "center" }}>
            {dot}
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: "13px" }}>{label}</div>
            {status && (
              <div style={{ fontSize: "11px", color: statusColor, marginTop: "2px" }}>
                {status === "not_run" ? "Not run yet" : status}
              </div>
            )}
          </div>
          <button
            onClick={handleClick}
            disabled={running || disabled}
            style={{
              padding: "6px 16px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: running || disabled ? "not-allowed" : "pointer",
              border: "1px solid var(--accent)",
              background: running || disabled ? "var(--surface-2)" : "var(--accent)",
              color: running || disabled ? "var(--text-secondary)" : "#fff",
              opacity: running || disabled ? 0.6 : 1,
              transition: "all 0.15s",
            }}
          >
            {running ? "Running…" : "Run"}
          </button>
        </div>
        {result && (
          <div
            style={{
              marginTop: "8px",
              padding: "8px 12px",
              background: "var(--surface-2)",
              borderRadius: "4px",
              fontSize: "11px",
              color: "var(--text-secondary)",
              fontFamily: "monospace",
              wordBreak: "break-all",
            }}
          >
            {result}
          </div>
        )}
        {error && (
          <div
            style={{
              marginTop: "8px",
              padding: "8px 12px",
              background: "rgba(220,38,38,0.08)",
              borderRadius: "4px",
              fontSize: "11px",
              color: "#dc2626",
              fontFamily: "monospace",
              wordBreak: "break-all",
            }}
          >
            {error}
          </div>
        )}
      </div>
    );
  }

  const base = VARIANT_STYLES[variant];
  const isOff = running || disabled;

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={isOff}
        style={{
          ...base,
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 20px",
          borderRadius: "8px",
          fontSize: "13px",
          fontWeight: 600,
          cursor: isOff ? "not-allowed" : "pointer",
          opacity: isOff ? 0.6 : 1,
          transition: "opacity 0.15s, transform 0.12s",
        }}
      >
        {running && (
          <span
            style={{
              width: "14px",
              height: "14px",
              border: "2px solid rgba(255,255,255,0.4)",
              borderTopColor: "#fff",
              borderRadius: "50%",
              display: "inline-block",
              animation: "spin 0.7s linear infinite",
              flexShrink: 0,
            }}
          />
        )}
        {running ? "Running…" : label}
      </button>
      {error && (
        <div
          style={{
            marginTop: "8px",
            padding: "8px 12px",
            background: "rgba(220,38,38,0.08)",
            border: "1px solid rgba(220,38,38,0.2)",
            borderRadius: "6px",
            fontSize: "12px",
            color: "#dc2626",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}

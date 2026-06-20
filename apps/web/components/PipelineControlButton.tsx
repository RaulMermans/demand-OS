"use client";

interface PipelineControlButtonProps {
  label: string;
  status?: string;
  running: boolean;
  disabled?: boolean;
  onRun: () => void;
  result?: string | null;
  error?: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "#15803d",
  success: "#15803d",
  not_run: "var(--text-secondary)",
  running: "#a16207",
  failed: "#dc2626",
  unknown: "var(--text-secondary)",
};

export default function PipelineControlButton({
  label,
  status,
  running,
  disabled,
  onRun,
  result,
  error,
}: PipelineControlButtonProps) {
  const statusColor = STATUS_COLORS[status ?? "not_run"] ?? "var(--text-secondary)";
  const dot = status === "completed" || status === "success" ? "✓" : status === "failed" ? "✗" : status === "running" ? "…" : "○";

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
          onClick={onRun}
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

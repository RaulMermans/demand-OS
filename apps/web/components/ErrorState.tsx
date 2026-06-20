"use client";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  message = "Failed to load data.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      style={{
        padding: "24px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: "4px solid #ef4444",
        borderRadius: "8px",
        display: "flex",
        alignItems: "flex-start",
        gap: "12px",
      }}
    >
      <div style={{ color: "#ef4444", fontWeight: 700, fontSize: "16px" }}>✕</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, marginBottom: "4px" }}>Error</div>
        <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{message}</div>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              marginTop: "12px",
              padding: "6px 14px",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "12px",
            }}
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

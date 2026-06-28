"use client";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      style={{
        padding: "20px 24px",
        background: "#fff1f2",
        border: "1px solid #fecdd3",
        borderLeft: "4px solid var(--danger)",
        borderRadius: "10px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
        <span
          style={{
            color: "var(--danger)",
            fontWeight: 700,
            fontSize: "16px",
            flexShrink: 0,
            marginTop: "1px",
          }}
        >
          ✕
        </span>
        <div>
          <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--danger)", marginBottom: "4px" }}>
            Error
          </div>
          <div style={{ fontSize: "13px", color: "#6b1e29" }}>{message}</div>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            alignSelf: "flex-start",
            padding: "6px 16px",
            borderRadius: "7px",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
            border: "1px solid var(--danger)",
            background: "transparent",
            color: "var(--danger)",
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
}

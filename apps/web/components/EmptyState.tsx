"use client";

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "60px 24px",
        color: "var(--text-secondary)",
      }}
    >
      <div style={{ fontSize: "32px", marginBottom: "12px", opacity: 0.4 }}>○</div>
      <div style={{ fontWeight: 600, fontSize: "16px", color: "var(--text-primary)", marginBottom: "8px" }}>
        {title}
      </div>
      {message && (
        <div style={{ fontSize: "13px", maxWidth: "400px", margin: "0 auto" }}>{message}</div>
      )}
      {action && <div style={{ marginTop: "20px" }}>{action}</div>}
    </div>
  );
}

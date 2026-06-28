"use client";

import Link from "next/link";

interface EmptyStateProps {
  title: string;
  message?: string;
  action?: { label: string; href: string };
}

export default function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "56px 24px",
        color: "var(--text-secondary)",
        background: "var(--surface-2)",
        border: "1px dashed var(--border-strong)",
        borderRadius: "12px",
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          display: "grid",
          placeItems: "center",
          margin: "0 auto 14px",
          borderRadius: "10px",
          background: "var(--accent-soft)",
          color: "var(--accent)",
          fontSize: "18px",
        }}
      >
        ○
      </div>
      <div
        style={{
          fontWeight: 600,
          fontSize: "15px",
          color: "var(--text-primary)",
          marginBottom: "8px",
        }}
      >
        {title}
      </div>
      {message && (
        <div style={{ fontSize: "13px", maxWidth: "400px", margin: "0 auto" }}>
          {message}
        </div>
      )}
      {action && (
        <div style={{ marginTop: "20px" }}>
          <Link
            href={action.href}
            style={{
              display: "inline-block",
              padding: "8px 20px",
              borderRadius: "8px",
              background: "var(--accent)",
              color: "#fff",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            {action.label}
          </Link>
        </div>
      )}
    </div>
  );
}

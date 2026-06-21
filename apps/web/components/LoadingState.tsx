"use client";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = "Loading..." }: LoadingStateProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "42px 20px",
        color: "var(--text-secondary)",
        fontSize: "14px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
      }}
    >
      <div
        style={{
          width: "20px",
          height: "20px",
          border: "2px solid var(--border)",
          borderTopColor: "var(--accent)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      {message}
    </div>
  );
}

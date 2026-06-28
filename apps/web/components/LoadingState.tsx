"use client";

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "56px 24px",
        gap: "16px",
        color: "var(--text-secondary)",
        fontSize: "14px",
      }}
    >
      <div
        style={{
          width: "28px",
          height: "28px",
          border: "3px solid var(--border)",
          borderTopColor: "var(--accent)",
          borderRadius: "50%",
          animation: "spin 0.75s linear infinite",
        }}
      />
      <span>{message}</span>
    </div>
  );
}

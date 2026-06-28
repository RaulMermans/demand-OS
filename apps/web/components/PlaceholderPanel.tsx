interface PlaceholderPanelProps {
  title: string;
  message?: string;
}

export default function PlaceholderPanel({ title, message }: PlaceholderPanelProps) {
  return (
    <div
      style={{
        background: "var(--scaffold-bg)",
        border: "1px solid var(--scaffold-border)",
        borderRadius: "12px",
        padding: "32px 28px",
      }}
    >
      <div
        style={{
          display: "inline-block",
          padding: "3px 10px",
          borderRadius: "6px",
          fontSize: "10px",
          fontWeight: 700,
          background: "var(--scaffold-border)",
          color: "var(--scaffold-text)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: "14px",
        }}
      >
        Coming soon
      </div>
      <div
        style={{
          fontSize: "16px",
          fontWeight: 700,
          color: "var(--scaffold-text)",
          marginBottom: "8px",
        }}
      >
        {title}
      </div>
      {message && (
        <div
          style={{
            fontSize: "13px",
            color: "var(--scaffold-text)",
            opacity: 0.8,
            lineHeight: 1.6,
          }}
        >
          {message}
        </div>
      )}
    </div>
  );
}

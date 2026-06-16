interface PlaceholderPanelProps {
  title: string;
  sprint: string;
  description: string;
}

export default function PlaceholderPanel({
  title,
  sprint,
  description,
}: PlaceholderPanelProps) {
  return (
    <div>
      <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
        {title}
      </h2>
      <div
        style={{
          display: "inline-block",
          background: "var(--scaffold-bg)",
          color: "var(--scaffold-text)",
          border: "1px solid var(--scaffold-border)",
          borderRadius: "4px",
          padding: "2px 8px",
          fontSize: "11px",
          fontWeight: 600,
          marginBottom: "20px",
        }}
      >
        Activates in {sprint}
      </div>

      <div className="scaffold-banner">
        <strong>{title} — scaffold ready.</strong> No model has been trained and
        no data has been seeded yet. This page will be populated in {sprint}.
      </div>

      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "24px",
          color: "var(--text-secondary)",
          fontSize: "13px",
          lineHeight: "1.8",
        }}
      >
        <strong style={{ color: "var(--text-primary)" }}>What will appear here:</strong>
        <p style={{ marginTop: "8px", whiteSpace: "pre-line" }}>{description}</p>
      </div>
    </div>
  );
}

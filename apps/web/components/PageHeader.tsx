interface PageHeaderProps {
  title: string;
  subtitle?: string;
  kicker?: string;
  badge?: string;
}

export default function PageHeader({ title, subtitle, kicker, badge }: PageHeaderProps) {
  return (
    <header
      style={{
        marginBottom: "32px",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "16px",
        flexWrap: "wrap",
      }}
    >
      <div>
        {kicker && (
          <div
            style={{
              fontSize: "11px",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--accent)",
              marginBottom: "6px",
            }}
          >
            {kicker}
          </div>
        )}
        <h1
          style={{
            fontSize: "28px",
            fontWeight: 800,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            lineHeight: 1.15,
            margin: 0,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontSize: "14px",
              color: "var(--text-secondary)",
              marginTop: "6px",
              lineHeight: 1.5,
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {badge && (
        <span
          style={{
            display: "inline-block",
            padding: "4px 10px",
            borderRadius: "999px",
            fontSize: "11px",
            fontWeight: 600,
            background: "#e0e7ff",
            color: "#3730a3",
            flexShrink: 0,
            marginTop: "4px",
          }}
        >
          {badge}
        </span>
      )}
    </header>
  );
}

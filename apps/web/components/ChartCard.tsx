import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export default function ChartCard({ title, subtitle, children }: ChartCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        padding: "20px 20px 16px",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            fontWeight: 700,
            fontSize: "14px",
            color: "var(--text-primary)",
          }}
        >
          {title}
        </div>
        {subtitle && (
          <div
            style={{
              fontSize: "12px",
              color: "var(--text-secondary)",
              marginTop: "3px",
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

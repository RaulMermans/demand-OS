import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  children: ReactNode;
  subtitle?: string;
}

export default function ChartCard({ title, children, subtitle }: ChartCardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        padding: "20px",
        marginBottom: "24px",
      }}
    >
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontWeight: 600, fontSize: "13px" }}>{title}</div>
        {subtitle && (
          <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
            {subtitle}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}

"use client";

import type { RiskDriverEntry } from "@/lib/types";
import StatusBadge from "./StatusBadge";

const SEV_COLORS: Record<string, string> = {
  high:   "#dc2626",
  medium: "#d97706",
  low:    "#6b7280",
};

interface Props {
  drivers: RiskDriverEntry[];
  disclaimer?: string;
}

export default function RiskDriverList({ drivers, disclaimer }: Props) {
  if (!drivers || drivers.length === 0) {
    return (
      <div
        style={{
          padding: "24px",
          textAlign: "center",
          color: "var(--text-secondary)",
          fontSize: "13px",
          border: "1px dashed var(--border)",
          borderRadius: "8px",
        }}
      >
        No risk drivers available. Run the pipeline to compute risk scores.
      </div>
    );
  }

  const visible = drivers.slice(0, 5);

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {visible.map((entry, i) => (
          <div
            key={i}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              padding: "14px 16px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "8px",
                flexWrap: "wrap",
              }}
            >
              <StatusBadge value={entry.risk_tier} />
              <span style={{ fontSize: "13px", fontWeight: 600 }}>
                {entry.product_name ?? entry.product_id}
              </span>
              {entry.sku && (
                <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  ({entry.sku})
                </span>
              )}
              <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginLeft: "auto" }}>
                {entry.store_id}
              </span>
            </div>

            {entry.estimated_lost_sales != null && (
              <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                Est. exposure:{" "}
                <strong style={{ color: "var(--text-primary)" }}>
                  €{entry.estimated_lost_sales.toLocaleString()}
                </strong>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {entry.drivers.slice(0, 2).map((d, j) => (
                <div key={j} style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background: SEV_COLORS[d.severity] ?? "#6b7280",
                      flexShrink: 0,
                      marginTop: "5px",
                    }}
                  />
                  <div>
                    <span
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: SEV_COLORS[d.severity] ?? "var(--text-primary)",
                      }}
                    >
                      {d.name}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--text-secondary)",
                        marginLeft: "6px",
                      }}
                    >
                      {d.explanation}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {disclaimer && (
        <p
          style={{
            fontSize: "11px",
            color: "var(--text-secondary)",
            marginTop: "10px",
            fontStyle: "italic",
          }}
        >
          {disclaimer}
        </p>
      )}
    </div>
  );
}

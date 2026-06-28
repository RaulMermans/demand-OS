"use client";

import type { ReorderQueueItem } from "@/lib/types";
import StatusBadge from "./StatusBadge";

const URGENCY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high:     "#f97316",
  medium:   "#d97706",
  low:      "#16a34a",
};

interface Props {
  items: ReorderQueueItem[];
  limit?: number;
  compact?: boolean;
}

export default function ReorderQueueTable({ items, limit, compact = false }: Props) {
  const visible = limit ? items.slice(0, limit) : items;
  const pad = compact ? "5px 8px" : "9px 12px";

  if (!items || items.length === 0) {
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
        No open reorder recommendations. Run the pipeline to generate recommendations.
      </div>
    );
  }

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: compact ? "11px" : "12px",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Urgency", "Product", "Store", "Rec. units", "Est. cost", "Reason", "Status"].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: pad,
                    fontSize: "10px",
                    fontWeight: 700,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                    color: "var(--text-secondary)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((item, i) => (
              <tr
                key={item.recommendation_id}
                style={{
                  borderBottom: "1px solid var(--border)",
                  background: i % 2 === 1 ? "var(--surface-2)" : "transparent",
                }}
              >
                <td style={{ padding: pad }}>
                  <span
                    style={{
                      padding: "2px 7px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: 700,
                      background: `${URGENCY_COLORS[item.urgency] ?? "#6b7280"}22`,
                      color: URGENCY_COLORS[item.urgency] ?? "#6b7280",
                      textTransform: "uppercase",
                    }}
                  >
                    {item.urgency}
                  </span>
                </td>
                <td style={{ padding: pad, fontWeight: 500 }}>
                  <div>{item.product_name ?? item.product_id}</div>
                  {item.sku && (
                    <div style={{ fontSize: "10px", color: "var(--text-secondary)" }}>{item.sku}</div>
                  )}
                </td>
                <td style={{ padding: pad, color: "var(--text-secondary)" }}>{item.store_id}</td>
                <td style={{ padding: pad, fontWeight: 600, textAlign: "right" }}>
                  {item.recommended_units != null ? item.recommended_units.toLocaleString() : "—"}
                </td>
                <td style={{ padding: pad, textAlign: "right", whiteSpace: "nowrap" }}>
                  {item.estimated_order_cost != null
                    ? `€${item.estimated_order_cost.toLocaleString()}`
                    : "—"}
                </td>
                <td
                  style={{
                    padding: pad,
                    color: "var(--text-secondary)",
                    maxWidth: "200px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.reason || "—"}
                </td>
                <td style={{ padding: pad }}>
                  <StatusBadge value={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {limit && items.length > limit && (
        <p
          style={{
            fontSize: "11px",
            color: "var(--text-secondary)",
            marginTop: "8px",
            textAlign: "right",
          }}
        >
          Showing {limit} of {items.length} items
        </p>
      )}
    </div>
  );
}

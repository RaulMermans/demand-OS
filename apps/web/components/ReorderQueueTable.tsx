"use client";

import type { ReorderQueueItem } from "@/lib/types";

const URGENCY_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#16a34a",
};

const CONFIDENCE_LABELS: Record<string, string> = {
  review_now: "Review now",
  monitor: "Monitor",
  low_priority: "Low priority",
};

interface Props {
  items: ReorderQueueItem[];
  limit?: number;
  compact?: boolean;
}

export default function ReorderQueueTable({ items, limit, compact = false }: Props) {
  const visible = limit ? items.slice(0, limit) : items;

  if (!items || items.length === 0) {
    return (
      <div
        style={{
          padding: "20px",
          textAlign: "center",
          color: "var(--text-secondary)",
          fontSize: "13px",
          border: "1px dashed var(--border)",
          borderRadius: "6px",
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
              {[
                "Product",
                "SKU",
                "Store",
                "Urgency",
                "Units",
                "Est. Cost",
                "Lead (days)",
                "Action",
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: "left",
                    padding: compact ? "5px 8px" : "7px 10px",
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    fontSize: "10px",
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
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
                  background: i % 2 === 0 ? "transparent" : "var(--surface)",
                }}
              >
                <td style={{ padding: compact ? "5px 8px" : "8px 10px", fontWeight: 500 }}>
                  {item.product_name ?? item.product_id}
                </td>
                <td style={{ padding: compact ? "5px 8px" : "8px 10px", color: "var(--text-secondary)" }}>
                  {item.sku ?? "—"}
                </td>
                <td style={{ padding: compact ? "5px 8px" : "8px 10px", color: "var(--text-secondary)" }}>
                  {item.store_id}
                </td>
                <td style={{ padding: compact ? "5px 8px" : "8px 10px" }}>
                  <span
                    style={{
                      padding: "2px 7px",
                      borderRadius: "4px",
                      fontSize: "10px",
                      fontWeight: 700,
                      background: `${URGENCY_COLORS[item.urgency] ?? "#6b7280"}22`,
                      color: URGENCY_COLORS[item.urgency] ?? "#6b7280",
                      border: `1px solid ${URGENCY_COLORS[item.urgency] ?? "#6b7280"}44`,
                      textTransform: "uppercase",
                    }}
                  >
                    {item.urgency}
                  </span>
                </td>
                <td
                  style={{
                    padding: compact ? "5px 8px" : "8px 10px",
                    fontWeight: 600,
                    textAlign: "right",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.recommended_units != null
                    ? item.recommended_units.toLocaleString()
                    : "—"}
                </td>
                <td
                  style={{
                    padding: compact ? "5px 8px" : "8px 10px",
                    textAlign: "right",
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.estimated_order_cost != null
                    ? `€${item.estimated_order_cost.toLocaleString()}`
                    : "—"}
                </td>
                <td
                  style={{
                    padding: compact ? "5px 8px" : "8px 10px",
                    textAlign: "center",
                    color: "var(--text-secondary)",
                  }}
                >
                  {item.lead_time_days ?? "—"}
                </td>
                <td style={{ padding: compact ? "5px 8px" : "8px 10px" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      color:
                        item.confidence_label === "review_now"
                          ? "#dc2626"
                          : item.confidence_label === "monitor"
                          ? "#d97706"
                          : "var(--text-secondary)",
                    }}
                  >
                    {CONFIDENCE_LABELS[item.confidence_label] ?? item.confidence_label}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {limit && items.length > limit && (
        <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "8px", textAlign: "right" }}>
          Showing {limit} of {items.length} items
        </p>
      )}
    </div>
  );
}

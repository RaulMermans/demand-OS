"use client";

import LineChartPanel from "./LineChartPanel";
import type { InventoryTrendPoint } from "@/lib/types";

interface Props {
  series: InventoryTrendPoint[];
  height?: number;
}

const SERIES = [
  { key: "inventory_on_hand", label: "On hand", color: "#2563eb" },
  { key: "forecasted_demand", label: "Forecast demand", color: "#f59e0b", dashed: true },
  { key: "reorder_point", label: "Reorder point", color: "#dc2626", dashed: true },
  { key: "safety_stock", label: "Safety stock", color: "#16a34a", dashed: true },
];

export default function InventoryTrendChart({ series, height = 260 }: Props) {
  if (!series || series.length === 0) {
    return (
      <div
        style={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-secondary)",
          fontSize: "13px",
          border: "1px dashed var(--border)",
          borderRadius: "6px",
        }}
      >
        Run the pipeline to generate inventory trend data.
      </div>
    );
  }

  const data = series.map((p) => ({
    date: p.date.slice(5),
    inventory_on_hand: p.inventory_on_hand,
    forecasted_demand: p.forecasted_demand,
    reorder_point: p.reorder_point,
    safety_stock: p.safety_stock,
  }));

  return (
    <LineChartPanel
      data={data}
      series={SERIES}
      xKey="date"
      height={height}
      emptyMessage="Run the pipeline to generate inventory trend data."
      valueFormatter={(v) => v.toFixed(0)}
    />
  );
}

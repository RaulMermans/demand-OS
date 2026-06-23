"use client";

import LineChartPanel from "./LineChartPanel";
import type { InventoryTrendPoint } from "@/lib/types";

interface Props {
  series: InventoryTrendPoint[];
  height?: number;
}

const SERIES = [
  { key: "inventory_on_hand", label: "On hand", color: "#2563eb" },
  { key: "forecasted_demand", label: "Forecast demand", color: "#d97706", dashed: true },
  { key: "reorder_point", label: "Reorder point", color: "#dc2626", dashed: true },
  { key: "safety_stock", label: "Safety stock", color: "#7c3aed", dashed: true },
];

export default function InventoryTrendChart({ series, height = 240 }: Props) {
  const data = series.map((p) => ({
    date: p.date.slice(5), // "MM-DD"
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
      emptyMessage="No inventory trend data available. Run the pipeline to generate data."
      valueFormatter={(v) => v.toFixed(0)}
    />
  );
}

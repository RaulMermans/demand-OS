"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface DataPoint {
  name: string;
  value: number;
  color?: string;
}

interface Props {
  data: DataPoint[];
  height?: number;
  emptyMessage?: string;
  valueFormatter?: (v: number) => string;
}

export interface BarChartDatum extends DataPoint {}

export default function BarChartPanel({
  data,
  height = 200,
  emptyMessage = "No data available.",
  valueFormatter,
}: Props) {
  if (!data || data.length === 0) {
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
        {emptyMessage}
      </div>
    );
  }

  const fmt = valueFormatter ?? ((v: number) => String(v));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={fmt}
          width={40}
        />
        <Tooltip
          formatter={(val) => [fmt(Number(val)), "Count"]}
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            fontSize: "12px",
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color ?? "var(--accent)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

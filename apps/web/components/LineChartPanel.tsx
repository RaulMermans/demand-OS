"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Series {
  key: string;
  label: string;
  color: string;
  dashed?: boolean;
}

interface Props {
  data: Record<string, unknown>[];
  xKey: string;
  series: Series[];
  height?: number;
  emptyMessage?: string;
  valueFormatter?: (v: number) => string;
}

export interface LineChartSeries extends Series {}

export default function LineChartPanel({
  data,
  xKey,
  series,
  height = 240,
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

  const fmt = valueFormatter ?? ((v: number) => v.toFixed(1));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={fmt}
          width={36}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            fontSize: "11px",
          }}
          formatter={(val, name) => [fmt(Number(val)), String(name)]}
        />
        <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} iconType="line" />
        {series.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            name={s.label}
            stroke={s.color}
            strokeWidth={1.5}
            dot={false}
            strokeDasharray={s.dashed ? "4 4" : undefined}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

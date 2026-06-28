"use client";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  emptyMessage = "No data.",
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "32px",
          color: "var(--text-secondary)",
          fontSize: "13px",
          background: "var(--surface-2)",
          border: "1px dashed var(--border)",
          borderRadius: "8px",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "12px",
        }}
      >
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  textAlign: col.align ?? "left",
                  padding: "8px 12px",
                  fontSize: "11px",
                  fontWeight: 700,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  color: "var(--text-secondary)",
                  whiteSpace: "nowrap",
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              style={{
                borderBottom: "1px solid var(--border)",
                background: i % 2 === 1 ? "var(--surface-2)" : "transparent",
              }}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    textAlign: col.align ?? "left",
                    padding: "9px 12px",
                    color: "var(--text-primary)",
                    verticalAlign: "middle",
                  }}
                >
                  {col.render
                    ? col.render(row)
                    : row[col.key] != null
                    ? String(row[col.key])
                    : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

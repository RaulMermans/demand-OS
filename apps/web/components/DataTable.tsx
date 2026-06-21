"use client";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  align?: "left" | "right" | "center";
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
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  textAlign: col.align ?? "left",
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
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    textAlign: col.align ?? "left",
                  }}
                >
                  {col.render
                    ? col.render(row)
                    : (row[col.key] != null ? String(row[col.key]) : "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

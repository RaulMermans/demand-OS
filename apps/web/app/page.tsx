import PlaceholderPanel from "@/components/PlaceholderPanel";

export default function HomePage() {
  return (
    <div>
      <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "8px" }}>
        DemandOS
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Demand forecasting and inventory risk platform
      </p>

      <div className="scaffold-banner">
        <strong>Sprint 0 — Scaffold Ready.</strong> The platform architecture is
        in place. Use the sidebar to explore what each section will contain. Run{" "}
        <code>scripts/seed_demo_data.py</code> in Sprint 1 to begin generating
        data.
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
        }}
      >
        {[
          { label: "Products tracked", value: "—", note: "seeded in Sprint 1" },
          { label: "Stores", value: "—", note: "seeded in Sprint 1" },
          { label: "Orders (30d)", value: "—", note: "seeded in Sprint 1" },
          { label: "Critical risks", value: "—", note: "computed in Sprint 5" },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <div style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
              {item.label}
            </div>
            <div style={{ fontSize: "28px", fontWeight: 700, margin: "8px 0" }}>
              {item.value}
            </div>
            <div style={{ color: "var(--scaffold-text)", fontSize: "11px" }}>
              {item.note}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

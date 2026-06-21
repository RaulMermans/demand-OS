"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/overview", label: "Overview" },
  { href: "/forecasts", label: "Forecasts" },
  { href: "/risks", label: "Inventory Risk" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/model-performance", label: "Model Performance" },
  { href: "/data-health", label: "Data Health" },
  { href: "/pipeline", label: "Pipeline Controls" },
];

const ADVANCED_NAV_ITEMS = [
  { href: "/csv-upload", label: "CSV Upload" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/connectors", label: "Connectors" },
];

interface RuntimeInfo {
  runtime_mode?: string;
  demo_scale?: string;
  database?: string;
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    fetch(`${base}/api/readiness`)
      .then((r) => r.json())
      .then((data: RuntimeInfo) => setRuntime(data))
      .catch(() => null);
  }, []);

  const runtimeLabel =
    runtime?.runtime_mode === "vercel" ? "Vercel" : runtime?.runtime_mode === "local" ? "Local" : null;
  const scaleLabel =
    runtime?.demo_scale === "small" ? "Small" : runtime?.demo_scale === "full" ? "Full" : null;
  const dataLabel = runtime ? "Seeded" : null;

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Sidebar */}
      <nav
        style={{
          width: "220px",
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          padding: "24px 0",
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "0 20px 24px",
            borderBottom: "1px solid var(--border)",
            marginBottom: "16px",
          }}
        >
          <div style={{ fontWeight: 700, fontSize: "16px", color: "var(--accent)" }}>
            DemandOS
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
            Deployed MVP · Demo Mode
          </div>
        </div>

        <ul style={{ listStyle: "none", padding: "0 8px", flex: 1 }}>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  style={{
                    display: "block",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    color: active ? "var(--text-primary)" : "var(--text-secondary)",
                    background: active ? "var(--surface-2)" : "transparent",
                    fontWeight: active ? 600 : 400,
                    fontSize: "13px",
                    marginBottom: "2px",
                  }}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}

          <li style={{ marginTop: "12px", marginBottom: "4px", padding: "0 12px" }}>
            <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Advanced
            </span>
          </li>

          {ADVANCED_NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  style={{
                    display: "block",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    color: active ? "var(--text-primary)" : "var(--text-secondary)",
                    background: active ? "var(--surface-2)" : "transparent",
                    fontWeight: active ? 600 : 400,
                    fontSize: "13px",
                    marginBottom: "2px",
                  }}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Runtime status indicator */}
        {runtime && (
          <div
            style={{
              margin: "16px 12px 0",
              padding: "10px 12px",
              background: "var(--surface-2)",
              borderRadius: "6px",
              fontSize: "10px",
              color: "var(--text-secondary)",
              lineHeight: "1.6",
            }}
          >
            {runtimeLabel && (
              <div>
                <span style={{ opacity: 0.6 }}>Runtime:</span>{" "}
                <span style={{ fontWeight: 600 }}>{runtimeLabel}</span>
              </div>
            )}
            {scaleLabel && (
              <div>
                <span style={{ opacity: 0.6 }}>Demo scale:</span>{" "}
                <span style={{ fontWeight: 600 }}>{scaleLabel}</span>
              </div>
            )}
            <div>
              <span style={{ opacity: 0.6 }}>Data:</span>{" "}
              <span style={{ fontWeight: 600 }}>Seeded</span>
            </div>
          </div>
        )}
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
        {children}
      </main>
    </div>
  );
}

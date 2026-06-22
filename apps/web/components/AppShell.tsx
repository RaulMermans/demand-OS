"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: "⌂" },
  { href: "/overview", label: "Overview", icon: "◫" },
  { href: "/forecasts", label: "Forecasts", icon: "⌁" },
  { href: "/risks", label: "Inventory Risk", icon: "△" },
  { href: "/recommendations", label: "Recommendations", icon: "→" },
  { href: "/model-performance", label: "Model Performance", icon: "◇" },
  { href: "/data-science", label: "ML Insights", icon: "⬡" },
  { href: "/data-health", label: "Data Health", icon: "✓" },
  { href: "/pipeline", label: "Pipeline Controls", icon: "▷" },
];

const ADVANCED_NAV_ITEMS = [
  { href: "/csv-upload", label: "CSV Upload", icon: "↑" },
  { href: "/monitoring", label: "Monitoring", icon: "◎" },
  { href: "/scenarios", label: "Scenarios", icon: "↗" },
  { href: "/connectors", label: "Connectors", icon: "⌘" },
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
  return (
    <div className="app-shell">
      <nav className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <div className="brand-mark">D</div>
          <div>
            <div className="brand-name">DemandOS</div>
            <div className="brand-subtitle">Deployed MVP · public portfolio</div>
          </div>
        </div>

        <ul className="nav-list">
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href ||
              (item.href === "/overview" && pathname.startsWith("/products/"));
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`nav-link${active ? " active" : ""}`}
                >
                  <span className="nav-icon" aria-hidden>{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}

          <li className="nav-section">Advanced tools</li>

          {ADVANCED_NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`nav-link${active ? " active" : ""}`}
                >
                  <span className="nav-icon" aria-hidden>{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        {runtime && (
          <div className="runtime-card">
            <div className="runtime-title">
              <span className="runtime-dot" />
              Demo environment online
            </div>
            {runtimeLabel && (
              <div className="runtime-row">
                <span>Runtime</span>
                <strong>{runtimeLabel}</strong>
              </div>
            )}
            {scaleLabel && (
              <div className="runtime-row">
                <span>Dataset</span>
                <strong>{scaleLabel} · synthetic</strong>
              </div>
            )}
            <div className="runtime-row">
              <span>External actions</span>
              <strong>Disabled</strong>
            </div>
          </div>
        )}
      </nav>

      <main className="app-main">{children}</main>
    </div>
  );
}

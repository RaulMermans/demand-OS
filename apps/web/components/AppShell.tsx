"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/overview", label: "Overview" },
  { href: "/forecasts", label: "Forecasts" },
  { href: "/risks", label: "Inventory Risk" },
  { href: "/recommendations", label: "Recommendations" },
  { href: "/model-performance", label: "Model Performance" },
  { href: "/data-health", label: "Data Health" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

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
            Sprint 8 · API + Dashboard
          </div>
        </div>

        <ul style={{ listStyle: "none", padding: "0 8px" }}>
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
        </ul>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
        {children}
      </main>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const NAV = [
  {
    section: "Operate",
    items: [
      { href: "/", label: "Cockpit" },
      { href: "/risks", label: "Risk Board" },
      { href: "/recommendations", label: "Reorder Queue" },
      { href: "/forecasts", label: "Forecasts" },
      { href: "/scenarios", label: "Scenarios" },
    ],
  },
  {
    section: "Trust",
    items: [
      { href: "/model-performance", label: "Forecast Trust" },
      { href: "/data-health", label: "Data Quality" },
      { href: "/pipeline", label: "Pipeline Trace" },
    ],
  },
  {
    section: "Setup",
    items: [
      { href: "/csv-upload", label: "CSV Upload" },
      { href: "/connectors", label: "Data Sources" },
    ],
  },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        background: "var(--background)",
      }}
    >
      <nav
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          bottom: 0,
          width: "240px",
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          zIndex: 100,
          overflowY: "auto",
        }}
      >
        <div
          style={{
            padding: "20px 20px 16px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div
            style={{
              fontWeight: 800,
              fontSize: "17px",
              color: "var(--text-primary)",
              letterSpacing: "-0.02em",
            }}
          >
            DemandOS
          </div>
          <div
            style={{
              fontSize: "11px",
              color: "var(--text-secondary)",
              marginTop: "2px",
            }}
          >
            Inventory decision cockpit
          </div>
        </div>

        <div style={{ flex: 1, padding: "12px 8px" }}>
          {NAV.map((group) => (
            <div key={group.section} style={{ marginBottom: "20px" }}>
              <div
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--text-tertiary)",
                  padding: "0 12px",
                  marginBottom: "4px",
                }}
              >
                {group.section}
              </div>
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {group.items.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        style={{
                          display: "block",
                          padding: "7px 12px",
                          borderRadius: "7px",
                          fontSize: "13px",
                          fontWeight: active ? 600 : 400,
                          color: active ? "var(--accent)" : "var(--text-secondary)",
                          background: active ? "var(--accent-soft)" : "transparent",
                          textDecoration: "none",
                          transition: "background 0.12s, color 0.12s",
                        }}
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div
          style={{
            padding: "12px 16px 16px",
            borderTop: "1px solid var(--border)",
          }}
        >
          <span
            style={{
              display: "inline-block",
              padding: "3px 8px",
              borderRadius: "999px",
              fontSize: "10px",
              fontWeight: 600,
              background: "#e0e7ff",
              color: "#3730a3",
            }}
          >
            Synthetic demo · no external actions
          </span>
        </div>
      </nav>

      <main
        style={{
          marginLeft: "240px",
          flex: 1,
          padding: "32px 40px",
          minWidth: 0,
        }}
      >
        {children}
      </main>
    </div>
  );
}

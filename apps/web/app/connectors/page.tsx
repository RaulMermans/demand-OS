"use client";

import { useEffect, useState } from "react";

interface ConnectorInfo {
  connector_id: string;
  name: string;
  description: string;
  status: string;
  enabled: boolean;
  requires_credentials: string[];
  capabilities: string[];
  note: string;
}

const STATUS_STYLE: Record<string, { bg: string; color: string }> = {
  active: { bg: "#1a3a1a", color: "#4caf50" },
  disabled: { bg: "#2a2a2a", color: "#888" },
  config_ready: { bg: "#1a3a4a", color: "#7ac8ff" },
};

export default function ConnectorsPage() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [validateId, setValidateId] = useState("shopify");
  const [validateConfig, setValidateConfig] = useState('{\n  "SHOPIFY_STORE_URL": "",\n  "SHOPIFY_ACCESS_TOKEN": ""\n}');
  const [validateResult, setValidateResult] = useState<any>(null);
  const [dryRunResult, setDryRunResult] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${base}/api/connectors`).then((r) => r.json()),
      fetch(`${base}/api/connectors/status`).then((r) => r.json()),
    ]).then(([conn, stat]) => {
      setConnectors(conn.connectors || []);
      setStatus(stat);
      setLoading(false);
    });
  }, []);

  async function runValidate() {
    let cfg: any;
    try {
      cfg = JSON.parse(validateConfig);
    } catch {
      setValidateResult({ error: "Invalid JSON" });
      return;
    }
    const r = await fetch(`${base}/api/connectors/validate-config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ connector_id: validateId, config: cfg }),
    });
    setValidateResult(await r.json());
    setDryRunResult(null);
  }

  async function runDryRun() {
    let cfg: any;
    try {
      cfg = JSON.parse(validateConfig);
    } catch {
      setDryRunResult({ error: "Invalid JSON" });
      return;
    }
    const r = await fetch(`${base}/api/connectors/dry-run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ connector_id: validateId, config: cfg }),
    });
    setDryRunResult(await r.json());
    setValidateResult(null);
  }

  return (
    <div style={{ maxWidth: "900px" }}>
      <h1 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "6px" }}>Connectors</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px", fontSize: "13px" }}>
        Manage data source connectors. Real connectors (Shopify, WooCommerce) are disabled —
        no live API calls are made in this deployment.
      </p>

      {/* Status summary */}
      {status && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "16px 20px",
            marginBottom: "20px",
            display: "flex",
            gap: "32px",
            fontSize: "13px",
          }}
        >
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Active: </span>
            <strong>{status.total_active}</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Disabled: </span>
            <strong>{status.total_disabled}</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Live sync: </span>
            <strong style={{ color: "#f44336" }}>Off</strong>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: "12px", marginLeft: "auto" }}>
            {status.note}
          </div>
        </div>
      )}

      {/* Connector cards */}
      {loading ? (
        <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Loading…</p>
      ) : (
        <div style={{ display: "grid", gap: "12px", marginBottom: "24px" }}>
          {connectors.map((c) => {
            const style = STATUS_STYLE[c.status] || STATUS_STYLE.disabled;
            return (
              <div
                key={c.connector_id}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  padding: "16px 20px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: "14px", marginBottom: "4px" }}>
                      {c.name}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                      {c.description}
                    </div>
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", fontSize: "11px" }}>
                      {c.capabilities.map((cap) => (
                        <span
                          key={cap}
                          style={{
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: "var(--surface-2)",
                            color: "var(--text-secondary)",
                          }}
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "3px 10px",
                        borderRadius: "10px",
                        fontSize: "11px",
                        fontWeight: 700,
                        background: style.bg,
                        color: style.color,
                        textTransform: "uppercase",
                      }}
                    >
                      {c.status}
                    </span>
                    {c.requires_credentials.length > 0 && (
                      <div style={{ marginTop: "8px", fontSize: "11px", color: "var(--text-secondary)" }}>
                        Requires: {c.requires_credentials.join(", ")}
                      </div>
                    )}
                  </div>
                </div>
                {c.note && (
                  <div
                    style={{
                      marginTop: "10px",
                      padding: "8px 12px",
                      background: "var(--surface-2)",
                      borderRadius: "6px",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {c.note}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Config validation tool */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "20px",
        }}
      >
        <div style={{ fontWeight: 600, fontSize: "14px", marginBottom: "12px" }}>
          Config Validation Tool
        </div>
        <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "14px" }}>
          Test connector config shape. No credentials are stored or transmitted to any external API.
        </p>

        <div style={{ marginBottom: "12px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
            Connector
          </label>
          <select
            value={validateId}
            onChange={(e) => {
              setValidateId(e.target.value);
              setValidateResult(null);
              setDryRunResult(null);
              const examples: Record<string, string> = {
                shopify:
                  '{\n  "SHOPIFY_STORE_URL": "",\n  "SHOPIFY_ACCESS_TOKEN": ""\n}',
                woocommerce:
                  '{\n  "WOO_SITE_URL": "",\n  "WOO_CONSUMER_KEY": "",\n  "WOO_CONSUMER_SECRET": ""\n}',
              };
              setValidateConfig(examples[e.target.value] || "{}");
            }}
            style={{
              padding: "6px 10px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-primary)",
              fontSize: "13px",
            }}
          >
            <option value="shopify">Shopify</option>
            <option value="woocommerce">WooCommerce</option>
          </select>
        </div>

        <div style={{ marginBottom: "12px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "4px" }}>
            Config JSON (required keys only — values not stored)
          </label>
          <textarea
            value={validateConfig}
            onChange={(e) => setValidateConfig(e.target.value)}
            rows={5}
            style={{
              width: "100%",
              padding: "8px 10px",
              borderRadius: "4px",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
              color: "var(--text-primary)",
              fontSize: "12px",
              fontFamily: "monospace",
              resize: "vertical",
            }}
          />
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={runValidate}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Validate Config
          </button>
          <button
            onClick={runDryRun}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              color: "var(--text-primary)",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Dry Run
          </button>
        </div>

        {(validateResult || dryRunResult) && (
          <div
            style={{
              marginTop: "14px",
              padding: "12px",
              background: "var(--surface-2)",
              borderRadius: "6px",
              fontSize: "12px",
              fontFamily: "monospace",
              whiteSpace: "pre-wrap",
            }}
          >
            {JSON.stringify(validateResult || dryRunResult, null, 2)}
          </div>
        )}
      </div>
    </div>
  );
}

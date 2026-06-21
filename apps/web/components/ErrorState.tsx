"use client";

import Link from "next/link";

interface ErrorStateProps {
  message?: string;
  endpoint?: string;
  context?: string;
  onRetry?: () => void;
  isApiKeyError?: boolean;
  isUnavailable?: boolean;
}

export default function ErrorState({
  message = "Failed to load data.",
  endpoint,
  context,
  onRetry,
  isApiKeyError,
  isUnavailable,
}: ErrorStateProps) {
  const isKeyError =
    isApiKeyError ||
    message.toLowerCase().includes("api key") ||
    message.includes("401") ||
    message.includes("Unauthorized");

  const isOffline =
    isUnavailable ||
    message.toLowerCase().includes("failed to fetch") ||
    message.toLowerCase().includes("networkerror") ||
    message.toLowerCase().includes("connection refused");

  let title = "Error";
  let hint: string | null = null;

  if (isKeyError) {
    title = "API key required";
    hint = "Enter your DEMANDOS_API_KEY on the Pipeline Controls page to run write actions.";
  } else if (isOffline) {
    title = "Backend unavailable";
    hint = "The API is not reachable. Check your network or the deployed backend status.";
  } else if (
    message.toLowerCase().includes("no data") ||
    message.toLowerCase().includes("no_data")
  ) {
    title = "No data yet";
    hint = "Run the pipeline from Pipeline Controls to seed data.";
  }

  return (
    <div
      style={{
        padding: "20px 24px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderLeft: `4px solid ${isKeyError ? "#f59e0b" : isOffline ? "#6366f1" : "#ef4444"}`,
        borderRadius: "8px",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
        <div
          style={{
            color: isKeyError ? "#f59e0b" : isOffline ? "#6366f1" : "#ef4444",
            fontWeight: 700,
            fontSize: "16px",
            flexShrink: 0,
          }}
        >
          {isKeyError ? "⚠" : isOffline ? "○" : "✕"}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, marginBottom: "4px" }}>{title}</div>
          <div style={{ color: "var(--text-secondary)", fontSize: "13px" }}>{message}</div>

          {(endpoint || context) && (
            <div
              style={{
                marginTop: "8px",
                fontSize: "11px",
                color: "var(--text-secondary)",
                opacity: 0.7,
              }}
            >
              {context && <span>{context} · </span>}
              {endpoint && <code style={{ fontFamily: "monospace" }}>{endpoint}</code>}
            </div>
          )}

          {hint && (
            <div
              style={{
                marginTop: "10px",
                fontSize: "12px",
                color: "var(--text-secondary)",
                padding: "8px 10px",
                background: "var(--surface-2)",
                borderRadius: "4px",
              }}
            >
              {hint}
              {isKeyError && (
                <>
                  {" "}
                  <Link
                    href="/pipeline"
                    style={{ color: "var(--accent)", textDecoration: "underline" }}
                  >
                    Go to Pipeline Controls →
                  </Link>
                </>
              )}
              {!isKeyError && !isOffline && (
                <>
                  {" "}
                  <Link
                    href="/pipeline"
                    style={{ color: "var(--accent)", textDecoration: "underline" }}
                  >
                    Go to Pipeline Controls →
                  </Link>
                </>
              )}
            </div>
          )}

          {onRetry && (
            <button
              onClick={onRetry}
              style={{
                marginTop: "12px",
                padding: "6px 14px",
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
              }}
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

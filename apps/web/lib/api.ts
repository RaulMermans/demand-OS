const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<{ status: string; version: string }>("/health"),
  status: () => apiFetch<{ status: string; pipeline_ready: boolean }>("/api/status"),
  overview: () => apiFetch<{ status: string; summary: Record<string, unknown> }>("/api/overview"),
  dataHealth: () => apiFetch<{ status: string; checks: unknown[] }>("/api/data-health"),
  forecasts: () => apiFetch<{ status: string }>("/api/forecasts"),
  risks: () => apiFetch<{ status: string }>("/api/risks"),
  recommendations: () => apiFetch<{ status: string }>("/api/recommendations"),
  metrics: () => apiFetch<{ status: string }>("/api/metrics"),
};

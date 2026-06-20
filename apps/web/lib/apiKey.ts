/**
 * Session-scoped API key storage for DemandOS pipeline controls.
 *
 * The key is stored in sessionStorage — cleared when the browser tab closes.
 * It is NEVER stored in localStorage, cookies, or environment variables.
 * Only sent on write/control requests (POST/PATCH pipeline endpoints).
 */

const SESSION_KEY = "demandos-api-key";

export function getStoredApiKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(SESSION_KEY) ?? "";
}

export function setStoredApiKey(key: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SESSION_KEY, key);
}

export function clearStoredApiKey(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(SESSION_KEY);
}

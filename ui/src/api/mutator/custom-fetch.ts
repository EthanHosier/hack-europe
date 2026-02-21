/**
 * Custom fetch mutator for Orval react-query client.
 * - Dev: requests go to /api (Vite proxy forwards to backend).
 * - Production: set VITE_API_URL to your API origin (e.g. https://hack-europe.vercel.app)
 *   so requests go to the real API instead of the frontend origin.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? "";

function getRequestUrl(url: string): string {
  if (!API_BASE) return url; // dev: /api/health → proxy
  const base = API_BASE.replace(/\/$/, "");
  const path = url.replace(/^\/api/, ""); // /api/health → /health
  return `${base}${path}`;
}

export const customFetch = async <T>(
  config: {
    url: string;
    method: string;
    signal?: AbortSignal;
    params?: Record<string, unknown>;
    data?: unknown;
  },
  _options?: unknown
): Promise<{ status: number; data: T }> => {
  const { url, method, signal, data } = config;
  const requestUrl = getRequestUrl(url);
  const response = await fetch(requestUrl, {
    method,
    signal,
    headers: {
      "Content-Type": "application/json",
    },
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });

  const body =
    response.status === 204 ||
    response.status === 205 ||
    response.status === 304
      ? null
      : await response.text();
  const parsed = body ? (JSON.parse(body) as T) : (null as T);

  return { status: response.status, data: parsed };
};

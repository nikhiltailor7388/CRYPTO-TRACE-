const configuredBaseUrl = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  ''
).trim().replace(/\/+$/, '')

/**
 * Uses Vite's local proxy when no public API URL is configured. On Vercel,
 * VITE_API_BASE_URL (or the legacy VITE_API_URL alias) points directly at
 * the backend when the frontend is not using the local Vite proxy.
 */
export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return configuredBaseUrl ? `${configuredBaseUrl}${normalizedPath}` : normalizedPath
}

export function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

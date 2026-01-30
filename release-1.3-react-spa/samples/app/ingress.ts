
/**
 * Derive the SPA basename under Home Assistant ingress.
 *
 * Heuristic:
 * - If path contains `/api/hassio_ingress/`, take everything up to and including the token segment.
 * - Otherwise return "/" (root served).
 *
 * Examples:
 * /api/hassio_ingress/ABC123/              -> /api/hassio_ingress/ABC123
 * /api/hassio_ingress/ABC123/proxies/1     -> /api/hassio_ingress/ABC123
 */
export function getIngressBasename(pathname: string = window.location.pathname): string {
  const marker = "/api/hassio_ingress/";
  const idx = pathname.indexOf(marker);
  if (idx === -1) return "/";

  const after = pathname.slice(idx + marker.length); // token + rest
  const token = after.split("/").filter(Boolean)[0];
  if (!token) return "/";

  return `${marker}${token}`;
}

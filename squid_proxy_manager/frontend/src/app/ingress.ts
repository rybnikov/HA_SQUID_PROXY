export function getIngressBasename(pathname: string = window.location.pathname): string {
  const marker = '/api/hassio_ingress/';
  const idx = pathname.indexOf(marker);
  if (idx == -1) {
    return '/';
  }

  const after = pathname.slice(idx + marker.length);
  const token = after.split('/').filter(Boolean)[0];
  if (!token) {
    return '/';
  }

  return `${marker}${token}`;
}

export function getApiBasePath(pathname: string = window.location.pathname): string {
  const base = getIngressBasename(pathname);
  if (base === '/') {
    return '/api';
  }
  return `${base}/api`;
}

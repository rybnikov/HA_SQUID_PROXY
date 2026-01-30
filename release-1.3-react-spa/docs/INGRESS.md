
# Home Assistant Ingress — SPA Notes

## Goals
- App works when served under an ingress subpath, e.g.:
  `/api/hassio_ingress/<token>/`
- Deep linking and browser refresh on nested routes does not 404
- Static assets resolve correctly under nested routes
- UI works in an iframe (HA sidebar panel)

## Routing basename (runtime derived)
Use a helper to derive basename at runtime from the current URL.

See sample:
- `samples/app/ingress.ts`
- `samples/app/router.tsx`

## Vite asset base
To avoid absolute asset URLs, configure Vite base to be relative.
Common approach:
- `base: "./"`

Also ensure:
- No hardcoded `/assets/...` in code
- Prefer import-based asset references

## Server fallback
Ensure the server serving the SPA returns `index.html` for unknown routes.
Nginx example:
```
location / {
  try_files $uri /index.html;
}
```

## iframe constraints
- Avoid assumptions about `window.top` navigation
- Ensure modals/menus are viewport-safe (Radix UI portals recommended)

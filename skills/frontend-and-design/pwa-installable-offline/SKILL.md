---
name: pwa-installable-offline
category: frontend-and-design
description: >-
  Make a Vite web app installable and offline-capable with vite-plugin-pwa
  (Workbox under the hood). Use this to add a web app manifest, generate a
  service worker, precache the build, add runtime caching for API/images, wire
  an "update available" prompt, and pass a Lighthouse PWA / installability
  audit. Reach for this whenever someone says "make it installable", "add to
  home screen", "works offline", "PWA", "service worker", or "manifest".
when_to_use:
  - Turning an existing Vite app (React, Vue, Svelte, vanilla) into an installable PWA
  - Adding offline support so the app loads with no network after first visit
  - Generating a valid web app manifest with icons so the browser shows an install prompt
  - Wiring a user-facing "new version available — reload" prompt (registerType prompt)
  - Adding runtime caching for API calls, fonts, or remote images via Workbox
  - Debugging why a PWA won't install or the service worker won't update
when_not_to_use:
  - Non-Vite bundlers (Next.js, webpack, CRA) — use Serwist / next-pwa or the workbox-webpack-plugin instead
  - You only need a static hero/landing page with no offline story — use quick-landing or web-artifacts-builder
  - Native app packaging (App Store / Play Store) — use Capacitor or Tauri, not a PWA
  - Pure performance tuning of an already-shipped bundle — use performance-optimization
keywords:
  - pwa
  - service-worker
  - offline
  - manifest
  - vite-plugin-pwa
  - workbox
  - installable
  - add-to-home-screen
  - precache
  - runtime-caching
  - registersw
  - lighthouse
similar_to:
  - performance-optimization
  - web-artifacts-builder
  - frontend-ui-engineering
  - shadcn-tailwind-v4-stack
inputs_needed: An existing Vite project (any framework); a 512x512 source icon/logo; the app name + theme color; which origins/endpoints should be cached at runtime.
produces: A configured vite.config with VitePWA, a generated manifest.webmanifest, a Workbox service worker, PWA icons, an SW registration + update-prompt hook, and a Lighthouse-passing installable/offline build.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# PWA: Installable + Offline (vite-plugin-pwa)

Add installability and offline support to a Vite app. `vite-plugin-pwa` wraps
Workbox: it generates the service worker, injects the precache manifest of your
build assets, and (optionally) generates the web app manifest + registration
script for you.

## When to use

Use when an existing **Vite** app needs to (a) show a browser install prompt /
"Add to Home Screen" and (b) keep working after the network drops. If the app
isn't on Vite, this skill's plugin doesn't apply — see `when_not_to_use`.

## Prerequisites

- A working Vite build (`vite build` succeeds). Node 18+.
- The plugin (dev dependency):

  ```bash
  npm i -D vite-plugin-pwa
  # optional icon generator (creates all icon sizes from one source):
  npm i -D @vite-pwa/assets-generator
  ```

- **HTTPS or localhost.** Service workers only register on `https://` or
  `http://localhost`. Testing over a LAN IP (`http://192.168.x.x`) will NOT
  register the SW — use `localhost` or a tunnel with TLS.
- One square source icon, ideally **512×512 PNG** with transparent or solid bg.

## Recipe 1 — Minimal auto-updating PWA

`registerType: 'autoUpdate'` = the new SW takes over silently on next load. Best
for content sites where a forced refresh is fine.

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    // ...your framework plugin (react(), vue(), etc.)
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'robots.txt'],
      manifest: {
        name: 'My VCCP App',
        short_name: 'VCCP App',
        description: 'What the app does in one line.',
        theme_color: '#0b0b0b',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          // maskable icon → Android adaptive-icon safe zone:
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
})
```

Icons live in `public/` (so `pwa-192x192.png` resolves to `/pwa-192x192.png`).
Generate every size from one source:
`npx @vite-pwa/assets-generator --preset minimal-2023 public/logo.svg`.

With `registerType: 'autoUpdate'` and `injectRegister: 'auto'` (the default),
the plugin injects the registration script — you write **no** JS to register.

## Recipe 2 — Prompt the user to update

`registerType: 'prompt'` (the default) shows *your* UI when a new version is
ready, and only swaps in the SW when the user clicks reload. Use for apps where
a surprise refresh would lose unsaved state.

Import the plugin's **virtual module** to drive your own toast/banner:

```ts
// src/pwa.ts  (vanilla — works in any framework)
import { registerSW } from 'virtual:pwa-register'

const updateSW = registerSW({
  onNeedRefresh() {
    // Show "New version available" UI with a Reload button.
    if (confirm('New version available. Reload?')) updateSW(true)
  },
  onOfflineReady() {
    // Show a one-time "Ready to work offline" toast.
    console.log('App ready to work offline')
  },
})
```

React apps can use the framework hook instead:

```tsx
import { useRegisterSW } from 'virtual:pwa-register/react'

export function ReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW()

  if (!offlineReady && !needRefresh) return null
  return (
    <div role="alert">
      {needRefresh ? 'New content available.' : 'Ready to work offline.'}
      {needRefresh && <button onClick={() => updateServiceWorker(true)}>Reload</button>}
      <button onClick={() => { setOfflineReady(false); setNeedRefresh(false) }}>Close</button>
    </div>
  )
}
```

Vue/Svelte have `virtual:pwa-register/vue` and `/svelte`. For **TS types** on
the virtual modules, add to `vite-env.d.ts`:

```ts
/// <reference types="vite-plugin-pwa/client" />
```

(Use `vite-plugin-pwa/react`, `/vue`, or `/svelte` for the framework hooks.)

## Recipe 3 — Runtime caching (APIs, fonts, images)

`globPatterns` precaches your own build output. Third-party/remote requests need
Workbox `runtimeCaching`. This is `generateSW` mode config:

```ts
workbox: {
  globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
  navigateFallback: '/index.html',   // SPA: serve app shell for unknown routes
  runtimeCaching: [
    {
      urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
      handler: 'NetworkFirst',       // fresh when online, cache when offline
      options: {
        cacheName: 'api-cache',
        networkTimeoutSeconds: 5,
        expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 },
        cacheableResponse: { statuses: [0, 200] },
      },
    },
    {
      urlPattern: ({ request }) => request.destination === 'image',
      handler: 'CacheFirst',         // images rarely change → serve from cache
      options: {
        cacheName: 'images',
        expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 30 },
      },
    },
  ],
}
```

Handler cheat sheet: `NetworkFirst` (APIs, freshness matters), `CacheFirst`
(hashed/immutable assets, images), `StaleWhileRevalidate` (fonts, CSS you want
instant but eventually fresh).

Need custom SW logic (push, background sync)? Switch to
`strategies: 'injectManifest'` with `srcDir: 'src'`, `filename: 'sw.ts'`, write
your own `sw.ts`, and call `precacheAndRoute(self.__WB_MANIFEST)`.

## Verify

1. **Build + preview over the SW-eligible origin:**

   ```bash
   npm run build && npm run preview   # serves on http://localhost:4173
   ```

   The dev server does *not* emit a full SW by default. To test the SW in `vite
   dev`, add `devOptions: { enabled: true }` to the VitePWA config.

2. **DevTools → Application:**
   - *Manifest* pane: name, icons, theme color all present, no errors.
   - *Service Workers* pane: one activated + running worker.
   - Look for an install icon in the address bar (or Chrome menu → "Install…").

3. **Offline test:** DevTools → Network → set to *Offline* → reload. The app
   shell and precached routes must still load.

4. **Lighthouse:** run the *Progressive Web App* / installability audit — it
   flags missing manifest fields, non-maskable icons, and no offline start_url.

## Pitfalls

- **Only localhost/HTTPS registers a SW.** A LAN IP silently no-ops — use
  `localhost`, `vite preview`, or a TLS tunnel.
- **No SW in `vite dev` by default**, so you'll debug a "broken" PWA that's fine
  in prod. Add `devOptions.enabled` while testing, or test against `vite preview`.
- **Stale service worker.** With `autoUpdate` the new SW may wait until all tabs
  close. During dev, in DevTools → Application → Service Workers, tick *Update
  on reload* + *Bypass for network*, or hit "Unregister".
- **Missing `maskable` icon** → Android crops your icon into a circle with ugly
  padding, and Lighthouse dings installability. Provide a `purpose: 'maskable'`
  512 icon with a safe zone.
- **`start_url` / `display` wrong** → no install prompt. Needs `display:
  'standalone'` (or `fullscreen`/`minimal-ui`) and a valid same-origin
  `start_url`.
- **SPA deep links 404 offline** without `navigateFallback: '/index.html'`.
- **`globPatterns` too narrow.** Fonts (`.woff2`) or `.json` data not in the
  glob won't be precached, so offline breaks. Workbox runtime caching only
  handles GET — API POSTs won't work offline without background-sync.
- **Icons must be in `public/`** — a manifest icon path that 404s kills the
  install prompt.

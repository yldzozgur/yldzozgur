---
title: "Service worker caching: the strategies that make apps load faster."
description: "The five service worker caching strategies, when to use each, and how to implement them with Workbox."
pubDate: 2026-03-09
tags: ["Architecture"]
draft: false
---

A service worker is a script that runs in the browser background, separate from the page. It can intercept network requests and respond from cache, making apps load instantly even on slow connections. The trick is choosing the right caching strategy for each type of resource.

## The five strategies

**Cache First (Cache Falling Back to Network)**

Check the cache first. If the response is there, return it without hitting the network. Only go to the network if the cache misses.

Best for: static assets with long-lived URLs (CSS, JS bundles with content hashes), images, fonts.

```javascript
// In service worker
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.open('static-v1').then(cache =>
      cache.match(event.request).then(cached =>
        cached ?? fetch(event.request).then(response => {
          cache.put(event.request, response.clone());
          return response;
        })
      )
    )
  );
});
```

**Network First (Network Falling Back to Cache)**

Try the network first. If it succeeds, return the fresh response and update the cache. If the network fails, fall back to the cached version.

Best for: API responses where freshness matters but offline access is better than nothing.

**Stale While Revalidate**

Return the cached version immediately (even if stale), then fetch a fresh version from the network in the background and update the cache for next time.

Best for: non-critical resources where you want both speed and eventual freshness. Blog post HTML, non-personalized API data.

**Network Only**

Always go to the network. No caching. Use for requests that must be fresh: payment processing, authentication endpoints.

**Cache Only**

Always serve from cache. Fails if not cached. Useful for assets precached during service worker installation.

## Workbox: don't write it by hand

The manual implementations get complex quickly. Workbox (from Google) provides well-tested, configurable implementations of all these strategies:

```javascript
// service-worker.js
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';
import { registerRoute } from 'workbox-routing';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { ExpirationPlugin } from 'workbox-expiration';

// Cache-first for fonts and static assets
registerRoute(
  ({ request }) => request.destination === 'font',
  new CacheFirst({
    cacheName: 'fonts',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 365 }), // 1 year
    ],
  })
);

// Network-first for API calls, fall back to cache
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [
      new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 60 * 5 }), // 5 min
    ],
  })
);

// Stale-while-revalidate for page HTML
registerRoute(
  ({ request }) => request.destination === 'document',
  new StaleWhileRevalidate({ cacheName: 'pages' })
);
```

## Precaching

Precaching loads resources into the cache during service worker installation, before any page requests them. This guarantees instant loading of critical assets:

```javascript
import { precacheAndRoute } from 'workbox-precaching';

// __WB_MANIFEST is injected by the Workbox build tool with
// a list of your assets and their content hashes
precacheAndRoute(self.__WB_MANIFEST);
```

Your build tool generates the manifest. With Vite:

```typescript
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default {
  plugins: [
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'service-worker.ts',
      injectManifest: {
        swDest: 'dist/sw.js',
      },
    }),
  ],
};
```

## Cache invalidation

Content-hashed URLs (`bundle.abc123.js`) never need invalidation -- a new file name means a new cache entry. The old one expires based on your `maxAgeSeconds` configuration.

For URLs without content hashes (like `/api/user/profile`), use `maxAgeSeconds` and `maxEntries` limits to bound cache growth and staleness.

## Debugging

In Chrome DevTools, the Application tab shows the service worker status, cache storage contents, and lets you simulate offline mode. Use "Update on reload" during development to skip the service worker update lifecycle.

The most common mistake: not handling the service worker update cycle. Old service workers stay active until all tabs are closed. `skipWaiting()` and `clientsClaim()` in Workbox force an immediate takeover, but only do this if your new service worker is compatible with the currently open pages.

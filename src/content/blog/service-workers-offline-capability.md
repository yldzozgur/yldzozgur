---
title: "Service workers: offline capability without a native app."
description: "How service workers intercept network requests to enable offline functionality, background sync, and push notifications."
pubDate: 2025-10-20
tags: ["JavaScript", "Performance"]
draft: false
---

A service worker is a script that runs in the background, separate from your web page, and acts as a programmable network proxy. It can intercept every network request the page makes and decide how to handle it: fetch from the network, serve from cache, or generate a response entirely.

## Registration

```javascript
// In your main JavaScript
if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register("/sw.js");
      console.log("SW registered:", registration.scope);
    } catch (error) {
      console.error("SW registration failed:", error);
    }
  });
}
```

The service worker file must be served from the same origin as your application. Its scope defaults to the directory it's in -- a worker at `/sw.js` controls the entire origin, while `/admin/sw.js` only controls `/admin/*`.

## Lifecycle

The service worker lifecycle is the part that confuses most developers:

1. **Install**: The browser downloads and parses the SW. Your `install` event fires. Cache static assets here.
2. **Activate**: The new SW takes control (after old tabs close). Clean up old caches here.
3. **Fetch**: The SW intercepts network requests from controlled pages.

A new service worker waits for the old one to finish if any tab still uses the old version. Call `skipWaiting()` to take over immediately:

```javascript
// sw.js
self.addEventListener("install", (event) => {
  self.skipWaiting(); // Take control immediately
  event.waitUntil(precacheAssets());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim(); // Take control of existing tabs
});
```

## Caching strategies

The `fetch` event is where you implement your caching strategy:

### Cache first (for static assets)

Serve from cache if available, fall back to network:

```javascript
const CACHE_NAME = "app-v1";
const STATIC_ASSETS = ["/", "/app.js", "/styles.css", "/logo.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
});

self.addEventListener("fetch", (event) => {
  if (isStaticAsset(event.request.url)) {
    event.respondWith(
      caches.match(event.request).then(cached => cached ?? fetch(event.request))
    );
  }
});
```

### Network first (for API calls)

Try the network, fall back to cache if offline:

```javascript
self.addEventListener("fetch", (event) => {
  if (event.request.url.includes("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful responses
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
  }
});
```

### Stale while revalidate (for content pages)

Serve cached version immediately, update cache in background:

```javascript
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(event.request);
      const networkPromise = fetch(event.request).then(response => {
        cache.put(event.request, response.clone());
        return response;
      });
      return cached ?? networkPromise;
    })
  );
});
```

This pattern gives instant response from cache (no network wait) while keeping the cache fresh. The user sees possibly stale content for the current visit but fresh content next time.

## Background sync

Background sync lets you defer actions until the user has a network connection:

```javascript
// In your page
async function submitForm(data) {
  if (!navigator.onLine) {
    await saveToIndexedDB(data); // Save locally
    await navigator.serviceWorker.ready.then(sw =>
      sw.sync.register("submit-form")
    );
    showMessage("Saved offline. Will sync when connected.");
    return;
  }
  await fetch("/api/submit", { method: "POST", body: JSON.stringify(data) });
}

// In sw.js
self.addEventListener("sync", (event) => {
  if (event.tag === "submit-form") {
    event.waitUntil(
      getFromIndexedDB().then(data =>
        fetch("/api/submit", { method: "POST", body: JSON.stringify(data) })
      )
    );
  }
});
```

## Push notifications

Service workers can receive push messages and display notifications even when the page is closed:

```javascript
// In sw.js
self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? { title: "New notification", body: "" };

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icon-192.png",
      badge: "/badge-72.png",
      data: { url: data.url }
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
```

## Workbox: skip the boilerplate

Google's Workbox library abstracts the caching strategy boilerplate:

```javascript
// sw.js with Workbox
import { precacheAndRoute } from "workbox-precaching";
import { NetworkFirst, CacheFirst, StaleWhileRevalidate } from "workbox-strategies";
import { registerRoute } from "workbox-routing";

precacheAndRoute(self.__WB_MANIFEST); // Injected by build tool

registerRoute(
  ({ url }) => url.pathname.startsWith("/api/"),
  new NetworkFirst({ cacheName: "api-cache" })
);

registerRoute(
  ({ request }) => request.destination === "image",
  new CacheFirst({ cacheName: "image-cache" })
);
```

Most frameworks (Next.js with `next-pwa`, Vite with `vite-plugin-pwa`) integrate Workbox into the build process and generate the service worker automatically with precaching lists.

---
title: "The HTTP cache: Cache-Control, ETags, headers that prevent stale data."
description: "How browser caching and CDN caching work through HTTP headers, and how to configure them correctly for different types of content."
pubDate: 2025-10-23
tags: ["HTTP", "Performance"]
draft: false
---

The fastest network request is the one that never happens. HTTP caching is the mechanism that makes this work, driven by headers that tell browsers and CDNs how long to hold onto responses.

## Cache-Control

`Cache-Control` is the primary caching directive. It can appear in both requests and responses; what matters for caching behavior is the response header.

Key directives:

**`max-age=N`**: Cache this response for N seconds. After N seconds, the cache must revalidate.

```
Cache-Control: max-age=86400
```

This tells any cache (browser, CDN, proxy) to serve this response for up to 24 hours without checking the server.

**`s-maxage=N`**: Like `max-age` but applies only to shared caches (CDNs, proxies). Overrides `max-age` for those caches.

```
Cache-Control: max-age=0, s-maxage=86400
```

This tells browsers not to cache but allows CDNs to cache for 24 hours.

**`no-cache`**: Despite the name, this does not prevent caching. It means "revalidate with the server before using a cached copy." If the server says the cache is still valid (304 Not Modified), the cached copy is used.

**`no-store`**: Actually prevents caching. The response is never stored. Use for truly sensitive data.

**`private`**: Only the browser may cache this, not CDNs.

**`public`**: Any cache may store this, including shared caches.

**`immutable`**: Tells the browser this resource will never change. Skip revalidation even when the user does a hard refresh. Use only with content-hashed URLs.

```
Cache-Control: public, max-age=31536000, immutable
```

## ETags: validation-based caching

An ETag is a unique identifier for a specific version of a resource:

```
HTTP/1.1 200 OK
ETag: "abc123def456"
Cache-Control: no-cache
Content-Type: application/json
```

The browser stores the response and its ETag. On the next request, it sends the ETag back:

```
GET /api/products HTTP/1.1
If-None-Match: "abc123def456"
```

If the data hasn't changed, the server responds with `304 Not Modified` and no body. The browser uses its cached copy. If the data changed, the server responds with `200 OK` and the new data.

ETags save bandwidth (no body transferred on 304) while guaranteeing freshness (the server always validates).

## Last-Modified: time-based validation

Similar to ETags but uses timestamps:

```
HTTP/1.1 200 OK
Last-Modified: Thu, 23 Oct 2025 08:00:00 GMT
Cache-Control: no-cache
```

Browser sends on next request:

```
GET /api/products HTTP/1.1
If-Modified-Since: Thu, 23 Oct 2025 08:00:00 GMT
```

ETags are preferable because they handle cases where a file is saved with the same content (modification time changes, content doesn't) or when timestamps are unreliable.

## Caching strategies by content type

**Static assets with content hashes** (JavaScript bundles, CSS, images):

```
Cache-Control: public, max-age=31536000, immutable
```

When the file changes, its hash in the URL changes, so the browser fetches a fresh copy. The URL is the cache key, and a new URL means no cached entry.

**HTML pages**:

```
Cache-Control: no-cache
ETag: "page-version-hash"
```

HTML should always be validated because it references other assets. `no-cache` with an ETag means the browser validates but skips the full download if nothing changed.

**API responses with user-specific data**:

```
Cache-Control: private, no-cache
ETag: "data-hash"
```

`private` prevents CDN caching. `no-cache` with ETag enables validation.

**API responses for public, cacheable data** (product listings, public content):

```
Cache-Control: public, s-maxage=300, stale-while-revalidate=60
```

CDNs cache for 5 minutes. During the 60-second stale-while-revalidate window, the CDN serves the stale response while fetching a fresh one in the background.

## Vary: per-header cache variations

`Vary` tells caches to store separate versions based on request headers:

```
Cache-Control: public, max-age=3600
Vary: Accept-Language
```

This caches separate versions for each language. `Vary: Accept-Encoding` is automatically handled by most CDNs to store separate gzip/brotli/uncompressed versions.

Be careful with `Vary: Cookie` or `Vary: Authorization` -- these effectively disable CDN caching since every user would have a different cache entry.

## Setting headers in Next.js

```javascript
// next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable"
          }
        ]
      },
      {
        source: "/api/:path*",
        headers: [
          { key: "Cache-Control", value: "no-cache" }
        ]
      }
    ];
  }
};
```

## Cache busting

When you need to invalidate a cached resource before its `max-age` expires:

- **Content hashing** (preferred): Include a hash of the file contents in the URL. Change the file, change the URL, old cache entry is never requested.
- **Query parameters**: `styles.css?v=2`. Works but requires updating every reference.
- **CDN purge API**: Most CDNs provide an API to purge specific URLs or cache tags. Slower and requires coordination.

The best caching strategy is content-addressed URLs for static assets with long `max-age`, combined with short or no-cache for the HTML entry point that references them.

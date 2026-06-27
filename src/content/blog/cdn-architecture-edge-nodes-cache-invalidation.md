---
title: "CDN architecture: what edge nodes do and how cache invalidation works."
description: "How CDN edge nodes cache and serve content, the difference between push and pull CDNs, and how cache invalidation propagates."
pubDate: 2025-10-27
tags: ["Performance", "DevOps"]
draft: false
---

A CDN (Content Delivery Network) is a distributed network of servers positioned geographically close to users. Instead of every request traveling to your origin server, most requests are served from an edge node nearby. The result is lower latency, reduced origin load, and better availability.

## How a CDN request works

Without a CDN, every request travels to your origin server:

```
User (Tokyo) → Internet → Origin (us-east-1) → 200ms round trip
```

With a CDN, the first request to each edge node fetches from origin. Subsequent requests are served locally:

```
User (Tokyo) → CDN edge (Tokyo) → Cache hit → 5ms response
```

The CDN edge node acts as a reverse proxy. It receives the request, checks its cache, and either returns the cached response or forwards the request to origin.

## Pull CDN vs push CDN

**Pull CDN** (most common): The CDN fetches content from your origin on demand. When a user requests a file the edge node doesn't have, the CDN pulls it from origin, caches it, and serves it. Future requests hit the cache. Cloudflare, Fastly, CloudFront, and Vercel's edge network all work this way.

**Push CDN**: You explicitly upload files to the CDN. The CDN does not talk to your origin. This gives you more control over what's cached but requires you to manage uploads. Useful for large media files where you want immediate global distribution.

Most web applications use pull CDNs. The CDN handles cache population automatically; you configure cache rules.

## Edge node hierarchy

Large CDNs have two-tier architectures:

**Edge nodes (PoPs - Points of Presence)**: Distributed globally, typically in 50-200+ cities. These serve the actual end users.

**Shield/backbone nodes**: A smaller set of intermediate servers that edge nodes check before going to origin. If 100 edge nodes each independently fetch the same resource from origin, you get 100 origin requests on a cache miss. A shield means all 100 edge nodes check one shield node, and the shield makes a single request to origin.

```
User → Edge (Singapore)  → 
User → Edge (Tokyo)      →  Shield (Asia) → Origin
User → Edge (Sydney)     →
```

Configuring a shield (called "Origin Shield" in CloudFront, "Tiered Cache" in Cloudflare) reduces origin traffic significantly for popular content.

## Cache keys

The CDN's cache key determines when two requests share a cached response. By default, the cache key is the full URL. But URLs with the same resource but different query parameters often produce the same response:

```
/products?sort=name&page=1  →  different cache entry
/products?page=1&sort=name  →  different cache entry (same parameters, different order)
```

Configure cache key normalization to handle this:
- Sort query parameters alphabetically
- Ignore irrelevant parameters (`utm_source`, `fbclid`, analytics parameters)

In Cloudflare, configure this in the Cache Rules settings. In CloudFront, use a Cache Policy with query string handling.

## Cache invalidation

When you deploy new content, you need the CDN to stop serving the old cached version. This is cache invalidation.

### Option 1: Let TTL expire

The simplest approach: set a short `max-age` and wait for it to expire. Works fine for content that updates on a predictable schedule. Not appropriate when you need immediate propagation.

### Option 2: URL-based invalidation (content hashing)

For static assets, include a hash of the file contents in the URL:

```html
<script src="/app.abc123.js"></script>
```

When the file changes, the hash changes, the URL changes, and the new URL has no cache entry. The old URL continues serving the old file until its TTL expires (irrelevant since no one requests it anymore).

This is the standard approach for build artifacts. Webpack, Vite, and most bundlers do this automatically.

### Option 3: CDN purge API

Most CDNs provide an API to explicitly purge cached content:

```bash
# Cloudflare purge by URL
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  --data '{"files": ["https://example.com/api/products"]}'

# Cloudflare purge everything
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {token}" \
  -d '{"purge_everything": true}'
```

Purge propagation takes seconds, not instant. During propagation, some edge nodes serve the old response.

### Option 4: Cache tags / surrogate keys

Tag cached responses with identifiers, then purge by tag:

```
Surrogate-Key: product-123 category-electronics
Cache-Control: public, max-age=3600
```

When product 123 is updated, purge all cached responses tagged `product-123`. This is more targeted than URL-based purging and works for pages that include data from multiple objects.

Fastly and Cloudflare Enterprise support cache tags. Vercel supports it through their `revalidateTag` API in Next.js:

```javascript
import { revalidateTag } from "next/cache";

export async function updateProduct(id, data) {
  await db.update(id, data);
  revalidateTag(`product-${id}`); // Purges all cached responses with this tag
}
```

## CDN for API responses

CDNs are typically thought of for static assets, but caching API responses at the edge has significant benefits for public data:

```javascript
// Next.js API route with CDN caching
export async function GET() {
  const products = await getPublicProducts();

  return Response.json(products, {
    headers: {
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60"
    }
  });
}
```

`s-maxage` targets shared caches (CDNs). The CDN caches for 5 minutes, then serves stale while revalidating in the background. The origin receives one request per 5 minutes from each edge node instead of one per user request.

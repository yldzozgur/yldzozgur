---
title: "Caching strategies: in-memory, HTTP headers, and when each is correct."
description: "A practical guide to the main caching layers available to web applications and the decision logic for choosing between them."
pubDate: 2025-07-07
tags: ["DevOps"]
draft: false
---

Caching is not one thing. It is a family of techniques that operate at different layers of the stack, with different invalidation models, different failure modes, and different costs. Picking the wrong layer for the job wastes effort. Picking the right one can cut infrastructure costs and latency simultaneously.

## Layer 1: in-process memory cache

The fastest cache is memory in the same process as your application code. No network hop, no serialization. Microsecond access.

```python
from functools import lru_cache

@lru_cache(maxsize=512)
def get_country_name(iso_code: str) -> str:
    return db.query("SELECT name FROM countries WHERE iso = %s", iso_code)
```

This works well for data that is small, changes rarely, and is expensive to compute or fetch. Country lists, configuration values, permission tables, compiled regex patterns.

The constraint is that each process has its own cache. If you run four application servers, you have four independent caches with potentially inconsistent data. When you deploy and restart processes, the cache empties. You cannot manually invalidate an entry across processes without a coordination mechanism.

Use in-process caching for read-only reference data or computed results that are cheap to reconstruct from a shared source if invalidated.

## Layer 2: shared cache (Redis, Memcached)

A shared cache sits outside the application process, accessible to all instances. Every server reads from and writes to the same store.

```python
import redis
import json

cache = redis.Redis(host='cache.internal', port=6379)

def get_user_profile(user_id: int):
    key = f"user:profile:{user_id}"
    cached = cache.get(key)
    if cached:
        return json.loads(cached)

    profile = db.fetch_user(user_id)
    cache.set(key, json.dumps(profile), ex=300)  # 5 minute TTL
    return profile
```

This pattern is called cache-aside or lazy population. The application checks the cache first, falls back to the database on a miss, and writes the result back to the cache with an expiry.

The TTL (time-to-live) is the primary invalidation mechanism. Short TTLs (30-300 seconds) are safe for data that changes but where brief staleness is acceptable. Explicit invalidation on write is needed when staleness is not acceptable:

```python
def update_user_profile(user_id: int, data: dict):
    db.update_user(user_id, data)
    cache.delete(f"user:profile:{user_id}")
```

Shared caches work well for session data, user-specific computed results, rate limit counters, and any data that multiple processes need to share but would be expensive to fetch per request.

## Layer 3: HTTP caching

HTTP caching is handled by browsers, CDNs, and reverse proxies. The application controls it via response headers. No code in the application has to do anything beyond setting the right headers.

```
Cache-Control: public, max-age=86400, stale-while-revalidate=3600
```

This tells any caching intermediary (CDN edge node, browser) to serve the cached response for 24 hours. After that, during the 1-hour `stale-while-revalidate` window, it can serve the stale response immediately while revalidating in the background.

For user-specific responses:

```
Cache-Control: private, max-age=0, must-revalidate
```

`private` tells shared caches (CDNs) not to store the response. Only the end user's browser may cache it.

For static assets with content-addressed filenames (like `main.abc123.js` from a bundler):

```
Cache-Control: public, max-age=31536000, immutable
```

One year. The file hash guarantees a new filename when content changes, so staleness is impossible.

ETags and conditional requests handle the revalidation flow:

```
Response:  ETag: "abc123"
Request:   If-None-Match: "abc123"
Response:  304 Not Modified  (no body, saves bandwidth)
```

## Choosing the right layer

The decision follows from the data characteristics:

**Is the data the same for all users?** HTTP caching at the CDN layer is the right answer. Static assets, public API responses, rendered HTML pages. The CDN absorbs the load and the origin never sees most requests.

**Is the data user-specific but shared across multiple application servers?** Redis or Memcached. Session state, user preferences, computed dashboards.

**Is the data read frequently within a single process and essentially static?** In-process memory cache. Country codes, feature flag tables, compiled configuration.

**Does staleness have a hard cost?** Use explicit cache invalidation on write, not TTL-based expiry. TTLs are appropriate when a few seconds of staleness is acceptable. Financial balances and inventory counts are not TTL-safe.

## Stampede protection

A cache miss under high load triggers many simultaneous database queries for the same key, a problem called a cache stampede. The fix is probabilistic early expiration or a lock:

```python
import threading

locks = {}

def get_with_lock(key, fetch_fn, ttl=300):
    cached = cache.get(key)
    if cached:
        return json.loads(cached)

    if key not in locks:
        locks[key] = threading.Lock()

    with locks[key]:
        # Double-check after acquiring lock
        cached = cache.get(key)
        if cached:
            return json.loads(cached)

        value = fetch_fn()
        cache.set(key, json.dumps(value), ex=ttl)
        return value
```

Caching done correctly is invisible to users. Caching done incorrectly shows stale data or collapses under load. The layer you choose determines the failure mode you get.

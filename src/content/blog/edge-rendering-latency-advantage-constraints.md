---
title: "Edge rendering: the latency advantage and the constraints."
description: "How edge rendering works, where it reduces latency, and what you give up compared to traditional server rendering."
pubDate: 2025-10-09
tags: ["Performance", "Vercel"]
draft: false
---

Edge rendering moves computation closer to the user by running code on servers distributed around the world instead of in a single data center. The latency advantage is real. So are the constraints.

## The latency problem edge rendering solves

A user in Tokyo hitting a server in us-east-1 experiences roughly 200ms of round-trip network latency before a single byte of your response arrives. For a server-rendered page that requires a database query, add 50-100ms for the query, and the user waits 300ms before seeing anything.

With edge rendering, the same request hits a server 20ms away in Tokyo. The total latency drops dramatically. The HTML starts arriving in under 100ms.

## How Vercel Edge Runtime works

Edge Functions run in V8 isolates -- the same JavaScript engine that powers Chrome -- instead of full Node.js processes. Isolates start in microseconds because there's no OS process initialization. This is what enables near-zero cold starts.

```javascript
// middleware.ts - runs at the edge on every request
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  // Runs in ~1ms, no cold start
  const country = request.geo?.country ?? "US";

  // Rewrite to country-specific version
  if (country === "DE") {
    return NextResponse.rewrite(new URL("/de" + request.nextUrl.pathname, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: "/((?!_next|api).*)"
};
```

This middleware runs before every page request, at an edge server near the user.

## What the Edge Runtime supports

The Edge Runtime is a subset of the Web API standard, not Node.js:

**Available:**
- `fetch`, `Request`, `Response`, `Headers`
- `URL`, `URLSearchParams`
- `TextEncoder`, `TextDecoder`
- Web Crypto API
- `setTimeout`, `setInterval`
- `ReadableStream`, `WritableStream`

**Not available:**
- Node.js built-ins: `fs`, `path`, `crypto` (use Web Crypto instead), `child_process`
- Most npm packages that depend on Node.js APIs
- Long-running connections

Mark a route as edge:

```javascript
// app/api/geo/route.ts
export const runtime = "edge";

export async function GET(request: Request) {
  // request.geo is populated by Vercel at the edge
  const { searchParams } = new URL(request.url);
  const city = request.headers.get("x-vercel-ip-city") ?? "Unknown";

  return Response.json({ city });
}
```

## Edge rendering vs edge middleware

There are two distinct uses of the edge:

**Edge middleware**: Runs before the request reaches your server. Used for auth checks, redirects, A/B testing, geolocation routing. Returns quickly (should be < 1ms). Cannot do heavy computation or access most databases.

**Edge rendering**: Renders full pages at the edge. The page handler fetches data and returns HTML, all from an edge server. Useful when the data source is also at the edge (KV store, distributed database).

The combination: middleware handles routing decisions instantly, edge rendering handles page generation from fast data sources.

## The database problem

The latency advantage of edge rendering disappears if your database is in a single region. A user in Tokyo hitting an edge server in Tokyo that then queries a database in us-east-1 is worse than just hitting the server in us-east-1 directly -- you've added a cross-region hop in the critical path.

Solutions:
- **Vercel KV (Upstash Redis)**: Global read replicas, low-latency from any region
- **PlanetScale**: Multi-region replication
- **Turso**: SQLite at the edge, deployed globally
- **Cloudflare D1**: SQLite database accessible from edge workers

For most applications, moving the database globally is complex. The pragmatic approach: use edge for requests that don't need a database (static content, auth middleware, geolocation) and use regional serverless functions for database-backed pages.

## When edge rendering helps most

**Personalization without a database call**: Customize content based on cookies, headers, or geolocation data that's available in the request itself.

**Authentication middleware**: Validate JWTs and redirect unauthenticated users without a database lookup.

**A/B testing**: Assign users to experiments and serve different content, all at the edge before the main server is involved.

**Static-ish content with regional variation**: Product pages that differ by currency or language but don't change per-user.

## When to stay on the server

If your page requires:
- A database query to a single-region database
- Access to Node.js APIs (file system, native modules)
- Heavy CPU computation
- npm packages with Node.js dependencies

Use a serverless function (Node.js runtime) or a dedicated server. The edge runtime is powerful for specific patterns, but forcing database-heavy pages through it adds complexity without latency benefit.

---
title: "Cold starts: what causes the delay and how to reduce it."
description: "What happens during a serverless cold start, why it adds latency, and practical techniques to minimize the impact."
pubDate: 2025-06-26
tags: ["Vercel", "Performance"]
draft: false
---

A cold start is the delay that happens when a serverless function runs for the first time after a period of inactivity. For functions that handle user-facing requests, this delay is a latency spike that users feel. Understanding what causes it leads directly to how to fix it.

## What happens during a cold start

When a serverless function receives a request and no warm instance exists, the cloud provider must:

1. Allocate a container (virtual machine or container runtime)
2. Download the function package and dependencies
3. Start the Node.js process
4. Execute module-level initialization code
5. Finally, call the handler function

Steps 1-4 are the cold start overhead. Steps 1-2 are controlled by the provider. Steps 3-4 are where your code matters.

Typical cold start durations:
- AWS Lambda with a small Node.js bundle: 100-400ms
- Vercel serverless functions: 200-600ms
- Vercel Edge Functions: 0-50ms (V8 isolates, not Node.js processes)

## What makes cold starts worse

**Large bundle size**: A 50 MB bundle takes longer to download and initialize than a 500 KB bundle. Every dependency you add increases bundle size.

**Heavy module-level initialization**: Code that runs when the module is imported (outside the handler function) runs on every cold start.

```javascript
// Bad: heavy initialization at module level
import puppeteer from "puppeteer"; // Large, slow to load
const browser = await puppeteer.launch(); // Runs on cold start

export default async function handler(req, res) {
  // ...
}
```

**Connecting to databases at module level**: Database connections established at module scope block the cold start until the connection is ready.

**Importing large libraries you use minimally**: `import _ from "lodash"` loads the entire 70 KB library when you might only need `_.groupBy`.

## Reducing cold start time

### Reduce bundle size

Audit your dependencies:

```bash
npx @next/bundle-analyzer
# or
npx bundlesize
```

Replace large libraries with smaller alternatives:
- `lodash` (70KB) → specific lodash functions or native JS
- `moment` (67KB) → `date-fns` (tree-shakeable) or `Temporal` API
- `axios` → native `fetch`

Use dynamic imports to defer loading:

```javascript
export default async function handler(req, res) {
  // Only loaded when this specific handler is called
  const { parse } = await import("csv-parse/sync");
  const records = parse(req.body);
  res.json(records);
}
```

### Lazy-initialize connections

Move initialization inside the handler but cache after first use:

```javascript
let dbClient = null;

async function getDb() {
  if (!dbClient) {
    const { Pool } = await import("pg");
    dbClient = new Pool({ connectionString: process.env.DATABASE_URL });
  }
  return dbClient;
}

export default async function handler(req, res) {
  const db = await getDb(); // Initialize on first warm request, reuse after
  const result = await db.query("SELECT * FROM users");
  res.json(result.rows);
}
```

On a cold start, `getDb()` initializes the connection. On subsequent requests to the same warm instance, it returns the cached client instantly.

### Use Edge Functions for latency-sensitive paths

Vercel Edge Functions run on V8 isolates instead of Node.js processes. Isolates start in milliseconds because there is no OS process to spin up. The tradeoff is a smaller runtime environment (no Node.js built-ins, limited npm packages).

```javascript
// app/api/fast-endpoint/route.ts
export const runtime = "edge"; // V8 isolate, near-zero cold start

export async function GET(request: Request) {
  return Response.json({ status: "ok" });
}
```

Edge is ideal for: authentication middleware, geolocation-based routing, A/B testing, rate limiting, and lightweight data fetching from an edge-compatible database.

### Keep functions warm with scheduled pings

If cold starts are unacceptable for specific critical paths, a scheduled ping prevents the function from going cold:

```yaml
# GitHub Actions: ping every 5 minutes
name: Keep warm

on:
  schedule:
    - cron: "*/5 * * * *"

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping function
        run: curl -s https://yourapp.com/api/health
```

This is a workaround, not a solution. For functions that must have consistently low latency, use Edge runtime or a long-running server.

## Measuring cold starts

Log the startup time from within your function:

```javascript
const MODULE_LOAD_TIME = Date.now();

export default async function handler(req, res) {
  const requestStart = Date.now();
  const coldStartMs = requestStart - MODULE_LOAD_TIME;

  // Include in structured logs
  console.log(JSON.stringify({
    type: "request",
    coldStartMs,
    isColdStart: coldStartMs > 100 // heuristic
  }));

  // ... handle request
}
```

Track this metric over time. A p99 cold start time above 1 second is a signal that bundle size or initialization code needs attention.

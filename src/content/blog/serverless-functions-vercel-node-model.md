---
title: "Serverless functions on Vercel: the Node model and what it can't do."
description: "How Vercel serverless functions work under the Node.js runtime, including execution model, limits, and what patterns don't fit."
pubDate: 2025-06-23
tags: ["Vercel", "Node.js"]
draft: false
---

Vercel serverless functions are good at handling HTTP requests quickly and scaling to zero when idle. They are not good at long-running processes, maintaining state, or background work. Understanding the execution model tells you when to use them and when not to.

## What a serverless function is

A file in the `api/` directory (or Next.js `app/api/` route) becomes an HTTP endpoint. When a request arrives, Vercel spins up a container, runs the function, returns the response, and the container either stays warm for subsequent requests or gets recycled.

```javascript
// api/hello.js
export default function handler(req, res) {
  res.status(200).json({ message: "Hello", method: req.method });
}
```

That is the entire function. No server setup, no port listening, no process management.

## The Node.js execution model

Vercel runs functions on Node.js (20.x by default as of 2025). The runtime is a standard Node.js environment with some constraints:

- **Execution timeout**: 10 seconds on Hobby, 60 seconds on Pro, 900 seconds on Enterprise
- **Memory**: 1024 MB by default, configurable up to 3009 MB
- **Payload size**: Request body max 4.5 MB
- **Response size**: No hard limit, but streaming is preferred for large responses

The function handler is exported as the default export for the Pages Router, or as named exports for App Router:

```javascript
// app/api/users/route.ts (App Router)
export async function GET(request: Request) {
  const users = await db.query("SELECT * FROM users LIMIT 10");
  return Response.json(users);
}

export async function POST(request: Request) {
  const body = await request.json();
  const user = await db.query(
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *",
    [body.name, body.email]
  );
  return Response.json(user.rows[0], { status: 201 });
}
```

## What you can configure

Set per-function configuration with exported constants:

```javascript
// api/heavy-task.js
export const config = {
  maxDuration: 60, // seconds, Pro plan required for > 10
  memory: 3009     // MB
};

export default async function handler(req, res) {
  // Long-running processing...
}
```

Or in `vercel.json` for all functions:

```json
{
  "functions": {
    "api/**/*.js": {
      "maxDuration": 30,
      "memory": 1024
    },
    "api/heavy.js": {
      "maxDuration": 60,
      "memory": 3009
    }
  }
}
```

## The file system is read-only (mostly)

Serverless functions have a read-only file system. The exception is `/tmp`, which provides up to 512 MB of ephemeral storage per function instance. Files written to `/tmp` are not shared between function instances and are deleted when the container is recycled.

```javascript
import { writeFileSync, readFileSync } from "fs";
import { tmpdir } from "os";
import path from "path";

export default async function handler(req, res) {
  const tempFile = path.join(tmpdir(), `${Date.now()}.txt`);
  writeFileSync(tempFile, "temporary data");
  // ... process file
  const content = readFileSync(tempFile, "utf8");
  res.json({ content });
}
```

Do not rely on `/tmp` for data that needs to persist between requests. Use a database or object storage.

## What serverless functions can't do

**Long-running background jobs**: If you need to process a large file after a user uploads it, a serverless function is the wrong tool. The timeout limit means tasks exceeding 15 minutes on most plans will be killed. Use a job queue with a worker process instead.

**WebSocket servers**: Serverless functions handle one request and close. They cannot maintain persistent connections. Use a dedicated WebSocket service like Ably, Pusher, or a long-running server.

**Persistent in-memory state**: Each function invocation may hit a different container. Global variables in Node.js module scope may be shared between requests on a warm container, but you cannot rely on this. State that must persist belongs in a database or cache.

**Spawning child processes that outlive the request**: `child_process.spawn` works, but the child is killed when the function returns.

## Warming and cold starts

When no instance of a function has run recently, Vercel spins up a new container. This cold start adds 200-500ms of latency. Subsequent requests to the same function hit a warm instance and have no cold start overhead.

Strategies to reduce cold start impact:
- Keep functions small. Smaller bundles initialize faster.
- Lazy-load heavy dependencies inside the handler, not at the module level.
- Use Edge Functions for latency-sensitive paths (they have near-zero cold starts).

```javascript
// Lazy load a heavy library
export default async function handler(req, res) {
  const { PDFDocument } = await import("pdf-lib"); // loaded only when called
  // ...
}
```

## Bundling and dependencies

Vercel bundles each function and its dependencies at deploy time. The bundle is limited to 250 MB (compressed). Large dependencies like `puppeteer` or `ffmpeg` require special handling -- use Vercel's `@vercel/og` for Puppeteer use cases, or move heavy processing to a separate service.

Check your bundle size with:

```bash
vercel build
# Inspect .vercel/output/functions/api/
```

Serverless functions are excellent for CRUD APIs, webhook handlers, form submissions, and data fetching. The moment you need persistent connections, background processing, or more than a minute of execution time, reach for a different compute primitive.

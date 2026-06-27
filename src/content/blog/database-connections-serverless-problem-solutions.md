---
title: "Database connections in serverless: the problem and the solutions."
description: "Why traditional database connection pooling breaks in serverless environments, and the patterns that actually work."
pubDate: 2025-10-13
tags: ["PostgreSQL", "Vercel"]
draft: false
---

PostgreSQL connections are expensive. Each one is a forked OS process on the database server, consuming memory and file descriptors. Traditional applications manage a small pool of connections and reuse them. Serverless functions break this model in a specific and painful way.

## Why serverless kills traditional pooling

A traditional application starts with a connection pool: open 10 connections on startup, reuse them across thousands of requests. This works because the application process is long-lived.

A serverless function starts fresh on each cold start and may run in hundreds of simultaneous instances. Each instance creates its own database connections. Scale to 200 concurrent function instances, each with a pool of 5 connections, and you're holding 1,000 PostgreSQL connections open -- well above the `max_connections` default of 100.

```
PostgreSQL error: remaining connection slots are reserved for non-replication superuser connections
```

This error means you've hit the connection limit. New connections are being refused.

## Connection count math

PostgreSQL's `max_connections` defaults to 100 (many managed services set it to 100-500). Subtract connections reserved for superuser access and monitoring:

Available connections: ~90

A Next.js application on Vercel might have:
- Up to 100 concurrent function instances under load
- Each instance holding 1-5 connections to warm up fast

That's 100-500 connections. You've blown the limit before you hit meaningful traffic.

## Solution 1: PgBouncer (external connection pooler)

PgBouncer sits between your application and PostgreSQL. Functions connect to PgBouncer, which maintains a small pool of actual PostgreSQL connections and multiplexes application connections onto them.

In transaction pooling mode, a connection is only held for the duration of a single transaction, then returned to the pool. Hundreds of function instances can share tens of PostgreSQL connections.

```
Functions (hundreds) → PgBouncer (10-50 connections) → PostgreSQL (10-50 connections)
```

Managed services that provide this:
- **Supabase**: Built-in PgBouncer on port 6543
- **Neon**: Built-in connection pooler
- **Railway**: Can configure PgBouncer

Connection string pattern:

```javascript
// Direct connection (not for serverless)
const directUrl = "postgresql://user:pass@host:5432/db";

// Pooler connection (for serverless)
const poolerUrl = "postgresql://user:pass@host:6543/db?pgbouncer=true";
```

## Solution 2: Neon serverless driver

Neon's serverless PostgreSQL can accept connections over HTTP instead of TCP. Each query is a separate HTTP request -- no persistent connection needed.

```javascript
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL);

export default async function handler(req, res) {
  // HTTP query, no persistent connection
  const users = await sql`SELECT * FROM users LIMIT 10`;
  res.json(users);
}
```

For Next.js App Router:

```javascript
// app/api/users/route.ts
import { neon } from "@neondatabase/serverless";

const sql = neon(process.env.DATABASE_URL!);

export async function GET() {
  const users = await sql`SELECT id, name, email FROM users`;
  return Response.json(users);
}
```

The HTTP driver has higher per-query latency than a persistent TCP connection (~5-20ms overhead) but eliminates the connection count problem entirely. For most serverless workloads, this tradeoff is favorable.

## Solution 3: Prisma with connection pooling

Prisma Accelerate is a connection pooler purpose-built for serverless with Prisma:

```javascript
// With Prisma Accelerate
import { PrismaClient } from "@prisma/client";
import { withAccelerate } from "@prisma/extension-accelerate";

const prisma = new PrismaClient().$extends(withAccelerate());

export default async function handler(req, res) {
  const users = await prisma.user.findMany({
    cacheStrategy: { ttl: 60 } // Accelerate can cache queries
  });
  res.json(users);
}
```

## Solution 4: Lazy connection with global caching

For cases where you must use a direct connection, cache the client across warm function invocations:

```javascript
import { Pool } from "pg";

// Module-level: persists across requests on warm instances
let pool: Pool | null = null;

function getPool() {
  if (!pool) {
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 1, // Only 1 connection per function instance
      idleTimeoutMillis: 10000,
      connectionTimeoutMillis: 5000
    });
  }
  return pool;
}

export default async function handler(req, res) {
  const db = getPool();
  const result = await db.query("SELECT * FROM users LIMIT 10");
  res.json(result.rows);
}
```

Setting `max: 1` limits each function instance to one connection. With this approach, connection count scales with function instances rather than with connections per instance. Still not ideal at high concurrency, but better than the default.

## Choosing the right solution

| Scenario | Solution |
|----------|----------|
| Neon database | Neon serverless driver (HTTP) |
| Supabase | Use port 6543 (built-in PgBouncer) |
| Prisma ORM | Prisma Accelerate |
| Any Postgres, need max compatibility | Self-hosted PgBouncer |
| Low traffic, simple setup | `max: 1` pool with lazy init |

The Neon HTTP driver and Supabase's built-in pooler are the lowest-friction options for new projects. For existing applications migrating to serverless, PgBouncer is the most universal solution.

---
title: "Database replication: read replicas and why they help."
description: "How PostgreSQL replication works, when read replicas make sense, and how to route reads and writes in your application."
pubDate: 2025-12-04
tags: ["PostgreSQL", "Databases"]
draft: false
---

A single database server handles both reads and writes. As traffic grows, the CPU and I/O of that single server become the bottleneck. Database replication distributes the load by creating copies of the primary that can serve read queries.

## How PostgreSQL replication works

PostgreSQL uses Write-Ahead Logging (WAL) for replication. Every change to the database is written to the WAL before being applied to the actual data files. Replicas receive this WAL stream and apply it, maintaining an identical copy of the data.

Two replication modes:

**Synchronous replication**: The primary waits for at least one replica to confirm it received and applied the WAL entry before acknowledging the write to the client. Guarantees no data loss if the primary fails, but adds latency to every write.

**Asynchronous replication** (the default): The primary acknowledges the write immediately after writing to its own WAL. The replica receives and applies the WAL stream with a small delay (usually milliseconds). Faster for writes, but the replica might be slightly behind -- there's a brief window where data is on the primary but not yet on the replica.

## When read replicas help

Read replicas help when:
- **Read-heavy workloads**: Most queries are reads (product listings, dashboards, search)
- **Analytical queries**: Long-running reports that would block writes on the primary
- **Geographic distribution**: A replica in another region serves local users with lower latency

Read replicas don't help with:
- Write-heavy workloads (all writes still go to primary)
- Transactions that mix reads and writes (must use the primary for consistency)

A common ratio: applications where 80%+ of queries are reads can offload most of their load to replicas.

## Setting up routing in your application

The simplest approach: two connection strings, one for reads, one for writes.

```javascript
import { Pool } from "pg";

const primaryPool = new Pool({ connectionString: process.env.PRIMARY_DATABASE_URL });
const replicaPool = new Pool({ connectionString: process.env.REPLICA_DATABASE_URL });

// Use for all writes
async function write(query, params) {
  return primaryPool.query(query, params);
}

// Use for reads that can tolerate slight staleness
async function read(query, params) {
  return replicaPool.query(query, params);
}

// Use the primary for reads that need the latest data
async function readConsistent(query, params) {
  return primaryPool.query(query, params);
}
```

Usage:

```javascript
// Insert goes to primary
await write(
  "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
  [userId, total]
);

// Product listings can go to replica
const products = await read("SELECT * FROM products WHERE active = true");

// After a write, read from primary for consistency
const order = await readConsistent("SELECT * FROM orders WHERE id = $1", [orderId]);
```

## Read-after-write consistency

The biggest pitfall: after writing data, immediately reading from a replica might not return the just-written data if the replica hasn't caught up.

```javascript
// Bug: user might not see their own update
await write("UPDATE users SET name = $1 WHERE id = $2", [newName, userId]);
const user = await read("SELECT * FROM users WHERE id = $1", [userId]); // might be stale!
```

Solutions:

1. **Always read your own writes from primary**: After any write, route subsequent reads for that object to the primary for a short window.

2. **Pass the write LSN**: PostgreSQL lets you wait for a replica to catch up to a specific WAL position:

```sql
-- After a write, get the current WAL position
SELECT pg_current_wal_lsn();

-- On replica, wait for it to catch up
SELECT pg_wal_replay_wait($1, 5000); -- wait up to 5 seconds
```

3. **Use replication lag metrics**: Monitor replica lag with `pg_stat_replication` on the primary:

```sql
SELECT
  client_addr,
  state,
  sent_lsn - replay_lsn AS replay_lag_bytes,
  replay_lag
FROM pg_stat_replication;
```

If replica lag is consistently low (< 100ms), read-after-write issues are rare in practice.

## Prisma with read replicas

Prisma supports read replica routing via a middleware:

```javascript
import { PrismaClient } from "@prisma/client";
import { readReplicas } from "@prisma/extension-read-replicas";

const prisma = new PrismaClient().$extends(
  readReplicas({
    url: process.env.REPLICA_DATABASE_URL
  })
);

// Automatically routes to replica
const users = await prisma.user.findMany();

// Force primary with $primary()
const user = await prisma.$primary().user.findUnique({ where: { id: 1 } });
```

## Managed replication

Most managed database services handle replication setup automatically:

- **Supabase**: Read replicas available via dashboard
- **Neon**: Branching provides read-only replicas
- **PlanetScale**: Automatic read-only regions
- **AWS RDS**: Read replicas with one-click setup, automatic failover

For a new application, start with a single primary. Add a read replica when you can measure that read queries are a bottleneck. Premature optimization of database architecture adds complexity without benefit.

The connection string approach described above makes it straightforward to add a replica later without rewriting your data access layer.

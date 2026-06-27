---
title: "Connection pooling math: how to calculate the right pool size."
description: "More connections isn't always better. Database connections are expensive resources, and the optimal pool size has a formula — here's how to work it out."
pubDate: 2026-06-22
tags: ["PostgreSQL", "Performance"]
draft: false
---

Opening a database connection is expensive: it involves a TCP handshake, authentication, process spawning (PostgreSQL forks a backend process per connection), and memory allocation on the database server. Connection pooling keeps a set of connections open and reuses them across application requests. But how large should that pool be?

The intuitive answer — "as large as possible" — is wrong. Too many connections cause contention at the database, excess memory consumption, and worse performance than a correctly sized pool.

## PostgreSQL's connection cost

Each PostgreSQL connection consumes roughly 5-10MB of memory on the server (the backend process overhead). A server with 100 connections is consuming at least 500MB just for connection overhead, before any query execution.

```sql
-- Current connection count and limits
SELECT count(*) AS current_connections FROM pg_stat_activity;
SHOW max_connections;

-- Connections by state
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;
-- idle: connections doing nothing (wasted resources)
-- active: running a query
-- idle in transaction: holding a transaction open with no active query
```

## The formula

The starting formula for pool size comes from a classic article on connection pooling:

```
pool_size = (number of CPU cores) * 2 + effective_spindle_count
```

For a typical 8-core database server with SSDs (spindle count = 1):

```
pool_size = 8 * 2 + 1 = 17
```

This seems surprisingly small. The reasoning: a CPU can only execute a fixed number of things in parallel. More connections than available CPU capacity means connections are queuing — waiting for CPU time. At that point, more connections add overhead (context switching, lock contention) without adding throughput.

## Little's Law applied to pools

A more rigorous approach uses Little's Law from queuing theory:

```
L = λ × W
```

Where:
- L = number of concurrent connections needed (pool size)
- λ = request rate (requests per second)
- W = average time a request holds a connection (seconds)

Example: an API handling 500 requests/second where each request holds a database connection for an average of 20ms:

```
L = 500 req/s × 0.020 s = 10 connections
```

Ten connections handle 500 requests per second at 20ms average connection hold time. Adding more connections doesn't increase throughput — it just creates idle connections.

```typescript
// Measure actual connection hold time in your application
const start = Date.now();
const client = await pool.connect();
try {
  await client.query('SELECT ...'); // your actual query
} finally {
  client.release();
  const holdTimeMs = Date.now() - start;
  metrics.histogram('db.connection_hold_ms', holdTimeMs);
}
```

## Multi-instance applications

In a containerized environment with multiple application instances, the total connection count is:

```
total_connections = pool_size_per_instance × number_of_instances
```

With 50 containers each holding a pool of 10 connections, you have 500 connections to the database. This is where misconfigured pools cause problems at scale — each additional deployment doubles the connection count.

```typescript
// node-postgres (pg) pool configuration
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  max: 10,           // pool size per instance
  min: 2,            // keep 2 connections warm
  idleTimeoutMillis: 30_000,  // release idle connections after 30s
  connectionTimeoutMillis: 5_000, // fail fast if pool is exhausted
});

// Log pool state for monitoring
setInterval(() => {
  console.log({
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount,
  });
}, 10_000);
```

## PgBouncer for scale

When you have many application instances or serverless functions where connection counts are unbounded, PgBouncer sits between the application and PostgreSQL, maintaining a small connection pool to PostgreSQL while handling many more connections from the application side.

```ini
# pgbouncer.ini
[databases]
myapp = host=postgres port=5432 dbname=myapp

[pgbouncer]
pool_mode = transaction   # release connection after each transaction
max_client_conn = 1000    # connections from applications
default_pool_size = 20    # actual PostgreSQL connections
```

In transaction mode, PgBouncer assigns a PostgreSQL connection only for the duration of a transaction, then returns it to the pool. A function that handles 1000 concurrent connections to PgBouncer only needs 20 connections to PostgreSQL.

The constraint: in transaction mode, session-level features (temporary tables, advisory locks, prepared statements bound to a session) don't work reliably. For most applications this is acceptable.

## Practical starting points

For a typical web application:
- Start with `pool_size = cores * 2` on the database server
- Divide by the number of application instances
- Set a connection timeout to fail fast when the pool is exhausted
- Monitor `waitingCount` — sustained non-zero values mean the pool is too small
- Monitor idle connections — many idle connections mean the pool is too large

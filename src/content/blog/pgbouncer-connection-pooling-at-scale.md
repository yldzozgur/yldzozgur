---
title: "Connection pooling at scale: why PgBouncer exists."
description: "How PgBouncer pools database connections to handle high concurrency, the three pooling modes, and how to configure it."
pubDate: 2025-12-08
tags: ["PostgreSQL", "Performance"]
draft: false
---

PostgreSQL forks a new OS process for every client connection. At 100 connections, you have 100 processes. At 1,000 connections, PostgreSQL is spending more memory on connection overhead than on serving queries. PgBouncer solves this by sitting between your application and PostgreSQL, multiplexing thousands of application connections onto a small pool of real PostgreSQL connections.

## The PostgreSQL connection model

Each PostgreSQL connection is a separate backend process. On a server with 4 GB of RAM, you can typically support 100-300 connections before memory becomes the bottleneck. Beyond that, you're in trouble.

The default `max_connections` is 100. Change it in `postgresql.conf`:

```sql
SHOW max_connections; -- Check current value
```

Increasing `max_connections` past ~500 degrades performance even if memory allows it, because PostgreSQL's lock manager and other subsystems have O(n) complexity with connection count.

## What PgBouncer does

PgBouncer maintains a small pool of real PostgreSQL connections. Application clients connect to PgBouncer (which accepts thousands of connections cheaply), and PgBouncer assigns them to pooled PostgreSQL connections.

```
1000 app clients → PgBouncer → 20 PostgreSQL connections
```

The 1000 clients each believe they have a real database connection. PgBouncer handles the routing.

## Three pooling modes

PgBouncer has three modes with different semantics:

**Session pooling**: A PostgreSQL connection is assigned to the client for the lifetime of the client's session. Connection reuse only happens when the client disconnects. This is barely more efficient than direct connections for long-lived application connections, but useful for connection count limits with short-lived serverless functions.

**Transaction pooling**: A PostgreSQL connection is assigned when a transaction starts and returned to the pool when the transaction completes. Between transactions, the application holds no PostgreSQL connection. This is the high-efficiency mode that enables 1,000+ app clients on 20 PostgreSQL connections.

**Statement pooling**: A PostgreSQL connection is assigned for a single statement and returned immediately. Most efficient for connection count, but breaks transactions (can't execute multiple statements atomically).

Transaction pooling is what you want for most applications. It has one major constraint: you cannot use session-level features between transactions. Specifically:

- `LISTEN` / `NOTIFY`
- Advisory locks (`pg_advisory_lock`)
- Prepared statements (must disable with `server_reset_query`)
- `SET` session parameters

If you use any of these, use session pooling instead.

## Configuring PgBouncer

`pgbouncer.ini`:

```ini
[databases]
myapp = host=localhost port=5432 dbname=myapp

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 600
log_connections = 0
log_disconnections = 0
```

Key parameters:

- `max_client_conn`: Maximum clients PgBouncer accepts (cheap, just a file descriptor)
- `default_pool_size`: Real PostgreSQL connections per database/user pair (this is the expensive limit)
- `reserve_pool_size`: Extra connections for traffic spikes
- `server_idle_timeout`: Return idle PostgreSQL connections to the pool after N seconds

`userlist.txt` (MD5 passwords):

```
"myuser" "md5password_hash_here"
```

Generate the hash: `echo -n "password_here_myuser" | md5sum` and prepend `md5`.

## Application connection strings

Your application connects to PgBouncer instead of PostgreSQL directly:

```javascript
// Before: direct PostgreSQL
const pool = new Pool({ connectionString: "postgres://user:pass@db-host:5432/myapp" });

// After: via PgBouncer
const pool = new Pool({ connectionString: "postgres://user:pass@pgbouncer-host:6432/myapp" });
```

With transaction pooling, set `max` to a higher number in your Node.js pool -- the bottleneck is now PgBouncer's `default_pool_size`, not a per-application limit:

```javascript
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 100, // PgBouncer handles the real limit
  idleTimeoutMillis: 10000
});
```

## Monitoring

PgBouncer exposes stats via a virtual database called `pgbouncer`:

```bash
psql -h pgbouncer-host -p 6432 -U pgbouncer pgbouncer

SHOW STATS;
SHOW POOLS;
SHOW CLIENTS;
SHOW SERVERS;
```

Key metrics to watch:

- `cl_waiting` in `SHOW POOLS`: Clients waiting for a server connection. If this is nonzero regularly, increase `default_pool_size`.
- `sv_active` vs `sv_idle` in `SHOW SERVERS`: Active vs idle PostgreSQL connections. Low `sv_idle` under load means you might need more pool size.

## Managed alternatives

If operating your own PgBouncer feels like too much, managed alternatives:

- **Supabase**: Provides PgBouncer on port 6543 out of the box with your project
- **Neon**: Has a built-in serverless driver (HTTP-based, no persistent connections)
- **pgbouncer-as-a-service**: Some hosting platforms offer this

For any application with more than 50 concurrent database users, connection pooling is not optional. PgBouncer is the most battle-tested solution.

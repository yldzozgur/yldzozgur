---
title: "Partial indexes: smaller, faster indexes for filtered queries."
description: "A partial index only indexes rows that match a condition. For queries that always filter on a specific value, a partial index is smaller, faster, and cheaper to maintain."
pubDate: 2026-06-18
tags: ["PostgreSQL", "Performance"]
draft: false
---

A standard index covers every row in a table. A partial index covers only the rows that satisfy a WHERE clause. When your queries consistently filter by a particular condition, a partial index can be dramatically smaller than a full index — and smaller indexes fit in memory, have faster lookups, and impose less overhead on writes.

## A concrete example

Consider an orders table where most orders are in a terminal state:

```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL,
  status TEXT NOT NULL, -- 'pending', 'processing', 'shipped', 'delivered', 'cancelled'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Typical distribution:
-- pending:     2%
-- processing:  3%
-- shipped:     5%
-- delivered:  80%
-- cancelled:  10%
```

An index to serve queries for active orders:

```sql
-- Full index: covers all 100% of rows
CREATE INDEX orders_status_full ON orders (status, created_at);

-- Partial index: covers only active orders (10% of rows)
CREATE INDEX orders_active_status ON orders (created_at)
WHERE status IN ('pending', 'processing', 'shipped');
```

If the table has 10 million rows, the partial index covers only about 1 million. It's 10x smaller, which means it's much more likely to fit entirely in `shared_buffers` and can be scanned much faster.

## Queries that use partial indexes

PostgreSQL uses a partial index when the query's WHERE clause implies the index predicate:

```sql
-- Uses the partial index (status = 'pending' implies status IN ('pending', 'processing', 'shipped'))
SELECT * FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 50;

-- Also uses the partial index
SELECT * FROM orders
WHERE status IN ('pending', 'processing')
AND created_at > NOW() - INTERVAL '7 days';

-- Does NOT use the partial index (delivered orders aren't in the index)
SELECT * FROM orders WHERE status = 'delivered';
```

Run `EXPLAIN` to confirm:

```sql
EXPLAIN SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC LIMIT 50;

-- Index Scan using orders_active_status on orders
--   Index Cond: (status = 'pending'::text)
```

## Unique partial indexes

Partial indexes are particularly powerful for conditional uniqueness constraints. A common pattern: an email address should be unique among non-deleted users, but multiple deleted records can share the same email.

```sql
-- Soft-delete pattern
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ;

-- Unique only among active (non-deleted) users
CREATE UNIQUE INDEX users_email_active_unique
ON users (email)
WHERE deleted_at IS NULL;

-- This insert succeeds (new user)
INSERT INTO users (email, name) VALUES ('alice@example.com', 'Alice');

-- This fails (duplicate active email)
INSERT INTO users (email, name) VALUES ('alice@example.com', 'Alice2');

-- This succeeds (alice was soft-deleted, a new alice can be created)
UPDATE users SET deleted_at = NOW() WHERE email = 'alice@example.com';
INSERT INTO users (email, name) VALUES ('alice@example.com', 'New Alice');
```

You can't implement this constraint with a standard unique index — it would reject the re-registration of a deleted email.

## Partial indexes for queue patterns

A work queue table where most rows are in a completed state benefits from a partial index:

```sql
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL,
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

-- Only index pending jobs — completed jobs aren't queried for work
CREATE INDEX jobs_pending_idx ON jobs (created_at ASC)
WHERE status = 'pending';

-- Worker query: uses the tiny partial index, ignores the millions of completed jobs
SELECT * FROM jobs
WHERE status = 'pending'
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

A full index on this table would grow continuously as completed jobs accumulate. The partial index stays the same size regardless of how many jobs complete.

## Write overhead comparison

Every index must be updated on INSERT, UPDATE, and DELETE. Partial indexes reduce this overhead because only rows matching the predicate need to update the index.

When a job completes and its status changes from `pending` to `completed`, the partial index (`WHERE status = 'pending'`) removes the entry rather than updating it. Completed jobs don't touch the index again. The full index would require an update regardless of status.

For tables where data transitions out of the indexed state (orders completing, jobs finishing, notifications being read), partial indexes naturally stay small without any maintenance intervention.

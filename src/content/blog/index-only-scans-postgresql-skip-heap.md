---
title: "Index-only scans: the PostgreSQL optimization that skips the heap."
description: "When all the columns a query needs are in an index, PostgreSQL can answer the query from the index alone — without touching the table at all."
pubDate: 2026-06-15
tags: ["PostgreSQL", "Performance"]
draft: false
---

A regular index scan in PostgreSQL involves two steps: finding the matching index entries, then fetching the actual rows from the table (the "heap") to get the full row data. An index-only scan skips the second step entirely — if the index contains all the columns the query needs, PostgreSQL reads just the index and returns the results without a single heap access.

## When index-only scans apply

An index-only scan is possible when:

1. Every column referenced in the query (in SELECT, WHERE, ORDER BY) is included in the index.
2. The visibility map indicates that the relevant heap pages are all-visible (all rows are visible to all current transactions).

The visibility map is maintained by VACUUM. Pages that have been vacuumed and contain no dead tuples are marked as all-visible. Index-only scans can proceed without heap access on all-visible pages.

```sql
-- Table
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL,
  status TEXT NOT NULL,
  total NUMERIC NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Regular index on status
CREATE INDEX orders_status_idx ON orders (status);

-- This query uses a regular index scan (needs total from heap)
SELECT status, total FROM orders WHERE status = 'pending';

-- Add total to the index as an INCLUDE column
CREATE INDEX orders_status_covering_idx ON orders (status) INCLUDE (total);

-- Now this query can use an index-only scan
SELECT status, total FROM orders WHERE status = 'pending';
```

The `INCLUDE` clause adds columns to the index without including them in the sort key — they're stored in the leaf pages of the B-tree and can be returned directly.

## Confirming with EXPLAIN

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT status, total FROM orders WHERE status = 'pending';
```

Look for `Index Only Scan` in the output:

```
Index Only Scan using orders_status_covering_idx on orders
  (cost=0.43..85.22 rows=1240 width=24)
  (actual time=0.042..1.823 rows=1240 loops=1)
  Index Cond: (status = 'pending')
  Heap Fetches: 0   <-- zero heap accesses
  Buffers: shared hit=28
```

`Heap Fetches: 0` confirms no heap access occurred. If the visibility map isn't current, you'll see a non-zero count — PostgreSQL had to visit the heap to verify visibility for those rows.

## Building covering indexes deliberately

The goal is to identify queries that run frequently, then design indexes that contain all the columns those queries need.

```sql
-- Frequent query: get user email and name for authentication
SELECT email, name FROM users WHERE email = $1;

-- Standard index on email requires heap access for name
CREATE INDEX users_email_idx ON users (email);

-- Covering index: email is the search key, name is included
CREATE INDEX users_email_covering_idx ON users (email) INCLUDE (name);

-- Another common pattern: list queries with filtering
-- Query: recent orders for a customer, showing id, status, total, created_at
SELECT id, status, total, created_at
FROM orders
WHERE customer_id = $1
ORDER BY created_at DESC
LIMIT 20;

-- Covering index for this query
CREATE INDEX orders_customer_covering_idx
ON orders (customer_id, created_at DESC)
INCLUDE (id, status, total);
```

## The visibility map and VACUUM interaction

Index-only scans degrade gracefully when pages aren't all-visible. PostgreSQL falls back to checking the heap for visibility only on pages that aren't marked. After a VACUUM run, more pages become all-visible, and subsequent index-only scans benefit.

```sql
-- Check how many pages are all-visible per table
SELECT
  relname,
  pg_relation_size(oid) AS table_size,
  (SELECT count(*) FROM generate_series(0, relpages - 1) AS blk
   WHERE pg_visibility_get_two_bits(oid, blk) >> 1 & 1 = 1
  ) AS all_visible_pages,
  relpages AS total_pages
FROM pg_class
WHERE relname = 'orders';
```

A table with many dead tuples (high update/delete rate and infrequent vacuum) will have few all-visible pages. Index-only scans on such tables degrade to near-regular index scans. Monitoring autovacuum frequency and dead tuple counts ensures the visibility map stays current.

## When INCLUDE makes sense vs. adding to the key

Adding a column to the sort key of an index allows filtering and sorting on it but increases the index size and affects sort order. Using `INCLUDE` adds the column only for retrieval, making the index smaller for that column and not affecting sort behavior.

Use `INCLUDE` for columns you need in the output but not for filtering or ordering. Use the sort key position for columns you need in WHERE or ORDER BY clauses.

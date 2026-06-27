---
title: "PostgreSQL indexes: B-tree, partial, composite and which queries need each."
description: "Not every index type is right for every query. PostgreSQL offers B-tree, partial, and composite indexes with different cost profiles. Here's how to match index type to query pattern."
pubDate: 2024-09-09
tags: ["Security"]
draft: false
---

PostgreSQL's default index type is a B-tree, and it handles most queries well. But using a B-tree for everything misses opportunities: a partial index on a filtered subset can be 10x smaller and faster; a composite index can satisfy multi-column queries that a single-column index can't. Understanding the types prevents both missing indexes (causing full scans) and redundant indexes (slowing down writes).

## B-tree indexes: the default

A B-tree (balanced tree) keeps data in sorted order. It supports equality, range, and sort queries.

```sql
-- Create a B-tree index (default type)
CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_posts_created_at ON posts (created_at DESC);
```

Queries this helps:

```sql
-- Equality: O(log n) instead of O(n)
SELECT * FROM users WHERE email = 'alice@example.com';

-- Range: uses the sorted structure
SELECT * FROM posts WHERE created_at > '2024-01-01';

-- Sort: index is already sorted, no extra sort step
SELECT * FROM posts ORDER BY created_at DESC LIMIT 10;
```

B-tree indexes are useless for:
- Queries using `LIKE '%suffix'` (leading wildcard) — can't use sorted structure
- Full-text search — use GIN/tsvector for that
- Geometric queries — use GiST

## Composite indexes

A composite index covers multiple columns. Like MongoDB compound indexes, it follows the **prefix rule**: the index on `(a, b, c)` can satisfy queries on `a`, `(a, b)`, and `(a, b, c)`, but not `b`, `c`, or `(b, c)` alone.

```sql
-- This index satisfies queries that filter by status, and optionally by created_at
CREATE INDEX idx_posts_status_created ON posts (status, created_at DESC);
```

Query patterns and whether the index helps:

```sql
-- Yes: uses both columns
SELECT * FROM posts WHERE status = 'published' ORDER BY created_at DESC;

-- Yes: uses prefix (status)
SELECT * FROM posts WHERE status = 'published';

-- No: skips the first column
SELECT * FROM posts WHERE created_at > '2024-01-01';
-- This needs a separate index on just (created_at)
```

Column order in a composite index matters. Put the most selective column first (the one with the most distinct values), unless your query always filters on a specific column — then put that column first regardless of selectivity.

## Partial indexes

A partial index covers only rows matching a condition. This is useful when you frequently query a subset of the table.

```sql
-- Only index active users — if 95% of users are inactive, this index is 20x smaller
CREATE INDEX idx_active_users_email ON users (email) WHERE deleted_at IS NULL;

-- Only index published posts
CREATE INDEX idx_published_posts_slug ON posts (slug) WHERE status = 'published';

-- Unique constraint only on active records (allows multiple deleted records with same email)
CREATE UNIQUE INDEX idx_users_email_unique ON users (email) WHERE deleted_at IS NULL;
```

The partial index is only used when the query's WHERE clause includes the index condition. A query that doesn't filter on `deleted_at IS NULL` won't use the partial index.

```sql
-- Uses the partial index
SELECT * FROM users WHERE email = 'alice@example.com' AND deleted_at IS NULL;

-- Does NOT use the partial index — queries across all users
SELECT * FROM users WHERE email = 'alice@example.com';
```

Partial indexes shine for:
- Soft-deleted records (index only active rows)
- Status-filtered queries (index only `status = 'active'`)
- Unique constraints that should only apply to non-deleted records

## Covering indexes (include columns)

A covering index includes extra columns so the query can be answered from the index alone without touching the main table. PostgreSQL calls these index-only scans.

```sql
-- If queries always need (id, email, name), include name in the index
CREATE INDEX idx_users_email_covering ON users (email) INCLUDE (id, name);
```

```sql
-- Index-only scan: no heap fetch needed
SELECT id, name FROM users WHERE email = 'alice@example.com';
```

Without `INCLUDE`, PostgreSQL would find the row location in the index, then fetch the full row from the table (a heap fetch) just to get `name`. With covering indexes, that second lookup is eliminated.

## Checking index usage

```sql
-- See if a query uses an index
EXPLAIN SELECT * FROM posts WHERE status = 'published' ORDER BY created_at DESC LIMIT 10;

-- Index Scan → using index
-- Seq Scan → full table scan — may need an index
-- Bitmap Index Scan → multiple index lookups merged
```

```sql
-- Find unused indexes (accumulates since last stats reset)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;
```

An index with `idx_scan = 0` since the last stats reset may be a candidate for removal — it costs write overhead without benefiting reads. Verify by checking if the queries that should use it are actually running.

## Write overhead

Every index adds overhead to INSERT, UPDATE, and DELETE. A table with 5 indexes pays 5 index updates on every write. Index only what you actually query. Review and drop indexes that show zero usage in production.

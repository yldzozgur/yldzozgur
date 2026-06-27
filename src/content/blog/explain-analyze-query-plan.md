---
title: "EXPLAIN ANALYZE: reading a query plan to find the slow part."
description: "EXPLAIN ANALYZE runs a query and shows exactly how PostgreSQL executed it — which indexes were used, how many rows were scanned, and where the time was spent."
pubDate: 2024-09-26
tags: ["Security"]
draft: false
---

When a query is slow, guessing at the cause is inefficient. `EXPLAIN ANALYZE` eliminates guessing — it executes the query and annotates every step with actual row counts and timing. Once you can read a query plan, slow queries become diagnosable in minutes.

## EXPLAIN vs EXPLAIN ANALYZE

`EXPLAIN` estimates the plan without running the query. `EXPLAIN ANALYZE` runs the query and shows actual results. Always use `EXPLAIN ANALYZE` for debugging — the estimates can be wrong, and you need actual numbers.

```sql
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE user_id = 123
  AND status = 'pending'
ORDER BY created_at DESC
LIMIT 10;
```

## Reading the output

```
Limit  (cost=0.43..8.47 rows=10 width=128) (actual time=0.047..0.089 rows=10 loops=1)
  ->  Index Scan Backward using idx_orders_user_status_created on orders
        (cost=0.43..120.50 rows=150 width=128) (actual time=0.044..0.082 rows=10 loops=1)
        Index Cond: ((user_id = 123) AND (status = 'pending'))
Planning Time: 0.215 ms
Execution Time: 0.115 ms
```

**Node types**: each line is a plan node. Read from the bottom up — inner nodes feed outer nodes.

**cost=0.43..120.50**: estimated startup cost (time to first row) and total cost. These are in arbitrary units, not milliseconds. Use them for relative comparisons, not absolute timing.

**rows=150**: estimated row count. **actual ... rows=10**: the number actually returned. A large gap between estimated and actual rows indicates outdated statistics — run `ANALYZE` on the table.

**loops=1**: how many times this node executed. In nested loop joins, inner nodes execute once per outer row.

**actual time=0.044..0.082**: actual timing in milliseconds. First number is time to first row; second is time to last row.

## The key scan types

**Seq Scan (Sequential Scan)**: reads every row in the table. Fast for small tables or when you're reading most of the table. A Seq Scan on a large table for a selective query indicates a missing index.

```
Seq Scan on users  (actual time=0.023..842.156 rows=1 loops=1)
  Filter: (email = 'alice@example.com')
  Rows Removed by Filter: 499999
```

499,999 rows scanned to find 1. This needs an index on `email`.

**Index Scan**: uses an index to find rows, then fetches each row from the heap (main table storage). Fast for selective queries.

```
Index Scan using idx_users_email on users  (actual time=0.032..0.035 rows=1 loops=1)
  Index Cond: ((email)::text = 'alice@example.com')
```

**Index Only Scan**: all needed columns are in the index. No heap fetch. Fastest for covering indexes.

**Bitmap Index Scan → Bitmap Heap Scan**: collects all matching row locations first, then fetches them in physical order. More efficient than Index Scan when many rows match (reduces random I/O).

## Finding the slow node

Add `BUFFERS` to see cache activity:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
```

Look for nodes with high `actual time`. The slowest node is usually:
- A Seq Scan on a large table
- A Hash Join or Sort with a large `rows` count
- A node with many `loops`

```
Hash Join  (actual time=245.823..1892.445 rows=50000 loops=1)
  Hash Cond: (orders.user_id = users.id)
  ->  Seq Scan on orders  (actual time=0.021..421.332 rows=1000000 loops=1)
  ->  Hash  (actual time=12.445..12.445 rows=5000 loops=1)
        ->  Seq Scan on users  (actual time=0.015..8.221 rows=5000 loops=1)
```

The bottleneck is the Seq Scan on `orders`. Index `orders.user_id` to fix the Hash Join cost.

## Outdated statistics

If estimated rows are way off actual rows:

```sql
-- Update table statistics
ANALYZE orders;

-- Update all tables
ANALYZE;
```

PostgreSQL autovacuum runs ANALYZE periodically, but after a bulk import or significant data change, running it manually helps the planner make better decisions.

## Practical workflow

1. Identify the slow query from logs or APM
2. Run `EXPLAIN (ANALYZE, BUFFERS)` with representative parameters
3. Find the node with the highest actual time
4. Check if that node is a Seq Scan — if so, check if an index would help
5. Check if estimated rows match actual rows — if not, run `ANALYZE`
6. Add index, re-run, compare timing

```sql
-- Before: 842ms, Seq Scan
CREATE INDEX idx_users_email ON users (email);

-- After: 0.035ms, Index Scan
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'alice@example.com';
```

Use `pg_stat_statements` extension in production to track query performance over time without running EXPLAIN manually:

```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

This shows which queries consume the most total time, making them the best candidates for optimization.

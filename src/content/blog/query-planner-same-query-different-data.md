---
title: "The query planner: why the same query runs differently on different data."
description: "PostgreSQL's query planner chooses how to execute a query based on table statistics. Understanding that process explains why query performance changes as data changes."
pubDate: 2026-06-25
tags: ["PostgreSQL", "Performance"]
draft: false
---

The same SQL query can run in 2ms on one table and 20 seconds on another — not because of the query itself, but because of the choices the query planner makes. Understanding how the planner works explains why query performance is data-dependent and what you can do about it.

## What the planner does

When you submit a query, PostgreSQL's planner generates multiple execution strategies and estimates the cost of each. It picks the plan with the lowest estimated cost.

```sql
EXPLAIN SELECT * FROM orders
WHERE customer_id = 'cust_123'
ORDER BY created_at DESC
LIMIT 20;
```

The output shows the plan the planner chose:

```
Limit  (cost=0.43..42.11 rows=20 width=128)
  ->  Index Scan Backward using orders_customer_created_idx on orders
        (cost=0.43..2104.52 rows=1000 width=128)
        Index Cond: (customer_id = 'cust_123'::uuid)
```

Cost is expressed in arbitrary units (roughly: disk page reads). The planner estimated this customer has 1000 orders and chose an index scan.

## Table statistics

The planner's cost estimates depend on statistics collected by `ANALYZE`. These statistics are stored in `pg_statistic` and exposed through `pg_stats`.

```sql
-- What the planner knows about a column
SELECT
  tablename,
  attname AS column,
  n_distinct,       -- estimated number of distinct values
  correlation,      -- how sorted the data is on disk (-1 to 1)
  most_common_vals, -- most frequent values
  most_common_freqs -- their frequencies
FROM pg_stats
WHERE tablename = 'orders' AND attname = 'status';
```

From `n_distinct` and `most_common_freqs`, the planner can estimate how many rows a WHERE clause will return. That estimate drives the plan choice.

## How statistics affect plan choice

```sql
-- If the planner knows status = 'pending' returns 1% of rows:
-- Index scan is cheaper (scan 1% of index, fetch 1% of heap)

-- If the planner knows status = 'delivered' returns 80% of rows:
-- Sequential scan is cheaper (random heap access for 80% of rows
-- is slower than reading the whole table sequentially)

EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'pending';
-- likely: Index Scan

EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'delivered';
-- likely: Seq Scan
```

The plan switch between these two queries is correct behavior — the planner is making a better choice for the data distribution.

## When the planner gets it wrong

The planner's estimates can be wrong when:

1. Statistics are stale (data changed significantly since the last ANALYZE)
2. The data distribution is unusual (exponential distribution, heavy skew)
3. Multiple correlated column filters interact in ways the planner doesn't model
4. Statistics have insufficient resolution for high-cardinality columns

```sql
-- Check when statistics were last collected
SELECT relname, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'orders';

-- Manually update statistics (autovacuum does this automatically, but on a schedule)
ANALYZE orders;

-- Increase statistics resolution for a column with high cardinality
ALTER TABLE orders ALTER COLUMN customer_id SET STATISTICS 500;
-- Default is 100 (samples 100 distinct values); up to 10000
ANALYZE orders;
```

## EXPLAIN ANALYZE: actual vs. estimated

Adding `ANALYZE` to `EXPLAIN` runs the query and shows both estimated and actual row counts:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders
WHERE customer_id = 'cust_123'
AND status = 'pending';
```

```
Index Scan using orders_customer_idx on orders
  (cost=0.43..2104.52 rows=10 width=128)
  (actual time=0.082..45.231 rows=8924 loops=1)
  Index Cond: (customer_id = 'cust_123'::uuid)
  Filter: (status = 'pending'::text)
  Rows Removed by Filter: 91076
  Buffers: shared hit=412 read=8823
```

The planner estimated 10 rows; the actual result was 8,924. This dramatic underestimate means the planner chose an index scan that was actually much more expensive than a sequential scan would have been. The source of the error: the planner estimated the filters independently, not knowing that `customer_id = 'cust_123'` and `status = 'pending'` are correlated (this customer creates many pending orders).

## Extended statistics for correlated columns

PostgreSQL can model correlations between columns with extended statistics:

```sql
-- Create statistics capturing the correlation between customer_id and status
CREATE STATISTICS orders_customer_status_stats (dependencies)
ON customer_id, status
FROM orders;

ANALYZE orders;

-- Now the planner accounts for the correlation
EXPLAIN SELECT * FROM orders
WHERE customer_id = 'cust_123' AND status = 'pending';
-- Rows estimate is much closer to actual
```

## Plan instability

A plan that works well today can degrade as data grows. A query that used an index scan at 10,000 rows might switch to a sequential scan at 10 million rows — and that switch might be wrong if the selectivity hasn't changed proportionally.

```sql
-- Force a specific plan for testing (not for production use)
SET enable_seqscan = off; -- disable sequential scans
EXPLAIN SELECT * FROM orders WHERE customer_id = 'cust_123';
-- Planner is forced to use an index even if it prefers a seq scan

-- pg_hint_plan extension for production plan hints (use sparingly)
/*+ IndexScan(orders orders_customer_idx) */
SELECT * FROM orders WHERE customer_id = 'cust_123';
```

The right response to plan instability is usually better statistics, better indexes, or schema changes — not plan hints. Hints lock you into a plan that may become wrong as data evolves. Understanding the planner's reasoning leads to fixes that stay correct.

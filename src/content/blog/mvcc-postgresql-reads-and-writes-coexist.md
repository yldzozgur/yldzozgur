---
title: "MVCC: how PostgreSQL lets reads and writes coexist."
description: "PostgreSQL's MVCC keeps multiple versions of each row so readers never block writers and writers never block readers. Here's how the mechanism works."
pubDate: 2026-06-11
tags: ["PostgreSQL"]
draft: false
---

In most database systems, reads and writes to the same row compete. A read that arrives during a write must wait for the write to finish, or the write must wait for the read. PostgreSQL avoids this contention through Multi-Version Concurrency Control (MVCC) — a system where each transaction sees a consistent snapshot of the database without blocking other transactions.

## The core idea

Instead of modifying rows in place and blocking concurrent access, PostgreSQL keeps multiple versions of each row. When a transaction updates a row, it creates a new version of that row and marks the old version as superseded. When a transaction reads, it sees only the versions that existed at the start of its snapshot — not newer versions that appeared after it began.

This means:
- Readers never wait for writers — they read old versions while new ones are being written
- Writers never wait for readers — they write new versions while readers read old ones
- Each transaction gets a consistent view of the database as it was at a point in time

## Row versions and transaction IDs

Every row in PostgreSQL has two hidden system columns:

- `xmin`: the transaction ID that created this row version
- `xmax`: the transaction ID that deleted or superseded this row version (0 if still current)

```sql
-- See the hidden system columns
SELECT id, name, xmin, xmax FROM users LIMIT 5;

-- id | name  | xmin | xmax
-- ---+-------+------+------
--  1 | Alice | 1234 |    0   <- current version, created by txn 1234
--  2 | Bob   | 1235 | 1290   <- old version, deleted by txn 1290
```

When a transaction updates a row:
1. The old row version gets `xmax` set to the current transaction ID.
2. A new row version is inserted with `xmin` set to the current transaction ID.

The old version remains on disk until vacuumed — it's needed for other transactions that started before this update and should still see the old value.

## Snapshot isolation

When a transaction starts, PostgreSQL takes a snapshot recording:
- The current transaction ID (`xmax` of the snapshot)
- The set of in-progress transactions at snapshot time

A row version is visible to a transaction if:
- Its `xmin` was committed before the snapshot was taken (the row existed at snapshot time)
- Its `xmax` is either 0 (not deleted) or represents a transaction that started after the snapshot

```sql
-- Transaction A begins — gets snapshot at txid 1000
BEGIN;

-- Transaction B starts and updates a row
-- (xmin=1001, xmax=0 for the new version)
-- (xmin=999, xmax=1001 for the old version)

-- Transaction A still reads the old version (xmin=999, xmax=1001)
-- because txid 1001 > 1000 (started after A's snapshot)
SELECT * FROM users WHERE id = 1; -- sees the pre-update value

COMMIT;
```

## Isolation levels in practice

```sql
-- Read Committed (default): snapshot taken at each statement
BEGIN;
-- Sees committed changes from other transactions between statements
SELECT count(*) FROM orders; -- might differ from next count
SELECT count(*) FROM orders; -- if another txn committed between statements
COMMIT;

-- Repeatable Read: snapshot taken at transaction start
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM orders; -- consistent
-- ... time passes, other transactions commit ...
SELECT count(*) FROM orders; -- same result as before
COMMIT;

-- Serializable: full isolation, detects anomalies and aborts if needed
BEGIN ISOLATION LEVEL SERIALIZABLE;
-- PostgreSQL detects if the transaction's reads/writes conflict with
-- concurrent serializable transactions and rolls back if needed
COMMIT;
```

## VACUUM: cleaning up dead versions

Old row versions accumulate. A row updated 100 times has 100 versions on disk. VACUUM reclaims this space by removing versions that no open transaction can still see.

```sql
-- Manual vacuum for a specific table
VACUUM users;

-- Vacuum with statistics update
VACUUM ANALYZE users;

-- See dead tuple accumulation
SELECT
  relname AS table,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

Autovacuum runs automatically based on how many dead tuples accumulate. Tables with high update/delete rates need more aggressive autovacuum settings.

## Transaction ID wraparound

PostgreSQL uses 32-bit transaction IDs. After about 2 billion transactions, the IDs wrap around. Without VACUUM cleaning up old row versions and advancing the oldest visible transaction, wraparound would cause old row versions to become invisible (their `xmin` would appear to be "in the future" after wraparound). This is a catastrophic failure mode.

```sql
-- Check for tables approaching wraparound
SELECT
  relname,
  age(relfrozenxid) AS xid_age,
  2000000000 - age(relfrozenxid) AS txns_until_forced_vacuum
FROM pg_class
WHERE relkind = 'r'
ORDER BY age(relfrozenxid) DESC
LIMIT 10;
```

VACUUM FREEZE marks old rows as permanently visible, removing their dependency on transaction ID comparison. PostgreSQL forces autovacuum on tables approaching the wraparound limit. Monitoring `xid_age` is a non-optional operational responsibility for PostgreSQL DBAs.

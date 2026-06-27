---
title: "Write-ahead logging: the mechanism behind database durability."
description: "WAL is how PostgreSQL guarantees that committed transactions survive crashes. Understanding it explains database performance characteristics and replication."
pubDate: 2026-06-08
tags: ["PostgreSQL", "Databases"]
draft: false
---

When PostgreSQL confirms a transaction commit, it's making a promise: even if the server crashes immediately afterward, that data won't be lost. Write-ahead logging (WAL) is the mechanism that makes good on that promise.

## The problem WAL solves

PostgreSQL stores its data on disk in 8KB pages (blocks). When you update a row, the change modifies an in-memory buffer pool page. Writing that page back to disk immediately on every change would be prohibitively slow — it would mean one random write per row modification.

Instead, PostgreSQL writes changes to a sequential log first — the WAL — before modifying the actual data pages. Sequential writes are much faster than random writes. The data pages can be written back to disk later, in the background, in batches.

If the server crashes before a data page is written, the WAL provides the information needed to replay the changes and restore consistency.

## WAL structure

The WAL is a sequence of records stored in files in the `pg_wal` directory. Each record describes a specific change:

```
LSN 0/1A3B4C: INSERT into relation 16384 (users) at block 42, offset 128
  - Page: 16384/0/42
  - Tuple data: (id=5, email='user@example.com', name='Alice')
  - Transaction ID: 12345

LSN 0/1A3B68: COMMIT transaction 12345
  - Timestamp: 2026-06-08 10:00:00.123
```

LSN stands for Log Sequence Number — a monotonically increasing position in the WAL. Every record has an LSN. The LSN of the latest flushed WAL record is what determines the "durability frontier."

## The commit sequence

When you commit a transaction:

1. PostgreSQL writes all WAL records for the transaction's changes.
2. PostgreSQL writes a COMMIT record to the WAL.
3. PostgreSQL calls `fsync()` to flush the WAL to durable storage.
4. Only after `fsync()` returns does PostgreSQL send "commit success" to the client.

The data pages themselves may still be in memory (dirty buffers) when the client receives the confirmation. The checkpoint process writes dirty pages to disk in the background. But if the server crashes before a checkpoint, PostgreSQL can replay the WAL to recover.

## WAL and performance settings

```sql
-- Check current WAL settings
SHOW wal_level;          -- minimal | replica | logical
SHOW synchronous_commit; -- on | off | local | remote_write | remote_apply
SHOW checkpoint_timeout;
SHOW max_wal_size;
```

`synchronous_commit = off` is a performance optimization that tells PostgreSQL not to wait for the WAL to be flushed before reporting commit success. Transactions commit faster, but a crash within a few milliseconds of commit could lose committed transactions. The data remains consistent — you'll never see partial transactions — but some commits may be silently rolled back.

```sql
-- Per-transaction control
BEGIN;
SET LOCAL synchronous_commit = off; -- faster commits for this transaction
INSERT INTO analytics_events (event_type, user_id) VALUES ($1, $2);
COMMIT; -- doesn't wait for WAL flush
```

This is appropriate for high-volume writes where occasional loss of recent data is acceptable (analytics, session data, telemetry).

## WAL and replication

Streaming replication works by shipping WAL records from the primary to replicas. The replica applies the same WAL records the primary generated, keeping its data pages in sync.

```sql
-- On primary: check replication lag
SELECT
  client_addr,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  (sent_lsn - replay_lsn) AS replication_lag_bytes
FROM pg_stat_replication;
```

Logical replication (as opposed to physical replication) decodes WAL records into logical changes (INSERT, UPDATE, DELETE) that can be applied to a different schema version or a different database system.

## WAL and point-in-time recovery

Continuous WAL archiving enables point-in-time recovery (PITR):

```bash
# postgresql.conf settings for WAL archiving
archive_mode = on
archive_command = 'cp %p /wal-archive/%f'
```

With a base backup and WAL archives, you can restore the database to any point in time. This is how managed databases (RDS, Cloud SQL, Supabase) implement their point-in-time restore features.

## Inspecting WAL

```sql
-- Current WAL position
SELECT pg_current_wal_lsn();

-- Size of WAL generated between two points
SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '0/1A3B4C');

-- WAL file containing a given LSN
SELECT pg_walfile_name('0/1A3B4C');
```

Understanding WAL explains why sequential write workloads are faster than random ones, why replication lag exists, and why certain performance knobs (synchronous_commit, checkpoint_completion_target) have the effects they do. It's the foundation on which PostgreSQL's durability guarantees rest.

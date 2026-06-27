---
title: "Database transactions: what ACID actually guarantees."
description: "What ACID properties mean in practice, with concrete examples of what breaks when each guarantee is violated."
pubDate: 2025-07-28
tags: ["DevOps"]
draft: false
---

ACID is one of those acronyms that appears in every database tutorial but is rarely explained in terms of what actually happens to your data. Atomicity, Consistency, Isolation, Durability. Each property prevents a specific class of data corruption. Understanding what they guarantee tells you what you can rely on and what you cannot.

## Atomicity

Atomicity guarantees that all operations in a transaction either all succeed or all fail. There is no partial completion.

The classic example is a bank transfer:

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
```

If the database crashes between the two UPDATE statements, atomicity ensures neither update persists. The first debit does not exist without the corresponding credit. When the database recovers, it rolls back the incomplete transaction.

Without atomicity, $100 could disappear from account 1 without appearing in account 2. The money vanishes.

In application code, the equivalent pattern is wrapping operations in a transaction block that rolls back on error:

```python
with db.transaction():
    account1.balance -= 100
    # If anything raises here, the transaction rolls back
    account2.balance += 100
```

## Consistency

Consistency guarantees that a transaction brings the database from one valid state to another valid state. It does not allow the database to end up in a state that violates defined constraints.

If you have a constraint that account balances cannot go negative:

```sql
ALTER TABLE accounts ADD CONSTRAINT positive_balance CHECK (balance >= 0);
```

Then a transaction that would produce a negative balance will fail and roll back. The constraint enforces a business rule at the database level. No application code can accidentally bypass it.

Consistency is the only ACID property that depends on the application as much as the database. Constraints you do not define are not enforced.

## Isolation

Isolation determines how concurrent transactions see each other's work. This is the most nuanced ACID property because it comes in levels that trade correctness for performance.

The default in most production databases (PostgreSQL, MySQL InnoDB) is Read Committed. This prevents dirty reads - you cannot read data from a transaction that has not yet committed.

The problem Read Committed does not prevent is non-repeatable reads:

```sql
-- Transaction A
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  -- Returns 500
-- Transaction B commits, setting balance to 400
SELECT balance FROM accounts WHERE id = 1;  -- Returns 400, different value!
COMMIT;
```

Transaction A reads the same row twice and gets different values. If your application logic depends on a value not changing mid-transaction, this is a bug.

Serializable isolation prevents this:

```sql
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- All reads within this transaction are consistent
-- as of the start of the transaction
COMMIT;
```

Serializable isolation has higher lock overhead. Use it when your transaction logic depends on data not changing between reads - generating sequential invoice numbers, enforcing uniqueness across a set of rows, computing aggregates that must be consistent.

The common isolation levels from weakest to strongest:
- Read Uncommitted: can read uncommitted data (almost never used)
- Read Committed: cannot read uncommitted data (default in most databases)
- Repeatable Read: reads are stable within a transaction
- Serializable: transactions appear to execute sequentially

## Durability

Durability guarantees that once a transaction commits, it stays committed even if the database crashes immediately after.

This is achieved through write-ahead logging (WAL). Before any data page on disk is modified, the change is written to a sequential log. On crash recovery, the database replays the log to reconstruct any changes that were committed but not yet written to the main data files.

Durability means that a successful COMMIT response from the database is a promise. The data is persisted. You do not need to verify it. You do not need to read it back.

The cost is that each COMMIT requires a synchronous disk write to the WAL. This is why databases offer `fsync=off` settings that improve write throughput dramatically - but at the cost of durability. With fsync off, a crash can lose committed transactions. This is appropriate for test environments, not production.

## What ACID does not guarantee

ACID does not guarantee correctness of your application logic. A transaction that correctly debits the wrong account is atomic, consistent, isolated, and durable - and still wrong.

ACID does not prevent all concurrency bugs. Lost updates can occur at Read Committed isolation if two transactions both read a value and both write based on that read without using `SELECT FOR UPDATE`:

```sql
-- Both transactions read balance = 500
-- Both compute 500 + 100 = 600
-- Both write 600
-- One update is lost
```

The fix is pessimistic locking:

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;  -- Locks the row
UPDATE accounts SET balance = balance + 100 WHERE id = 1;
COMMIT;
```

Or optimistic locking with a version column that causes one transaction to fail if the row changed since it was read.

ACID gives you a solid foundation. What you build on top of it determines correctness.

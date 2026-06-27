---
title: "Soft deletes: why you almost never want to actually delete data."
description: "Hard deletes are irreversible and break foreign key references. The soft delete pattern marks records as deleted while keeping them in the database, enabling recovery and audit trails."
pubDate: 2024-09-02
tags: ["Security"]
draft: false
---

When a user clicks "delete," most applications should not actually remove the row from the database. The soft delete pattern — marking a record as deleted without removing it — solves several real problems that hard deletes create.

## Why hard deletes cause problems

**Recovery is impossible.** When a user accidentally deletes something important, your only option is a database backup restore. Depending on your backup schedule, this could mean hours of data loss.

**Audit trails break.** If you're keeping logs of "user X did Y," and user X's account is hard-deleted, you have orphaned log entries with no way to reconstruct what happened.

**Foreign key violations.** In a relational database, deleting a user who has orders, comments, or activity records breaks referential integrity unless you cascade delete everything (worse) or set columns to null (loses context).

**Analytics gaps.** Historical reports compare cohorts over time. If users who churned are hard-deleted, your retention curves look better than they are.

## The pattern

Add two fields to every table that should support soft deletes:

```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN deleted_by UUID REFERENCES users(id);
```

Or in a Mongoose schema:

```js
const userSchema = new Schema({
  email: String,
  name: String,
  deletedAt: { type: Date, default: null },
  deletedBy: { type: Schema.Types.ObjectId, ref: "User", default: null },
});
```

"Deleting" a record sets `deleted_at`:

```js
async function softDeleteUser(userId, deletedByUserId) {
  await db.users.updateOne(
    { _id: userId },
    {
      $set: {
        deletedAt: new Date(),
        deletedBy: deletedByUserId,
      },
    }
  );
}
```

## Filtering deleted records

Every query against soft-deletable tables must filter out deleted records:

```js
// Always add this filter
const users = await User.find({ deletedAt: null });
const user = await User.findOne({ _id: id, deletedAt: null });
```

This is where soft deletes become a maintenance burden — it's easy to forget the filter and accidentally expose deleted records. Middleware helps enforce it:

```js
// Mongoose query middleware: apply filter automatically
userSchema.pre(/^find/, function () {
  // 'this' is the query
  this.where({ deletedAt: null });
});

// Now you don't need to remember to filter
const users = await User.find({ role: "admin" }); // automatically excludes deleted
```

For explicit admin access to deleted records:

```js
const deletedUsers = await User.find({ deletedAt: { $ne: null } }).setOptions({
  skipDeletedFilter: true, // custom option to bypass the pre-hook
});
```

## PostgreSQL: Row Level Security approach

In PostgreSQL, you can enforce soft deletes at the database level:

```sql
-- Create a view that excludes soft-deleted records
CREATE VIEW active_users AS
  SELECT * FROM users WHERE deleted_at IS NULL;

-- Application queries use the view, not the base table
SELECT * FROM active_users WHERE email = $1;

-- Admin queries use the base table directly
SELECT * FROM users WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC;
```

## Indexing deleted_at

Add an index on `deleted_at` (or a partial index on non-deleted records):

```sql
-- PostgreSQL: partial index — only indexes active records
-- Makes queries for active records fast; deleted records not in index
CREATE INDEX idx_users_active ON users (email) WHERE deleted_at IS NULL;
```

```js
// Mongoose
userSchema.index({ deletedAt: 1, email: 1 });
```

Without indexing, every query that filters `deleted_at: null` does a full scan.

## Recovery

Restoring a soft-deleted record is a single update:

```js
async function restoreUser(userId) {
  await db.users.updateOne(
    { _id: userId },
    { $set: { deletedAt: null, deletedBy: null } }
  );
}
```

Compare this to recovering a hard-deleted record: restore from backup, find the row, re-insert it, re-establish all foreign key relationships. Soft deletes make recovery trivial.

## When to actually hard delete

Soft deletes are not appropriate everywhere:

**Regulatory requirements**: GDPR right to erasure requires genuinely removing personal data. Soft deletes don't satisfy this. For GDPR-scoped data, you may need to hard delete or anonymize (replace PII with null/placeholder values while keeping the record for relational integrity).

**High-volume transient data**: logging tables, event streams, analytics events — these grow indefinitely and don't need recovery. Archive or purge them on a schedule.

**Truly ephemeral data**: sessions, one-time tokens, rate limit counters — these have no business reason to be recoverable.

The default for user-generated content, user accounts, and business records should be soft delete. The default for everything else is to think carefully before choosing either.

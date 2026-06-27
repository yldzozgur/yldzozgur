---
title: "MongoDB without indexes is a full collection scan every time."
description: "Without the right indexes, every query MongoDB runs reads every document in the collection. Here's how indexes work, how to create them, and how to verify they're being used."
pubDate: 2024-08-12
tags: ["Security"]
draft: false
---

A query against an unindexed field in MongoDB examines every document in the collection. For a collection with 1 million documents, a query that returns one result still reads all 1 million. This is called a collection scan (COLLSCAN), and it's why apps that work fine during development become slow after launch — development databases have hundreds of documents; production has millions.

## How indexes work

An index maintains a sorted data structure (a B-tree) over one or more fields. When MongoDB processes a query against an indexed field, it uses the B-tree to jump directly to the matching documents instead of scanning everything. The index lookup is O(log n); the collection scan is O(n).

MongoDB automatically creates one index: `_id`. Everything else you create.

## Creating basic indexes

```js
// In Mongoose schema definition
const userSchema = new Schema({
  email: { type: String, unique: true }, // unique: true creates a unique index
  username: { type: String },
  createdAt: { type: Date },
});

userSchema.index({ username: 1 }); // 1 = ascending, -1 = descending
userSchema.index({ createdAt: -1 }); // latest first queries are common
```

Or directly via the MongoDB driver:

```js
await db.collection("users").createIndex({ email: 1 }, { unique: true });
await db.collection("users").createIndex({ createdAt: -1 });
```

## Compound indexes

A compound index covers multiple fields. It can satisfy queries on the leftmost fields:

```js
// This index covers:
// - queries on { status }
// - queries on { status, createdAt }
// - sort on { status: 1, createdAt: -1 } with any status filter
// It does NOT cover:
// - queries on only { createdAt } — wrong order
userSchema.index({ status: 1, createdAt: -1 });
```

This is the **prefix rule**: a compound index on `{ a, b, c }` covers queries on `a`, `a + b`, and `a + b + c`, but not `b`, `c`, or `b + c` alone.

Example query patterns that benefit from `{ status: 1, createdAt: -1 }`:

```js
// Uses index
Post.find({ status: "published" }).sort({ createdAt: -1 });

// Uses index (prefix only)
Post.find({ status: "draft" });

// Does NOT use compound index efficiently — only createdAt, no status
Post.find({}).sort({ createdAt: -1 });
```

## Verifying index usage with explain

`explain("executionStats")` tells you exactly what MongoDB did to answer a query:

```js
const result = await Post
  .find({ status: "published" })
  .sort({ createdAt: -1 })
  .limit(20)
  .explain("executionStats");

console.log(result.executionStats.executionStages.stage);
// "IXSCAN" means index scan — good
// "COLLSCAN" means collection scan — needs an index

console.log(result.executionStats.totalDocsExamined);
// Should be close to the number of results returned
// If this number is much larger than nReturned, the index is not selective enough
```

The key fields to check:
- `stage`: `IXSCAN` (good) vs `COLLSCAN` (bad)
- `totalDocsExamined`: documents read to fulfill the query
- `nReturned`: documents actually returned
- `executionTimeMillis`: how long it took

A well-indexed query has `totalDocsExamined` close to `nReturned`. A poorly indexed one has `totalDocsExamined` equal to the total collection size.

## Sparse and partial indexes

**Sparse indexes** only index documents where the field exists:

```js
userSchema.index({ phoneNumber: 1 }, { sparse: true });
// Documents without phoneNumber are not in this index
// Useful for optional fields where most documents won't have the field
```

**Partial indexes** index only documents matching a filter:

```js
// Only index posts that are published — drafts don't need to be found by slug
await db.collection("posts").createIndex(
  { slug: 1 },
  { partialFilterExpression: { status: "published" }, unique: true }
);
```

Partial indexes are smaller and faster to update than full indexes. They're ideal when you only need to query a subset of documents.

## The index tax

Indexes are not free. Every write (insert, update, delete) must also update all relevant indexes. A collection with 10 indexes pays 10 index update operations on every write. For write-heavy collections, too many indexes hurt write throughput.

The balance: add indexes for every query pattern your application actually uses. Don't add indexes speculatively. You can identify missing indexes by looking for COLLSCAN in slow query logs or in MongoDB Atlas performance advisor.

```js
// List all indexes on a collection
const indexes = await db.collection("posts").indexes();
console.log(indexes);

// Drop an unused index
await db.collection("posts").dropIndex("old_field_1");
```

Index your query fields, especially in filters (`find()` conditions), sort fields, and fields used in `$lookup` joins. An unindexed `$lookup` on a large collection is one of the most common MongoDB performance killers.

---
title: "MongoDB transactions: what they cost and when they're worth it."
description: "MongoDB supports multi-document ACID transactions since version 4.0, but they carry overhead. Understand when you genuinely need them and when document modeling eliminates the need."
pubDate: 2024-08-19
tags: ["Security"]
draft: false
---

MongoDB added multi-document ACID transactions in version 4.0, which surprised developers who had learned "MongoDB doesn't support transactions." The common advice was to model your data such that all related changes fit in a single document — which is still good advice. But some operations genuinely span multiple documents, and for those, transactions are now available.

## When you actually need a transaction

A transaction is necessary when you need to make multiple document writes atomically — either all succeed or all fail, with no partial state visible to other readers.

Classic example: transferring money between two accounts.

```js
// Without a transaction, these two updates can partially succeed
await Account.updateOne({ _id: fromId }, { $inc: { balance: -100 } });
// crash here? fromId is debited, toId is not credited
await Account.updateOne({ _id: toId }, { $inc: { balance: 100 } });
```

With a transaction:

```js
const session = await mongoose.startSession();
session.startTransaction();

try {
  await Account.updateOne(
    { _id: fromId, balance: { $gte: 100 } },
    { $inc: { balance: -100 } },
    { session }
  );

  await Account.updateOne(
    { _id: toId },
    { $inc: { balance: 100 } },
    { session }
  );

  await session.commitTransaction();
} catch (err) {
  await session.abortTransaction();
  throw err;
} finally {
  session.endSession();
}
```

The `{ session }` option on each operation enrolls it in the transaction. If anything throws, `abortTransaction()` rolls back both updates.

## The with-transaction helper

Mongoose provides a cleaner API that handles retry logic for transient errors:

```js
async function transfer(fromId, toId, amount) {
  const session = await mongoose.startSession();

  return session.withTransaction(async () => {
    const from = await Account.findOneAndUpdate(
      { _id: fromId, balance: { $gte: amount } },
      { $inc: { balance: -amount } },
      { session, new: true }
    );

    if (!from) {
      throw new Error("Insufficient funds or account not found");
    }

    await Account.findByIdAndUpdate(
      toId,
      { $inc: { balance: amount } },
      { session }
    );
  });
}
```

`withTransaction` automatically retries on transient transaction errors (like write conflicts) and commits on success.

## What transactions cost

Transactions in MongoDB carry real overhead:

**Latency**: a transaction acquires locks and coordinates across the replica set's oplog. Each write within a transaction has higher latency than a standalone write.

**Resource usage**: transactions hold locks for their duration. Long-running transactions can block other writers.

**60-second hard limit**: MongoDB aborts any transaction that runs longer than 60 seconds. Transactions are not a tool for long-running batch operations.

**Replica set only**: transactions require a replica set (or a sharded cluster with replica sets). They don't work on standalone MongoDB instances. Atlas always uses replica sets.

**Retryable writes**: simple single-document writes are retryable by default (the driver retries them once on transient errors). Transactions require you to handle this explicitly, hence `withTransaction`.

## When document modeling eliminates the need

Many situations that seem to require transactions don't, if you model the data correctly.

**Order + inventory update**: instead of updating an inventory document and creating an order document separately, create the order with a status of "pending" first, then confirm it. Or use a reservation pattern — decrement inventory optimistically and reconcile asynchronously.

**Audit logs**: instead of updating a record and inserting an audit log entry in a transaction, embed recent changes in the document itself, or use a change stream to create audit logs asynchronously.

**Single document writes are already atomic**: MongoDB guarantees that writes to a single document are atomic, including writes to embedded arrays and nested objects. If you can restructure your data so a "transaction" is really just updating one document, you get atomicity for free.

```js
// Atomic: updating multiple fields and an embedded array in one document
await Order.updateOne(
  { _id: orderId },
  {
    $set: { status: "confirmed" },
    $push: { history: { status: "confirmed", at: new Date() } },
    $inc: { version: 1 },
  }
);
// All of this either succeeds or fails — no transaction needed
```

## The rule

Use transactions when you genuinely need cross-document atomicity and the data model can't be restructured to avoid it. Don't use transactions as a substitute for thinking about data modeling. Start with the simplest model, identify which operations require cross-document consistency, and apply transactions only to those.

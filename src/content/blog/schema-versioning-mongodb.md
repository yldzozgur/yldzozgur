---
title: "Schema versioning in MongoDB: migrations without downtime."
description: "MongoDB's flexible schema doesn't eliminate the need for migrations — it changes how you do them. Here's the lazy migration pattern that updates documents without a big-bang script."
pubDate: 2024-08-26
tags: ["Security"]
draft: false
---

The common assumption is that MongoDB's schemaless nature means you never have to think about migrations. In practice, applications evolve, and data that was stored in one shape needs to be read in another. The difference from relational databases is that MongoDB lets you handle this gradually rather than with a blocking ALTER TABLE statement.

## The problem

You stored user addresses as a flat string:

```js
// Old format
{ _id: ObjectId("..."), name: "Alice", address: "123 Main St, Austin TX 78701" }
```

The new feature needs a structured address:

```js
// New format
{
  _id: ObjectId("..."),
  name: "Alice",
  address: {
    street: "123 Main St",
    city: "Austin",
    state: "TX",
    zip: "78701"
  }
}
```

In PostgreSQL, you'd run a migration that alters the column type and backfills all rows. In MongoDB, you have options that don't require touching all documents at once.

## The schema version field

Add a `schemaVersion` field to every document. When you read a document, check its version and upgrade it if needed:

```js
const CURRENT_VERSION = 2;

function upgradeDocument(user) {
  if (!user.schemaVersion || user.schemaVersion < 1) {
    // v0 → v1: no changes tracked, assume initial format
    user.schemaVersion = 1;
  }

  if (user.schemaVersion < 2) {
    // v1 → v2: convert flat address to structured
    if (typeof user.address === "string") {
      const parts = user.address.split(",").map((s) => s.trim());
      user.address = {
        street: parts[0] ?? "",
        city: parts[1] ?? "",
        state: parts[2]?.split(" ")[0] ?? "",
        zip: parts[2]?.split(" ")[1] ?? "",
      };
    }
    user.schemaVersion = 2;
  }

  return user;
}
```

## Lazy migration on read

Read the document, upgrade it in memory, save it back:

```js
async function getUser(id) {
  const user = await db.users.findOne({ _id: new ObjectId(id) });
  if (!user) return null;

  if (user.schemaVersion < CURRENT_VERSION) {
    const upgraded = upgradeDocument(user);
    // Save the upgraded version back
    await db.users.replaceOne({ _id: user._id }, upgraded);
    return upgraded;
  }

  return user;
}
```

This upgrades documents one at a time as they're accessed, spreading the work across normal application traffic. Documents for inactive users stay in the old format until those users return.

## Lazy migration in Mongoose

With Mongoose, a post-init hook handles this transparently:

```js
const userSchema = new Schema({
  name: String,
  address: Schema.Types.Mixed, // supports both string and object
  schemaVersion: { type: Number, default: 1 },
});

userSchema.post("init", async function () {
  if (this.schemaVersion < CURRENT_VERSION) {
    upgradeDocument(this);
    await this.save();
  }
});
```

Every document that comes out of `find()` or `findOne()` passes through this hook. Upgraded documents are saved back automatically.

## Background migration for completeness

Lazy migration means old-format documents exist until those users are active. If you need all documents in the new format (for a query that assumes the new shape, or for a future schema change), run a background migration that processes documents in batches:

```js
async function backfillSchemaVersion() {
  const batchSize = 1000;
  let processed = 0;
  let cursor = db.users
    .find({ schemaVersion: { $lt: CURRENT_VERSION } })
    .batchSize(batchSize);

  for await (const user of cursor) {
    const upgraded = upgradeDocument(user);
    await db.users.replaceOne({ _id: user._id }, upgraded);
    processed++;

    if (processed % batchSize === 0) {
      console.log(`Migrated ${processed} documents`);
      // Optional: small delay to avoid overwhelming the database
      await new Promise((r) => setTimeout(r, 10));
    }
  }

  console.log(`Migration complete: ${processed} documents upgraded`);
}
```

Run this as a background job, not as a blocking startup step. It can take hours on large collections and should not prevent your application from starting.

## Writing new code that handles both formats

During a migration, your application must handle both old and new document shapes. Write your code to accept both:

```js
function formatAddress(user) {
  if (typeof user.address === "string") {
    // Old format: return as-is for display
    return user.address;
  }
  if (user.address && typeof user.address === "object") {
    // New format: reconstruct display string
    const { street, city, state, zip } = user.address;
    return `${street}, ${city} ${state} ${zip}`;
  }
  return "No address";
}
```

Once the background migration is complete and all documents are at the current version, you can remove the compatibility code.

## The deploy order

1. Deploy code that reads both old and new format, writes new format
2. Start lazy migration (documents upgrade on read)
3. Run background backfill job
4. After all documents are at current version, remove old-format compatibility code

This sequence means no downtime and no big-bang migration that might fail halfway through.

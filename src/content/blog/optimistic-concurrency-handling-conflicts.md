---
title: "Optimistic concurrency: handling conflicts without locking rows."
description: "Pessimistic locking serializes access to data and creates contention. Optimistic concurrency lets transactions proceed freely and detects conflicts only when they actually occur."
pubDate: 2026-06-01
tags: ["Databases", "PostgreSQL"]
draft: false
---

When multiple users or processes can modify the same data concurrently, you need a strategy for handling conflicts. Pessimistic locking (selecting rows `FOR UPDATE`) prevents conflicts by blocking other transactions from touching the row until you're done. Optimistic concurrency takes the opposite approach: allow concurrent access, detect conflicts at write time, and handle them explicitly.

## Why optimistic concurrency

Pessimistic locking is correct but expensive when conflicts are rare. Every reader that touches a locked row must wait, even if most of the time they wouldn't have conflicted with each other. Under high read load, this creates a performance bottleneck.

Optimistic concurrency assumes conflicts are uncommon. Transactions read data freely, make their changes, and only at commit time check whether the data changed since they read it. If it has, the write fails and the application retries or reports a conflict.

## Implementation with a version column

The standard approach uses a version number that increments on every update:

```sql
CREATE TABLE documents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  content     TEXT NOT NULL,
  version     INTEGER NOT NULL DEFAULT 1,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

When updating, include the known version in the WHERE clause:

```sql
-- Client reads the document (version = 5)
SELECT id, title, content, version FROM documents WHERE id = $1;

-- Client makes edits...

-- Client submits update — only succeeds if version is still 5
UPDATE documents
SET
  title = $2,
  content = $3,
  version = version + 1,
  updated_at = NOW()
WHERE id = $1 AND version = 5;

-- Check affected rows: 0 means a conflict occurred
```

If another process updated the document between the read and the write, its version is now 6. The WHERE clause matches nothing, the update affects 0 rows, and you know a conflict happened.

## Application-level implementation

```typescript
class ConflictError extends Error {
  constructor(resourceId: string) {
    super(`Conflict updating resource ${resourceId}`);
    this.name = 'ConflictError';
  }
}

async function updateDocument(
  id: string,
  changes: { title?: string; content?: string },
  knownVersion: number
): Promise<Document> {
  const result = await db.query(`
    UPDATE documents
    SET
      title = COALESCE($3, title),
      content = COALESCE($4, content),
      version = version + 1,
      updated_at = NOW()
    WHERE id = $1 AND version = $2
    RETURNING *
  `, [id, knownVersion, changes.title ?? null, changes.content ?? null]);

  if (result.rowCount === 0) {
    // Either the document doesn't exist or the version has changed
    const exists = await db.query('SELECT id FROM documents WHERE id = $1', [id]);
    if (exists.rowCount === 0) {
      throw new Error(`Document ${id} not found`);
    }
    throw new ConflictError(id);
  }

  return result.rows[0];
}
```

The API includes the version in the response and requires it in update requests:

```typescript
// GET /documents/:id returns:
// { id: "...", title: "...", content: "...", version: 5, updatedAt: "..." }

// PUT /documents/:id requires version in body:
// { title: "New title", version: 5 }

app.put('/documents/:id', async (req, res) => {
  const { title, content, version } = req.body;

  if (typeof version !== 'number') {
    return res.status(400).json({ error: 'version is required' });
  }

  try {
    const updated = await updateDocument(req.params.id, { title, content }, version);
    return res.json(updated);
  } catch (error) {
    if (error instanceof ConflictError) {
      return res.status(409).json({
        error: 'CONFLICT',
        message: 'Document was modified by another request. Fetch the latest version and retry.',
      });
    }
    throw error;
  }
});
```

## ETags as an HTTP-native version mechanism

HTTP has a built-in optimistic concurrency mechanism: ETags.

```typescript
// Return ETag header with the version
app.get('/documents/:id', async (req, res) => {
  const doc = await getDocument(req.params.id);
  res.setHeader('ETag', `"${doc.version}"`);
  res.json(doc);
});

// Require If-Match header on updates
app.put('/documents/:id', async (req, res) => {
  const ifMatch = req.headers['if-match'];
  if (!ifMatch) {
    return res.status(428).json({ error: 'If-Match header required' });
  }

  const version = parseInt(ifMatch.replace(/"/g, ''));

  try {
    const updated = await updateDocument(req.params.id, req.body, version);
    res.setHeader('ETag', `"${updated.version}"`);
    res.json(updated);
  } catch (error) {
    if (error instanceof ConflictError) {
      return res.status(412).json({ error: 'Precondition Failed' }); // ETag mismatch
    }
    throw error;
  }
});
```

## When optimistic concurrency is appropriate

Optimistic concurrency shines when conflicts are rare (users editing different documents, infrequent concurrent updates to shared resources) and the cost of retrying on conflict is low. It falls short when conflicts are common — high-contention scenarios like inventory counters, seat booking systems, or financial ledgers may be better served by pessimistic locking or atomic database operations (`UPDATE inventory SET stock = stock - 1 WHERE id = $1 AND stock > 0`).

The conflict detection cost is paid only when conflicts actually occur, making optimistic concurrency the efficient default for most multi-user applications.

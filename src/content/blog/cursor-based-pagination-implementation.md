---
title: "Cursor-based pagination: the implementation that doesn't break under load."
description: "Offset pagination skips rows, which breaks when data changes between pages. Cursor-based pagination uses a stable position marker that stays correct regardless of concurrent writes."
pubDate: 2026-05-28
tags: ["REST API", "Databases"]
draft: false
---

Offset pagination (`LIMIT 20 OFFSET 40`) is easy to implement and intuitive to use. It breaks in ways that matter when data changes between page requests — items get skipped, items get shown twice — and its performance degrades as the offset grows. Cursor-based pagination avoids both problems.

## The problem with offset pagination

```sql
-- Page 1: fetch items 1-20
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 0;

-- Meanwhile, someone publishes a new post (it would appear at position 1)

-- Page 2: fetch items 21-40
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 20;
-- The new post shifted everything — item 20 from page 1 now appears at position 21
-- It shows up again on page 2
```

At high offsets, the database has to read and discard all prior rows to find the start of the requested page. An `OFFSET 10000 LIMIT 20` query on a large table is slower than `OFFSET 0 LIMIT 20` because the database must scan through 10,000 rows to find the start position.

## Cursor-based pagination

Instead of "skip N rows," cursor pagination says "give me records after this specific record." The cursor encodes a position in the dataset — typically the sort column value (and a tiebreaker) of the last item on the previous page.

```sql
-- Instead of OFFSET, use WHERE to filter by position
SELECT * FROM posts
WHERE created_at < '2026-05-28T10:00:00Z'  -- position of last item
  AND id < 'post_abc'                        -- tiebreaker for same timestamp
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

New posts appearing before the cursor don't affect subsequent pages. The query always starts from a stable anchor.

## Implementation

```typescript
interface Post {
  id: string;
  title: string;
  createdAt: Date;
}

interface PageResult<T> {
  items: T[];
  nextCursor: string | null;
  hasMore: boolean;
}

function encodeCursor(post: Post): string {
  return Buffer.from(
    JSON.stringify({ createdAt: post.createdAt.toISOString(), id: post.id })
  ).toString('base64url');
}

function decodeCursor(cursor: string): { createdAt: string; id: string } {
  return JSON.parse(Buffer.from(cursor, 'base64url').toString('utf-8'));
}

async function getPosts(
  cursor?: string,
  limit: number = 20
): Promise<PageResult<Post>> {
  let whereClause = '';
  let params: unknown[] = [limit + 1]; // fetch one extra to detect hasMore

  if (cursor) {
    const { createdAt, id } = decodeCursor(cursor);
    whereClause = `
      WHERE (created_at, id) < ($2::timestamptz, $3)
    `;
    params = [limit + 1, createdAt, id];
  }

  const rows = await db.query<Post>(`
    SELECT id, title, created_at AS "createdAt"
    FROM posts
    ${whereClause}
    ORDER BY created_at DESC, id DESC
    LIMIT $1
  `, params);

  const hasMore = rows.length > limit;
  const items = hasMore ? rows.slice(0, limit) : rows;
  const lastItem = items[items.length - 1];

  return {
    items,
    hasMore,
    nextCursor: hasMore && lastItem ? encodeCursor(lastItem) : null,
  };
}
```

Fetching `limit + 1` items and checking whether you got them is a clean way to determine if there are more results without a separate `COUNT(*)` query.

## API design

```typescript
// GET /api/posts?cursor=eyJjcmVhdGVkQXQ...&limit=20
app.get('/api/posts', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);
  const cursor = req.query.cursor as string | undefined;

  const result = await getPosts(cursor, limit);

  res.json({
    data: result.items,
    pagination: {
      nextCursor: result.nextCursor,
      hasMore: result.hasMore,
    },
  });
});
```

The cursor is opaque to clients. They store it and pass it back on the next request without parsing it. Encoding it in base64 reinforces this — it looks like a token, not a parseable value.

## Index requirement

Cursor pagination is only fast if the sort columns are indexed together:

```sql
-- Index supporting ORDER BY created_at DESC, id DESC
CREATE INDEX posts_cursor_idx ON posts (created_at DESC, id DESC);
```

Without this index, each page request scans the entire table from the cursor position.

## Bi-directional pagination

Supporting "previous page" requires a `before` cursor in addition to `after`:

```sql
-- For "before" cursor: reverse the sort direction
SELECT * FROM posts
WHERE (created_at, id) > ($1, $2)  -- greater than for reverse direction
ORDER BY created_at ASC, id ASC     -- ascending to get items "before"
LIMIT $3;
-- Then reverse the result set in application code
```

Most APIs only need forward pagination. If you need bidirectional navigation (like a virtualized list), implement both cursors from the start — it's harder to add later once clients are using the single-direction API.

---
title: "Offset pagination breaks at scale. Here's how cursor pagination fixes it."
description: "OFFSET-based pagination is easy to implement but produces inconsistent results as data changes. Cursor pagination is stable, performant, and the right default for most APIs."
pubDate: 2024-06-13
tags: ["REST API", "PostgreSQL"]
draft: false
---

Pagination is one of those features that works fine in development and shows its problems in production. Offset pagination is easy to understand and implement, but it has two issues that become real at scale: performance and consistency. Cursor pagination fixes both.

## How offset pagination works

```sql
SELECT * FROM posts ORDER BY created_at DESC LIMIT 20 OFFSET 40;
```

The client requests page 3 (offset 40, limit 20). Simple.

API endpoint:

```
GET /posts?page=3&limit=20
```

```js
app.get('/posts', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = parseInt(req.query.limit) || 20;
  const offset = (page - 1) * limit;

  const posts = await db.query(
    'SELECT * FROM posts ORDER BY created_at DESC LIMIT $1 OFFSET $2',
    [limit, offset]
  );

  res.json({ data: posts, page, limit });
});
```

## The two problems

**Problem 1: Inconsistent results**

Suppose a user loads page 1 (posts 1-20). While they're reading, someone creates a new post. It goes to the top of the list. The user clicks "next page" to load page 2 (offset 20). The new post shifted everything down — what was post 20 is now post 21. They see post 20 twice. Or if posts are deleted, they skip items entirely.

**Problem 2: Performance**

`OFFSET 10000` doesn't mean "skip 10000 rows cheaply." The database scans and discards those rows. `OFFSET 100000` on a million-row table forces the database to throw away the first 100,000 rows before returning the 20 you want. As pages get higher, queries get slower.

## How cursor pagination works

Instead of "give me page 3," the client says "give me the next 20 items after item X."

"Item X" is the cursor — an opaque pointer to a position in the sorted result set. Typically it's the ID or timestamp of the last item on the previous page.

```sql
SELECT * FROM posts
WHERE created_at < '2024-01-15 10:30:00'
ORDER BY created_at DESC
LIMIT 20;
```

This is efficient: an index on `created_at` makes this fast regardless of how many rows come before it.

## Implementation

```js
app.get('/posts', async (req, res) => {
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const cursor = req.query.cursor; // base64-encoded cursor value

  let query;
  let params;

  if (cursor) {
    const decoded = Buffer.from(cursor, 'base64').toString('utf8');
    const { createdAt, id } = JSON.parse(decoded);

    // Use (created_at, id) pair to handle ties
    query = `
      SELECT * FROM posts
      WHERE (created_at, id) < ($1, $2)
      ORDER BY created_at DESC, id DESC
      LIMIT $3
    `;
    params = [createdAt, id, limit + 1];
  } else {
    query = `
      SELECT * FROM posts
      ORDER BY created_at DESC, id DESC
      LIMIT $1
    `;
    params = [limit + 1];
  }

  const posts = await db.query(query, params);
  const hasMore = posts.length > limit;
  const items = hasMore ? posts.slice(0, limit) : posts;

  const nextCursor = hasMore
    ? Buffer.from(
        JSON.stringify({
          createdAt: items[items.length - 1].created_at,
          id: items[items.length - 1].id,
        })
      ).toString('base64')
    : null;

  res.json({
    data: items,
    nextCursor,
    hasMore,
  });
});
```

Key details:

- Fetch `limit + 1` items. If you get more than `limit`, there's a next page. Slice off the extra item.
- Encode the cursor as base64 so clients treat it as opaque and don't try to parse or construct it.
- Use both `created_at` and `id` in the cursor to handle rows with identical timestamps.
- The `WHERE (created_at, id) < ($1, $2)` syntax is a row comparison — it compares the tuple, which is exactly what you want.

## The client experience

```json
{
  "data": [...],
  "nextCursor": "eyJjcmVhdGVkQXQiOiIyMDI0LTAxLTE1IiwiaWQiOjE0Mn0=",
  "hasMore": true
}
```

To load the next page:

```
GET /posts?cursor=eyJjcmVhdGVkQXQiOiIyMDI0LTAxLTE1IiwiaWQiOjE0Mn0=
```

If `nextCursor` is null, the client has reached the end.

## Trade-offs

Cursor pagination doesn't support jumping to an arbitrary page — you can't load page 47 without loading pages 1 through 46 first. For most use cases (infinite scroll, chronological feeds, API consumers processing data in sequence), this is fine.

If you need arbitrary page jumping (search results, admin tables where users jump to specific pages), offset pagination with a capped maximum page is the pragmatic choice. At those page numbers, the performance issue is smaller than on truly large datasets.

For anything with real volume, cursor-based is the default.

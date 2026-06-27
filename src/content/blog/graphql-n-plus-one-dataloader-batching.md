---
title: "The N+1 problem in GraphQL: DataLoader and the batching fix."
description: "Every GraphQL resolver that fetches related data naively creates N+1 database queries. DataLoader solves this with batching and caching within a request."
pubDate: 2026-05-25
tags: ["GraphQL", "Performance"]
draft: false
---

The N+1 problem is one of the first performance issues you hit with GraphQL. It occurs when resolving a list of N items, and each item triggers an additional query to fetch related data — resulting in 1 query for the list and N queries for the relations, for a total of N+1.

## How the problem occurs

Consider a GraphQL query that fetches posts with their authors:

```graphql
query {
  posts {
    id
    title
    author {
      name
      email
    }
  }
}
```

The naive resolver implementation:

```javascript
const resolvers = {
  Query: {
    posts: () => db.query('SELECT * FROM posts LIMIT 20'),
  },
  Post: {
    // This runs once per post
    author: (post) => db.query(
      'SELECT * FROM users WHERE id = $1', [post.author_id]
    ),
  },
};
```

Fetching 20 posts triggers 1 query for the posts, then 20 separate queries for each author — 21 queries total. At 100 posts it's 101 queries. At 1000 posts, it's 1001.

You can see this in query logs: many nearly-identical `SELECT * FROM users WHERE id = $1` queries running in sequence.

## DataLoader: batch and cache

DataLoader, originally built by Facebook, solves this by batching multiple single-item lookups into one query within a single event loop tick.

```javascript
import DataLoader from 'dataloader';

// The batch function receives an array of keys and returns an array of values
// in the same order
const userLoader = new DataLoader(async (userIds) => {
  const users = await db.query(
    'SELECT * FROM users WHERE id = ANY($1)',
    [userIds]
  );

  // DataLoader requires results in the same order as the input keys
  const userMap = new Map(users.map(u => [u.id, u]));
  return userIds.map(id => userMap.get(id) ?? null);
});
```

Now update the resolver to use the loader:

```javascript
const resolvers = {
  Post: {
    author: (post) => userLoader.load(post.author_id),
  },
};
```

When 20 posts resolve simultaneously (within the same event loop tick), DataLoader collects all 20 `author_id` values and makes a single batched query. The result: 2 queries total instead of 21.

## Request-scoped loaders

DataLoader also caches within a request — calling `userLoader.load('usr_123')` twice returns the same cached result the second time. This is only safe when the loader is scoped to a single request. Sharing a loader across requests would return stale data.

```javascript
// Create loaders per request in your GraphQL context
function createContext(req) {
  return {
    user: req.user,
    loaders: {
      user: new DataLoader(async (ids) => {
        const users = await db.query(
          'SELECT * FROM users WHERE id = ANY($1)', [ids]
        );
        const map = new Map(users.map(u => [u.id, u]));
        return ids.map(id => map.get(id) ?? null);
      }),
      post: new DataLoader(async (ids) => {
        const posts = await db.query(
          'SELECT * FROM posts WHERE id = ANY($1)', [ids]
        );
        const map = new Map(posts.map(p => [p.id, p]));
        return ids.map(id => map.get(id) ?? null);
      }),
    },
  };
}

// In resolvers, access loaders through context
const resolvers = {
  Post: {
    author: (post, _args, context) =>
      context.loaders.user.load(post.author_id),
  },
  Comment: {
    post: (comment, _args, context) =>
      context.loaders.post.load(comment.post_id),
    author: (comment, _args, context) =>
      context.loaders.user.load(comment.author_id),
  },
};
```

## Batching with filters

DataLoader's batch function receives an array of keys. For more complex lookups, use a composite key:

```javascript
// Batch loading posts by author, with a status filter
const postsByAuthorLoader = new DataLoader(
  async (keys) => {
    // keys = [{ authorId: '1', status: 'published' }, ...]
    const authorIds = [...new Set(keys.map(k => k.authorId))];

    const posts = await db.query(`
      SELECT * FROM posts
      WHERE author_id = ANY($1)
      ORDER BY created_at DESC
    `, [authorIds]);

    // Group by author
    const byAuthor = new Map();
    for (const post of posts) {
      if (!byAuthor.has(post.author_id)) byAuthor.set(post.author_id, []);
      byAuthor.get(post.author_id).push(post);
    }

    return keys.map(({ authorId, status }) =>
      (byAuthor.get(authorId) ?? []).filter(p => p.status === status)
    );
  },
  { cacheKeyFn: (key) => `${key.authorId}:${key.status}` }
);
```

## When DataLoader isn't enough

DataLoader batches requests within a single tick. For deeply nested schemas where each level triggers resolution before the next level starts, some N+1 patterns remain. In those cases, alternatives like query planning at the schema level (Graphile's look-ahead, Pothos with query complexity analysis) or moving to a join-based query approach for specific resolvers are worth exploring.

But for the standard case of resolving related records in a list query, DataLoader turns N+1 into 1+1, and that change in query count makes the difference between an endpoint that degrades under load and one that doesn't.

---
title: "GraphQL vs REST: the actual tradeoff, not the hype."
description: "A realistic comparison of GraphQL and REST covering over-fetching, type safety, tooling, caching, and when each approach wins."
pubDate: 2025-11-06
tags: ["REST-API", "GraphQL"]
draft: false
---

GraphQL was introduced as a solution to REST's over-fetching and under-fetching problems. It solved those problems and introduced new ones. The right choice depends on your specific situation, not on which technology is trending.

## The problems GraphQL solves

**Over-fetching**: A REST endpoint for `/users/:id` returns the full user object. The client needed just the name and avatar. The rest was wasted bandwidth.

**Under-fetching**: Displaying a user's profile with their recent posts and follower count requires three API calls: `/users/:id`, `/users/:id/posts`, `/users/:id/followers`. Each is a round trip.

GraphQL addresses both with a single flexible query:

```graphql
query GetUserProfile($id: ID!) {
  user(id: $id) {
    name
    avatarUrl
    posts(limit: 5) {
      title
      publishedAt
    }
    followerCount
  }
}
```

One request, exactly the fields needed, data joined server-side.

## The problems GraphQL introduces

**Caching becomes harder**: REST endpoints map naturally to HTTP caching. `GET /products/123` with `Cache-Control: max-age=3600` caches that resource for an hour. GraphQL queries are POST requests (usually) with a body; HTTP caches ignore POST bodies.

You can cache at the application layer (Redis, persisted queries), but it's more work and more complexity than REST's native HTTP caching.

**Query complexity attacks**: A client can write a deeply nested query that forces the server to join many tables and return megabytes of data:

```graphql
# This could kill your database
{
  users {
    posts {
      comments {
        author {
          posts {
            comments { ... }
          }
        }
      }
    }
  }
}
```

You must implement query depth limiting and complexity analysis. Libraries like `graphql-query-complexity` help, but it's boilerplate REST doesn't need.

**N+1 query problem**: Without care, resolving a list of users with their posts fires one query for users, then N queries for each user's posts. DataLoader solves this through batching and caching, but it's an extra pattern to understand and implement.

```javascript
// Without DataLoader: N+1 queries
const usersResolver = async () => {
  const users = await db.query("SELECT * FROM users");
  return users.map(async user => ({
    ...user,
    posts: await db.query("SELECT * FROM posts WHERE user_id = $1", [user.id])
    // This fires once per user
  }));
};

// With DataLoader: batched into 2 queries total
const postLoader = new DataLoader(async (userIds) => {
  const posts = await db.query(
    "SELECT * FROM posts WHERE user_id = ANY($1)",
    [userIds]
  );
  return userIds.map(id => posts.filter(p => p.userId === id));
});
```

## Type safety: GraphQL's strongest advantage

The GraphQL schema is a contract. Clients know exactly what fields are available and their types. Code generators like `graphql-codegen` turn the schema into TypeScript types automatically:

```typescript
// Generated from schema
type User = {
  id: string;
  name: string;
  email: string;
  posts: Post[];
};

// Query result is fully typed
const { data } = useQuery<GetUserProfileQuery>(GET_USER_PROFILE, {
  variables: { id: userId }
});
// data.user.name is typed as string, no casting
```

REST APIs can achieve similar type safety with OpenAPI/Swagger and code generation, but GraphQL's introspection makes tooling easier -- the schema is queryable from the API itself.

## When REST is the right choice

- **Simple CRUD APIs**: The over-fetching problem is minimal when resources map cleanly to UI components
- **Public APIs**: REST is more widely understood; GraphQL requires clients to understand the query language
- **Heavy caching requirements**: CDN caching of individual resources is straightforward
- **Small teams**: GraphQL schema design, resolver implementation, and tooling setup take time; REST gets you moving faster
- **File uploads**: Multipart form data with REST is standard; GraphQL multipart handling is non-standard and varies by client

## When GraphQL is the right choice

- **Complex, interconnected data**: Multiple resource types that clients always need together
- **Multiple clients with different data needs**: Mobile app needs 3 fields, web app needs 20 -- GraphQL lets each client ask for what it needs
- **Rapid iteration on frontend**: Frontend teams can add fields without backend changes, as long as the data is already in the schema
- **Internal APIs with TypeScript consumers**: Code generation from schema to types eliminates a category of bugs

## A pragmatic middle ground

REST with OpenAPI provides type safety through codegen and works well for most APIs. The API is predictable, cacheable, and familiar to every developer.

Add GraphQL when you have a specific pain point it solves: complex data graphs, multiple client types, or frontends that need flexible data composition.

The worst outcome is choosing GraphQL to be modern and spending three months fighting N+1 queries and caching problems on an app where REST with three endpoints would have worked fine.


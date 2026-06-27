---
title: "URL design: naming conventions that prevent bikeshedding on every PR."
description: "URL structure debates slow down teams. Establishing consistent naming conventions up front eliminates the recurring arguments and makes your API predictable."
pubDate: 2024-06-03
tags: ["REST-API"]
draft: false
---

URL naming is one of the most-argued topics in API design, which is unfortunate because the actual rules are simple and have been stable for years. The debates mostly happen because teams don't write down their conventions early. Here's a set of conventions that's worth adopting and encoding in a linter or review checklist.

## Nouns, not verbs

URLs identify resources. HTTP methods express what you're doing with them. Mixing verbs into URLs creates redundancy and makes the API harder to learn.

```
# Wrong
GET  /getUsers
POST /createUser
POST /deleteUser
GET  /fetchUserById?id=5

# Right
GET    /users
POST   /users
DELETE /users/:id
GET    /users/:id
```

The method already carries the verb. `POST /users` is "create a user." `DELETE /users/:id` is "delete a user." There's no need to repeat it.

## Plural nouns for collections

Use plural nouns consistently. `/users` not `/user`, `/posts` not `/post`.

The reason is consistency: both the collection endpoint and the individual resource endpoint use the same noun:

```
GET /users        â†’ collection
GET /users/:id    â†’ single item from the same collection
```

If you used singular (`/user`), you'd end up with `/user/:id` for the item and `/users` for the collection â€” an inconsistency that forces developers to memorize which form each endpoint uses.

## Lowercase, hyphenated, no underscores

```
# Wrong
/userProfiles
/User_Profiles
/UserProfiles

# Right
/user-profiles
```

URLs are case-sensitive on most servers, but browsers and clients normalize them inconsistently. Sticking to lowercase eliminates case-sensitivity bugs entirely. Use hyphens instead of underscores â€” underscores can be hidden under link underlines and are harder to type correctly.

## Nested resources for relationships

When a resource belongs to another resource, nest it:

```
GET  /users/:userId/posts          â†’ posts by a specific user
POST /users/:userId/posts          â†’ create a post for a user
GET  /users/:userId/posts/:postId  â†’ specific post by a specific user
```

Keep nesting shallow â€” two levels max. Deep nesting creates long, hard-to-read URLs:

```
# Avoid
/users/:userId/teams/:teamId/projects/:projectId/tasks/:taskId/comments
```

At this depth, a flat URL with query parameters is cleaner:

```
GET /comments?taskId=:taskId
```

## Query parameters for filtering, sorting, pagination

Query params belong on collection endpoints where you're modifying which items come back:

```
GET /posts?status=published
GET /posts?authorId=42&sort=createdAt&order=desc
GET /posts?page=2&limit=20
GET /posts?tags=nodejs,express
```

Not as path segments:

```
# Wrong â€” these are not separate resources
GET /posts/published
GET /posts/page/2
GET /posts/sort/createdAt
```

A published post and an unpublished post are the same resource type. The filter is an attribute of the query, not of the resource.

## Actions that don't map to CRUD

Sometimes you need endpoints for operations that don't fit the resource model cleanly. Activating an account, sending an email, archiving a record â€” these are actions.

Options:

**Use a sub-resource that represents the state:**

```
POST /users/:id/activation     â†’ activate user
DELETE /users/:id/activation   â†’ deactivate user
```

**Use a verb as a sub-resource where the action is clearly distinct:**

```
POST /users/:id/password-reset â†’ trigger password reset
POST /orders/:id/cancel        â†’ cancel an order
```

The key is that these should be rare. Most operations fit CRUD if you model the resource correctly. A "cancel" action on an order is really a PATCH that sets `status: 'cancelled'`. The verb endpoint is an alternative when the semantic difference is important or when there's no obvious field to update.

## Versioning in the URL

Include the API version in the base path:

```
/api/v1/users
/api/v2/users
```

This makes it explicit and easy to route at the proxy or gateway level. More on versioning strategies in a later post, but whatever approach you choose, establish it before the first endpoint goes to production.

## Write it down

The biggest source of URL bikeshedding is having no written convention. Put a short API style guide in your README or contributing docs:

- Plural nouns
- Lowercase with hyphens
- Nest max 2 levels
- Query params for filtering/sorting/pagination
- Verb in path only for non-CRUD actions

With that written down, PR comments become "this doesn't follow our convention" with a link, instead of a preference debate. The specific choices matter less than having consistent choices.


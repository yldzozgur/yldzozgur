---
title: "API design review: 10 questions before you call an endpoint done."
description: "A checklist of design decisions that are easy to skip when building an endpoint and painful to change after consumers depend on it."
pubDate: 2026-05-21
tags: ["REST API", "Architecture"]
draft: false
---

API design decisions are hard to reverse. Consumers build against your contracts, and breaking changes require coordination, versioning, and migration paths. Running through a short review before an endpoint ships catches most of the issues that become expensive to fix later.

## 1. Does the URL represent a resource, not an action?

REST URLs identify resources. Actions are expressed through HTTP methods.

```
// Wrong — verbs in URLs
POST /api/createUser
GET  /api/getUserById?id=123
POST /api/deleteUser

// Correct — resources + methods
POST   /api/users
GET    /api/users/123
DELETE /api/users/123
```

Exceptions exist (batch operations, complex searches, non-resource actions) but they should be deliberate, not accidental.

## 2. Are status codes semantically correct?

Status codes are part of the contract. Using them inconsistently makes clients handle errors incorrectly.

```
200 OK              — successful read, update, or delete
201 Created         — resource was created (include Location header)
204 No Content      — successful action with no response body
400 Bad Request     — client sent invalid data (include error details)
401 Unauthorized    — not authenticated
403 Forbidden       — authenticated but not authorized
404 Not Found       — resource doesn't exist
409 Conflict        — state conflict (duplicate, version mismatch)
422 Unprocessable   — valid syntax but failed business validation
429 Too Many Requests — rate limit exceeded
500 Internal Server Error — unexpected server failure
```

Returning `200` with `{"success": false}` in the body forces clients to parse the body to detect errors, defeating the purpose of status codes.

## 3. Is the error response shape consistent?

Every error should look the same, regardless of which endpoint produced it.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      }
    ]
  }
}
```

A consistent shape lets clients write error handling once. Inconsistent shapes mean per-endpoint error handling.

## 4. Are you returning the full resource or just an ID?

After a `POST /users`, returning just `{"id": "usr_123"}` forces the client to make a second request to get the user's data. Returning the full created resource eliminates that round trip.

## 5. Can the endpoint be paginated?

Any endpoint returning a list can grow unbounded. If pagination isn't implemented now, adding it later is a breaking change.

```json
{
  "data": [...],
  "pagination": {
    "nextCursor": "eyJpZCI6IjEyMyJ9",
    "hasMore": true
  }
}
```

Cursor-based pagination (rather than offset) scales better and handles concurrent inserts correctly.

## 6. Does it expose what it shouldn't?

Review the response for fields that shouldn't leave the server:

- Password hashes
- Internal database IDs when you want opaque public IDs
- Server infrastructure details in error messages
- Private user data exposed to other users

## 7. Is authentication and authorization correct for every combination?

Test the matrix:
- Unauthenticated request: should return 401
- Authenticated as wrong user: should return 403
- Authenticated as admin: should succeed
- Authenticated as owner: should succeed
- Authenticated as non-owner: should return 403

Authorization checks are often applied correctly for the primary action but missed for related sub-resources.

## 8. Is input validated before it reaches business logic?

Every field in the request body and URL parameters should have explicit validation:

```typescript
const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(18).max(120),
  role: z.enum(['admin', 'user']),
  tags: z.array(z.string().max(50)).max(10).optional(),
});

const result = schema.safeParse(req.body);
if (!result.success) {
  return res.status(400).json({ error: formatZodError(result.error) });
}
```

Return errors immediately, before hitting the database or calling any external services.

## 9. Are there obvious performance problems?

Before shipping, run `EXPLAIN ANALYZE` on the queries the endpoint executes. Look for:
- Sequential scans on large tables (missing indexes)
- N+1 query patterns (a query in a loop)
- Queries with no limit returning unbounded results

One unindexed query that takes 200ms at 100 rows will take 2 seconds at 10,000 rows.

## 10. Is the endpoint idempotent when it should be?

`GET`, `PUT`, and `DELETE` should be idempotent — calling them multiple times should produce the same result as calling once. For `POST` endpoints, consider whether clients need an idempotency key to safely retry on network failures.

```
// Idempotency key in header
POST /api/payments
Idempotency-Key: a8f9e21b-4c3d-4b1a-8e2f-9d6c7b5a3e1f
```

The server stores the key and returns the same response for duplicate requests, preventing double-charges or duplicate record creation on retried requests.

Running through these ten questions before a PR merges catches the design issues that are straightforward to fix now and expensive to fix after clients have integrated.

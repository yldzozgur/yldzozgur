---
title: "Idempotency: why your PUT endpoint should be safe to call twice."
description: "Idempotency is a property of HTTP methods that makes distributed systems more reliable. Here's what it means, which methods must have it, and how to implement it for POST."
pubDate: 2024-06-17
tags: ["REST-API"]
draft: false
---

Idempotency means that calling an operation multiple times produces the same result as calling it once. In the context of APIs, it means a client can safely retry a request without worrying about duplicate side effects.

This matters because networks are unreliable. A request can fail after the server processes it but before the response reaches the client. Without idempotency, a client retry creates a duplicate â€” two orders, two charges, two records.

## Which HTTP methods are idempotent

The HTTP spec defines idempotency requirements for each method:

| Method | Idempotent | Safe (no side effects) |
|--------|------------|----------------------|
| GET    | Yes        | Yes                  |
| HEAD   | Yes        | Yes                  |
| PUT    | Yes        | No                   |
| DELETE | Yes        | No                   |
| PATCH  | No         | No                   |
| POST   | No         | No                   |

GET and HEAD must never change server state. PUT and DELETE must be idempotent â€” calling them multiple times must produce the same result as calling once. POST has no idempotency guarantee.

## PUT idempotency in practice

PUT replaces a resource entirely with the request body. If you call it twice with the same body, the second call should produce the same result as the first:

```js
// This is idempotent â€” replacing the resource twice has the same end state
app.put('/users/:id', async (req, res, next) => {
  try {
    const user = await db.query(
      `UPDATE users SET name = $1, email = $2 WHERE id = $3 RETURNING *`,
      [req.body.name, req.body.email, req.params.id]
    );

    if (!user.rows.length) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(user.rows[0]);
  } catch (err) {
    next(err);
  }
});
```

Calling this twice with the same body sets `name` and `email` to the same values both times. The database ends up in the same state.

**What breaks PUT idempotency:**

```js
// NOT idempotent â€” each call increments the counter
app.put('/posts/:id', async (req, res, next) => {
  await db.query(
    `UPDATE posts SET title = $1, view_count = view_count + 1 WHERE id = $2`,
    [req.body.title, req.params.id]
  );
});
```

If a client retries this PUT due to a network timeout, the view count increments twice. The fix: don't mix idempotent updates with non-idempotent side effects. Increment view counts on GET or via a separate endpoint.

## DELETE idempotency

Deleting something that doesn't exist should return 404, but a retry on a successful delete should also not produce a new error state. Some teams return 204 on any delete (whether or not the row existed), treating "already deleted" as success:

```js
app.delete('/users/:id', async (req, res, next) => {
  try {
    await db.query('DELETE FROM users WHERE id = $1', [req.params.id]);
    res.status(204).send(); // 204 whether row existed or not
  } catch (err) {
    next(err);
  }
});
```

This is debatable â€” returning 404 when the resource doesn't exist is also valid and more informative. The important thing is that calling DELETE twice doesn't double-delete or corrupt related data.

## Making POST idempotent with idempotency keys

POST isn't idempotent by definition, but you can implement idempotency keys to make it safe to retry:

The client generates a unique key for each intended operation and sends it in a header:

```
POST /orders
Idempotency-Key: 8f14e45f-ceea-4f7b-ab5b-da0b7e3a3a1b
```

The server stores the result the first time it processes this key. On a retry with the same key, it returns the stored result instead of processing again:

```js
app.post('/orders', async (req, res, next) => {
  const idempotencyKey = req.headers['idempotency-key'];

  if (!idempotencyKey) {
    return res.status(400).json({ error: 'Idempotency-Key header required' });
  }

  // Check if we've already processed this key
  const cached = await cache.get(`idempotency:${idempotencyKey}`);
  if (cached) {
    return res.status(cached.status).json(cached.body);
  }

  try {
    const order = await createOrder(req.body);
    const result = { status: 201, body: order };

    // Store result for 24 hours
    await cache.set(`idempotency:${idempotencyKey}`, result, 86400);

    res.status(201).json(order);
  } catch (err) {
    next(err);
  }
});
```

The client can retry on network failure and always get back the same response â€” the original order, not a duplicate.

This is how Stripe handles payment idempotency. The key is stored with a TTL; after expiration, the same key could create a new order, so clients should use keys that are unique per intended action.

## Why it matters

Idempotency makes your API resilient in the face of real network conditions. Clients that implement retry logic (all robust clients should) need to know which requests are safe to retry automatically and which require user confirmation. Following HTTP's defined idempotency semantics gives clients that signal without needing extra documentation.


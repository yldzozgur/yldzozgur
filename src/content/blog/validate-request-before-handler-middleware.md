---
title: "Validate the request before it reaches your handler."
description: "Putting validation logic inside route handlers pollutes business logic and lets bad input reach your database. Here's how to intercept it earlier with middleware."
pubDate: 2024-05-13
tags: ["Express", "Security"]
draft: false
---

The most common place developers write input validation is inside the route handler — right before or mixed in with business logic. It works, but it creates handlers that do two things at once: they validate input and they execute business logic. Separating these into middleware makes both cleaner.

## What happens without middleware validation

Here's a typical handler that validates inline:

```js
app.post('/users', async (req, res) => {
  const { email, password, age } = req.body;

  if (!email || typeof email !== 'string') {
    return res.status(400).json({ error: 'Email is required' });
  }
  if (!password || password.length < 8) {
    return res.status(400).json({ error: 'Password must be at least 8 characters' });
  }
  if (age !== undefined && (typeof age !== 'number' || age < 0)) {
    return res.status(400).json({ error: 'Age must be a positive number' });
  }

  // actual business logic starts here
  const user = await createUser({ email, password, age });
  res.status(201).json(user);
});
```

This works for a single route. Multiply it across twenty endpoints and you have validation scattered everywhere, inconsistently formatted, impossible to test in isolation.

## Validation as middleware

Move the checks into a separate function:

```js
function validateCreateUser(req, res, next) {
  const { email, password, age } = req.body;
  const errors = [];

  if (!email || typeof email !== 'string') {
    errors.push('Email is required');
  }
  if (!password || password.length < 8) {
    errors.push('Password must be at least 8 characters');
  }
  if (age !== undefined && (typeof age !== 'number' || age < 0)) {
    errors.push('Age must be a positive number');
  }

  if (errors.length > 0) {
    return res.status(400).json({ errors });
  }

  next();
}
```

Then compose it with the route:

```js
app.post('/users', validateCreateUser, async (req, res) => {
  const user = await createUser(req.body);
  res.status(201).json(user);
});
```

The handler now does exactly one thing. If `validateCreateUser` finds errors, it sends a 400 and the handler never runs.

## Using a schema validation library

Writing validation by hand is error-prone. Libraries like `zod`, `joi`, and `express-validator` let you define schemas and get structured errors for free.

Here's the same validation with `zod`:

```js
const { z } = require('zod');

const createUserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  age: z.number().positive().optional(),
});

function validateBody(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        errors: result.error.errors.map((e) => ({
          field: e.path.join('.'),
          message: e.message,
        })),
      });
    }
    req.body = result.data; // replace with parsed/coerced data
    next();
  };
}
```

Use it like this:

```js
app.post('/users', validateBody(createUserSchema), async (req, res) => {
  const user = await createUser(req.body);
  res.status(201).json(user);
});
```

The `validateBody` function is reusable — pass it any Zod schema and it returns a middleware function. This pattern works for query params and URL params too:

```js
const getUsersSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().max(100).default(20),
});

function validateQuery(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.query);
    if (!result.success) {
      return res.status(400).json({ errors: result.error.errors });
    }
    req.query = result.data;
    next();
  };
}

app.get('/users', validateQuery(getUsersSchema), getUsers);
```

Notice `z.coerce.number()` — query params arrive as strings. Coercion converts `"20"` to `20` automatically.

## Validating URL parameters

```js
const userParamsSchema = z.object({
  id: z.string().uuid(),
});

app.get(
  '/users/:id',
  validateParams(userParamsSchema),
  async (req, res) => {
    const user = await findUser(req.params.id);
    if (!user) return res.status(404).json({ error: 'Not found' });
    res.json(user);
  }
);
```

If `:id` isn't a valid UUID, validation rejects it before hitting the database — protecting against malformed queries and potential injection.

## Why this matters for security

Validation middleware is your first line of defense against bad input reaching your application logic. Without it:

- Malformed data can trigger unhandled exceptions deep in your code
- Type coercion surprises can cause unexpected behavior in database queries
- Large payloads can exhaust memory if you're not enforcing size limits

Combine schema validation with `express.json({ limit: '10kb' })` at the app level to reject oversized bodies before they're even parsed.

## Consistent error format

One underrated benefit: validation middleware makes error responses consistent. When validation logic lives in handlers, each developer formats errors slightly differently. With a shared `validateBody` helper, every validation error looks the same, which makes frontend error handling straightforward.

The pattern is simple: define a schema, create a middleware factory that validates against it, and compose it with your routes. The handler sees only valid, coerced data.

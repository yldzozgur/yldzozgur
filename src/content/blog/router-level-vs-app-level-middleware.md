---
title: "Router-level vs app-level middleware: picking the wrong one breaks auth."
description: "App-level and router-level middleware behave differently in ways that aren't obvious until auth stops working. Here's what each one does and when to use it."
pubDate: 2024-05-09
tags: ["Express"]
draft: false
---

Express has two scopes for middleware: the application level and the router level. They look almost identical in code, which makes it easy to choose the wrong one — and when auth middleware ends up in the wrong scope, it either runs on every route when it shouldn't, or silently skips protected routes.

## App-level middleware

App-level middleware is attached directly to the `app` instance:

```js
const express = require('express');
const app = express();

app.use(express.json());

app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next();
});
```

It runs for every request that reaches the app. There's no isolation — if you put auth middleware here, it applies globally. If you put CORS headers here, they go on every response.

That's fine for middleware that genuinely needs to run everywhere: body parsing, logging, security headers. But if you try to protect only your `/api` routes with app-level middleware, you end up writing path checks inside the middleware itself:

```js
// Fragile — manual path check inside middleware
app.use((req, res, next) => {
  if (!req.path.startsWith('/api')) return next();
  if (!req.headers.authorization) return res.status(401).json({ error: 'Unauthorized' });
  next();
});
```

This works but it's hard to maintain and easy to break as the app grows.

## Router-level middleware

`express.Router()` creates a mini-app that has its own middleware stack:

```js
const router = express.Router();

router.use((req, res, next) => {
  console.log('This only runs for routes mounted on this router');
  next();
});

router.get('/users', getUsers);
router.post('/users', createUser);
```

Middleware attached with `router.use()` only runs for requests that match routes on that router. It never touches routes registered on a different router or directly on `app`.

You mount the router onto the app:

```js
app.use('/api', router);
```

Now `router.use(...)` middleware runs only for requests to `/api/*`. Everything else is unaffected.

## The auth pattern that breaks

Here's the mistake that causes auth to stop working:

```js
const router = express.Router();

router.get('/users', getUsers);       // registered first
router.use(requireAuth);              // auth registered after routes
router.post('/users', createUser);
```

Order matters in the router stack the same way it does in the app stack. The `GET /users` route is already registered before `requireAuth`, so it never goes through the auth check. The fix is to always put middleware before the routes it should protect:

```js
const router = express.Router();

router.use(requireAuth);              // auth first
router.get('/users', getUsers);
router.post('/users', createUser);
```

## Combining both levels

A real app typically has some middleware at the app level (global) and some at the router level (scoped):

```js
const express = require('express');
const app = express();

// App-level: runs on everything
app.use(express.json());
app.use(require('helmet')());

// Public routes — no auth required
const publicRouter = express.Router();
publicRouter.get('/status', (req, res) => res.json({ ok: true }));
publicRouter.post('/login', loginHandler);
app.use('/', publicRouter);

// Private routes — require auth
const apiRouter = express.Router();
apiRouter.use(requireAuth);           // only applies inside this router
apiRouter.get('/users', getUsers);
apiRouter.delete('/users/:id', deleteUser);
app.use('/api', apiRouter);
```

The `requireAuth` middleware is isolated to `apiRouter`. Requests to `/status` and `/login` never encounter it. Requests to `/api/*` always do.

## Splitting routers across files

The real payoff of router-level middleware is that you can move each router into its own file:

```js
// routes/api.js
const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');

router.use(requireAuth);

router.get('/users', getUsers);
router.post('/users', createUser);

module.exports = router;
```

```js
// app.js
const apiRouter = require('./routes/api');
app.use('/api', apiRouter);
```

The auth logic is co-located with the routes it protects, not scattered across the main app file. When you add new routes to `routes/api.js`, they automatically get auth because the middleware is already registered at the top of that router.

## When to use each

Use app-level middleware for things that should run on every request without exception: JSON parsing, compression, logging, security headers.

Use router-level middleware for things that apply to a subset of routes: authentication, permission checks, input validation that's specific to a resource.

The distinction isn't just organizational. It's the difference between "this must always happen" and "this should only happen here." Getting that boundary right is what keeps auth logic predictable as the codebase grows.

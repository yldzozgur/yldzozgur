---
title: "The middleware chain is everything in Express. Here's how requests move."
description: "Understanding how a request flows through Express middleware is the foundation of every feature you'll build. Here's how the chain actually works."
pubDate: 2024-05-02
tags: ["Express", "Node.js"]
draft: false
---

Every Express application is a pipeline. A request enters at one end, passes through a sequence of functions, and eventually gets a response — or doesn't, if something goes wrong. That pipeline is the middleware chain.

## What middleware is

A middleware function in Express has this signature:

```js
function myMiddleware(req, res, next) {
  // do something
  next(); // pass control to the next middleware
}
```

Three parameters: the request object, the response object, and `next` — a function that hands control to the next middleware in the stack. If you don't call `next()`, the request stops there. If you call `res.send()` or `res.json()`, the response is sent and the chain effectively ends.

## Registering middleware

You attach middleware to your app with `app.use()`:

```js
const express = require('express');
const app = express();

app.use((req, res, next) => {
  console.log(`${req.method} ${req.url}`);
  next();
});

app.get('/hello', (req, res) => {
  res.send('Hello');
});
```

The logger runs on every request because it's registered with `app.use()` without a path. The route handler only runs for `GET /hello`. Order matters: middleware registered first runs first.

## The chain in sequence

When a `GET /hello` request comes in, Express walks through its stack in order:

1. Logger middleware runs, calls `next()`
2. Route handler for `GET /hello` matches, sends response

If you had a second `app.use()` after the route, it would not run — because the route handler sent the response and didn't call `next()`.

```js
app.use(loggerMiddleware);      // 1st
app.use(authMiddleware);        // 2nd
app.get('/hello', handler);     // 3rd — sends response
app.use(neverReachesHere);      // never runs for /hello
```

## Passing data between middleware

The `req` object is shared across the entire chain for a single request. Middleware can attach properties to it:

```js
app.use((req, res, next) => {
  req.requestId = crypto.randomUUID();
  next();
});

app.get('/hello', (req, res) => {
  res.json({ id: req.requestId, message: 'Hello' });
});
```

This is how auth middleware works in practice: parse the token, verify it, attach `req.user`, and every subsequent handler has access to the authenticated user.

## Path-scoped middleware

`app.use()` accepts a path prefix as the first argument:

```js
app.use('/api', apiMiddleware);
```

`apiMiddleware` only runs when the request URL starts with `/api`. Useful for applying auth to all API routes without touching your public routes.

## Multiple handlers on one route

A route handler is just middleware. You can chain multiple handlers on a single route:

```js
app.post(
  '/users',
  validateBody,    // middleware 1
  checkPermission, // middleware 2
  createUser       // final handler
);
```

Each one calls `next()` to pass control forward. If `validateBody` finds invalid input, it can call `next(new Error('Invalid body'))` to jump to your error handler, skipping `checkPermission` and `createUser` entirely.

## Short-circuiting the chain

Any middleware can end the chain early by sending a response:

```js
function requireAuth(req, res, next) {
  if (!req.headers.authorization) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}
```

The `return` before `res.status()` is important. Without it, execution continues in the function body after the response is sent, which can lead to "headers already sent" errors.

## Built-in middleware

Express ships with a few built-in middleware functions:

```js
app.use(express.json());           // parses JSON request bodies
app.use(express.urlencoded({ extended: true })); // parses form data
app.use(express.static('public')); // serves static files
```

These are always registered near the top of the file, before your routes, because routes that read `req.body` depend on the body-parsing middleware having already run.

## The mental model

Think of your Express app as a conveyor belt. Middleware functions are stations on the belt. The request object is the item moving through. Every station either processes it and passes it on, or takes it off the belt by sending a response. Knowing which station runs when — and in what order — is what separates Express code that works from Express code that mysteriously doesn't.

Get the order right, use `next()` consistently, and short-circuit early when you need to reject. Everything else in Express builds on top of this.

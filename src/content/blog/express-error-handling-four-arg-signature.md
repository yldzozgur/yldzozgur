---
title: "Express error handling has one rule everyone gets wrong: the 4-arg signature."
description: "Error handling in Express works differently from regular middleware. One wrong function signature and your errors silently pass through. Here's how it actually works."
pubDate: 2024-05-06
tags: ["Express"]
draft: false
---

Express has a dedicated error-handling layer. It works, but it has one non-obvious requirement that catches almost every developer the first time: the error handler function must accept exactly four arguments.

## How errors propagate

When something goes wrong in a route handler or middleware, you pass the error to `next()`:

```js
app.get('/users/:id', async (req, res, next) => {
  try {
    const user = await db.findUser(req.params.id);
    if (!user) {
      return next(new Error('User not found'));
    }
    res.json(user);
  } catch (err) {
    next(err);
  }
});
```

Calling `next(err)` with any truthy value tells Express to skip all remaining regular middleware and jump straight to the error handler.

## The four-argument rule

An error handler looks exactly like regular middleware — with one difference. It must have four parameters: `err`, `req`, `res`, `next`.

```js
// This works
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: err.message });
});

// This does NOT work as an error handler
app.use((req, res, next) => {
  // Express sees 3 params and treats this as regular middleware
  // Errors skip right past it
});
```

Express identifies error handlers by the function's `.length` property. If it's 4, Express routes errors there. If it's 3, Express treats it as regular middleware and never calls it for errors. This is why you must always include `next` as the fourth parameter even if you never call it.

## Where to place the error handler

Error handlers go at the very end of your middleware stack, after all routes:

```js
const app = express();

app.use(express.json());
app.use('/api', apiRouter);
app.get('/health', healthHandler);

// Error handler — always last
app.use((err, req, res, next) => {
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
  });
});
```

If you put it before your routes, it will never catch errors from those routes.

## Custom error classes

A clean pattern is to define your own error class with a `status` property:

```js
class AppError extends Error {
  constructor(message, status = 500) {
    super(message);
    this.status = status;
    this.name = 'AppError';
  }
}
```

Then throw it anywhere in your app:

```js
app.get('/users/:id', async (req, res, next) => {
  try {
    const user = await db.findUser(req.params.id);
    if (!user) return next(new AppError('User not found', 404));
    res.json(user);
  } catch (err) {
    next(err);
  }
});
```

Your error handler reads `err.status` to set the response code:

```js
app.use((err, req, res, next) => {
  const status = err.status || 500;
  const message = status < 500 ? err.message : 'Internal Server Error';

  res.status(status).json({ error: message });
});
```

The distinction matters: 4xx errors are the client's fault and safe to expose. 5xx errors are your fault and you should log them but not expose internal details.

## Handling async errors

Express 4 does not automatically catch rejected promises. You need to wrap async handlers:

```js
// Without async wrapper — unhandled rejection
app.get('/data', async (req, res) => {
  const data = await somethingThatThrows(); // Express never sees this error
  res.json(data);
});

// With try/catch — error reaches next()
app.get('/data', async (req, res, next) => {
  try {
    const data = await somethingThatThrows();
    res.json(data);
  } catch (err) {
    next(err);
  }
});
```

A common pattern is a wrapper function that does this automatically:

```js
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

app.get('/data', asyncHandler(async (req, res) => {
  const data = await somethingThatThrows();
  res.json(data);
}));
```

Express 5 (currently in release candidate) handles this natively, but most production apps are still on Express 4.

## Multiple error handlers

You can stack error handlers to handle different categories:

```js
// Handle validation errors differently
app.use((err, req, res, next) => {
  if (err.name === 'ValidationError') {
    return res.status(400).json({ error: err.message, fields: err.fields });
  }
  next(err); // pass to the next error handler
});

// Catch-all
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Something went wrong' });
});
```

Calling `next(err)` inside an error handler passes the error to the next error handler in the stack.

## The one thing to remember

If your error handler isn't being called, check the function signature first. Add the `err` parameter and make sure all four arguments are present. That single rule resolves the majority of error-handling bugs in Express.

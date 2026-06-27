---
title: "API error responses: the format that makes frontend error handling not miserable."
description: "Inconsistent error responses force frontend developers to write brittle parsing code. A predictable error format makes client-side error handling straightforward."
pubDate: 2024-06-20
tags: ["REST-API"]
draft: false
---

Error handling in a frontend app is only as easy as the API makes it. When every endpoint returns errors in a different format â€” some with `message`, some with `error`, some with arrays, some with strings â€” the client code becomes a pile of conditional checks. A consistent error format eliminates that.

## What's wrong with ad-hoc errors

Here's what inconsistent error responses look like when accumulated across a real API:

```json
// Endpoint A validation error
{ "message": "Email is required" }

// Endpoint B validation error
{ "error": { "email": "Invalid format" } }

// Endpoint C validation error
{ "errors": ["Email is required", "Password too short"] }

// Endpoint D not found
{ "msg": "Not found" }

// Endpoint E auth error
"Unauthorized"
```

Frontend code that handles all of these is messy. Every new error format requires updating the error-handling logic. Debugging is harder because you can't make assumptions.

## A format that works

A good error response has these properties:
- Same shape on every endpoint
- Machine-readable type for programmatic handling
- Human-readable message for display or logging
- Field-level detail for validation errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" },
      { "field": "password", "message": "Must be at least 8 characters" }
    ]
  }
}
```

For non-validation errors:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "User with ID 42 was not found"
  }
}
```

The top-level `error` key always exists on error responses and never exists on success responses. That's all the client needs to branch on.

## Implementation in Express

Define an error class with a code:

```js
// utils/errors.js
class AppError extends Error {
  constructor(message, code, status = 500, details = null) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

module.exports = { AppError };
```

Create specific error types:

```js
const notFound = (resource, id) =>
  new AppError(`${resource} with ID ${id} was not found`, 'NOT_FOUND', 404);

const unauthorized = () =>
  new AppError('Authentication required', 'UNAUTHORIZED', 401);

const forbidden = () =>
  new AppError('You do not have permission to perform this action', 'FORBIDDEN', 403);

const validationError = (details) =>
  new AppError('Request validation failed', 'VALIDATION_ERROR', 400, details);

module.exports = { notFound, unauthorized, forbidden, validationError };
```

Global error handler that formats them consistently:

```js
// middleware/errorHandler.js
function errorHandler(err, req, res, next) {
  // Known application error
  if (err.code && err.status) {
    return res.status(err.status).json({
      error: {
        code: err.code,
        message: err.message,
        ...(err.details && { details: err.details }),
      },
    });
  }

  // Unknown error â€” log it, don't expose internals
  console.error({
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
    },
  });
}

module.exports = errorHandler;
```

Using it in route handlers:

```js
const { notFound, validationError } = require('../utils/errors');

app.get('/users/:id', async (req, res, next) => {
  try {
    const user = await findUser(req.params.id);
    if (!user) return next(notFound('User', req.params.id));
    res.json(user);
  } catch (err) {
    next(err);
  }
});
```

## Validation errors with field detail

When validation fails, field-level errors let the frontend highlight specific inputs:

```js
// In validation middleware using Zod
function validateBody(schema) {
  return (req, res, next) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      const details = result.error.errors.map((e) => ({
        field: e.path.join('.'),
        message: e.message,
      }));
      return next(validationError(details));
    }
    req.body = result.data;
    next();
  };
}
```

Response:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "email", "message": "Invalid email" },
      { "field": "name", "message": "Required" }
    ]
  }
}
```

The frontend iterates `details` and knows exactly which form field has which message.

## Frontend error handling with a consistent format

```js
async function apiRequest(url, options) {
  const response = await fetch(url, options);

  if (!response.ok) {
    const body = await response.json();
    throw body.error; // { code, message, details? }
  }

  return response.json();
}

// Usage
try {
  await apiRequest('/api/users', { method: 'POST', body: JSON.stringify(data) });
} catch (err) {
  if (err.code === 'VALIDATION_ERROR') {
    setFieldErrors(err.details);
  } else if (err.code === 'UNAUTHORIZED') {
    redirectToLogin();
  } else {
    showGenericError(err.message);
  }
}
```

The `err.code` switch is predictable and exhaustive. No parsing, no guessing, no "what does this endpoint return on failure?"

## Document your error codes

Publish a list of error codes your API can return. Clients shouldn't have to discover them from source code or trial and error. Even a short markdown table in your README is enough:

| Code | Status | Description |
|------|--------|-------------|
| VALIDATION_ERROR | 400 | Request body failed validation |
| UNAUTHORIZED | 401 | Missing or invalid auth token |
| FORBIDDEN | 403 | Authenticated but not permitted |
| NOT_FOUND | 404 | Requested resource does not exist |
| CONFLICT | 409 | Resource already exists |
| INTERNAL_ERROR | 500 | Unexpected server error |

The format itself is simple. The discipline is applying it consistently across every endpoint.


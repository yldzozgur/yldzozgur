---
title: "CORS: the config that works and the one that silently breaks everything."
description: "CORS errors happen in the browser, not the server, which makes them confusing to debug. Here's how CORS actually works and the Express config that gets it right."
pubDate: 2024-05-16
tags: ["Express", "Security"]
draft: false
---

CORS errors are browser errors, not server errors. Your server sends a response; the browser looks at the response headers; if those headers don't permit the requesting origin, the browser blocks the response before JavaScript sees it. The server never knew anything was wrong.

Understanding that distinction is the key to debugging CORS.

## What CORS is protecting against

Browsers enforce a same-origin policy: JavaScript on `https://myapp.com` cannot make requests to `https://api.otherdomain.com` by default. CORS (Cross-Origin Resource Sharing) is the mechanism that lets a server explicitly relax that policy for specific origins.

When your frontend at `https://myapp.com` makes a fetch request to your API at `https://api.myapp.com`, those are different origins. Without CORS headers on the API, the browser blocks the response.

## The `cors` package

Install it:

```bash
npm install cors
```

The simplest config — and the one that causes the most problems:

```js
const cors = require('cors');
app.use(cors()); // allows ALL origins
```

This sets `Access-Control-Allow-Origin: *`. It works for public APIs. It doesn't work for requests that include credentials (cookies, authorization headers), because the browser requires a specific origin, not a wildcard, when credentials are involved.

## Config that works for a real app

```js
const cors = require('cors');

const allowedOrigins = [
  'https://myapp.com',
  'https://www.myapp.com',
];

if (process.env.NODE_ENV === 'development') {
  allowedOrigins.push('http://localhost:3000');
}

app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (mobile apps, curl, Postman)
    if (!origin) return callback(null, true);

    if (allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error(`CORS blocked: ${origin}`));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));
```

Key points:

- `origin` can be a function for dynamic checking
- `credentials: true` is required when sending cookies or `Authorization` headers
- `allowedHeaders` must list every header your frontend sends
- `!origin` check allows server-to-server requests and tooling like Postman

## Preflight requests

For anything other than simple GET/POST requests, browsers send a preflight `OPTIONS` request first to ask the server if the actual request is allowed. You need to handle it.

With the `cors` middleware applied via `app.use()`, preflight is handled automatically. But if you're applying CORS only to specific routes, you need to handle OPTIONS explicitly:

```js
const corsOptions = { origin: 'https://myapp.com', credentials: true };

app.options('/api/*', cors(corsOptions)); // handle preflight for all /api routes
app.use('/api', cors(corsOptions), apiRouter);
```

If you forget the `app.options()` line, preflight requests to `/api/*` get no CORS headers back, and the browser refuses to make the actual request.

## The silent failure

Here's the config that looks correct but silently breaks credentialed requests:

```js
app.use(cors({
  origin: '*',
  credentials: true,
}));
```

The browser will refuse this. The spec explicitly forbids `Access-Control-Allow-Origin: *` when `Access-Control-Allow-Credentials: true` is also set. The browser rejects the response with a CORS error that says exactly this, but it's easy to miss.

The fix is specifying the exact origin:

```js
app.use(cors({
  origin: 'https://myapp.com',
  credentials: true,
}));
```

## Per-route CORS

Sometimes you want CORS on only some routes:

```js
// Public endpoint — any origin
app.get('/public', cors(), publicHandler);

// Private endpoint — specific origin + credentials
app.get('/private', cors({ origin: 'https://myapp.com', credentials: true }), privateHandler);
```

This is useful when you have a public read endpoint alongside a credentialed write endpoint.

## Debugging CORS

When you see a CORS error in the browser console:

1. Open the Network tab and find the blocked request
2. Look at the response headers — is `Access-Control-Allow-Origin` present?
3. If it's missing, the CORS middleware isn't running (check registration order)
4. If it's `*` but you're sending credentials, change it to the specific origin
5. Check `allowedHeaders` — if your request sends a header not in the list, it's blocked

The most reliable debugging step: temporarily add `console.log` inside the `origin` callback function to see what origin value is coming in. It's often not what you expect.

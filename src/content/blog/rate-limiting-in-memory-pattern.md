---
title: "Rate limiting without a third-party service: the pattern that holds up."
description: "You don't need Redis or an external service to rate limit a Node.js API. Here's the in-process pattern that works for single-instance apps and the point where you need to upgrade."
pubDate: 2024-05-23
tags: ["Express", "Node.js"]
draft: false
---

Rate limiting prevents a single client from overwhelming your API with requests. The simplest implementation stores request counts in memory inside your process. For single-instance Node.js apps, this is completely sufficient and requires no external dependencies.

## The basic pattern

The idea is straightforward: keep a map of IP addresses to request counts, increment on each request, and return 429 Too Many Requests if the count exceeds your limit. Reset the count periodically.

```js
const requestCounts = new Map();

function rateLimiter(maxRequests, windowMs) {
  return (req, res, next) => {
    const ip = req.ip;
    const now = Date.now();

    if (!requestCounts.has(ip)) {
      requestCounts.set(ip, { count: 1, resetAt: now + windowMs });
      return next();
    }

    const record = requestCounts.get(ip);

    if (now > record.resetAt) {
      record.count = 1;
      record.resetAt = now + windowMs;
      return next();
    }

    if (record.count >= maxRequests) {
      return res.status(429).json({
        error: 'Too many requests',
        retryAfter: Math.ceil((record.resetAt - now) / 1000),
      });
    }

    record.count += 1;
    next();
  };
}
```

Use it as middleware:

```js
// 100 requests per 15 minutes, applied globally
app.use(rateLimiter(100, 15 * 60 * 1000));

// Stricter limit on auth endpoints
app.post('/login', rateLimiter(5, 60 * 1000), loginHandler);
```

## Using express-rate-limit

The pattern above illustrates the concept, but `express-rate-limit` is the production-ready version of the same idea. It handles edge cases, adds standard headers, and is well-tested:

```bash
npm install express-rate-limit
```

```js
const rateLimit = require('express-rate-limit');

const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  standardHeaders: true,    // adds RateLimit-* headers
  legacyHeaders: false,
  message: {
    error: 'Too many requests, please try again later.',
  },
});

const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  skipSuccessfulRequests: true, // don't count successful logins against the limit
});

app.use(globalLimiter);
app.post('/login', authLimiter, loginHandler);
app.post('/register', authLimiter, registerHandler);
```

The `standardHeaders` option adds `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` headers to responses, which lets clients know how close they are to being limited before it happens.

## Handling the `X-Forwarded-For` header

If your app runs behind a proxy (nginx, a load balancer, or a hosting platform), `req.ip` will be the proxy's IP, not the client's. You need to tell Express to trust the proxy:

```js
app.set('trust proxy', 1); // trust first proxy
```

With this set, Express reads the client IP from `X-Forwarded-For`. Without it, every request appears to come from the same IP, and your rate limiter limits the proxy instead of individual clients.

## Custom key generation

Rate limiting by IP isn't always right. For authenticated endpoints, rate limiting per user ID is more accurate:

```js
const userLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 60,
  keyGenerator: (req) => {
    return req.user?.id || req.ip; // use user ID if authenticated, IP otherwise
  },
});

app.use('/api', requireAuth, userLimiter, apiRouter);
```

## The memory limitation

In-memory rate limiting has one real constraint: it doesn't work across multiple server instances. If you run two Node.js processes or deploy to a platform that scales horizontally, each instance has its own counter. A client can make 100 requests to instance A and 100 requests to instance B for a total of 200.

For single-instance apps — which covers most projects in their early stage — this isn't a problem. For multi-instance deployments, `express-rate-limit` supports pluggable stores:

```js
const RedisStore = require('rate-limit-redis');
const redis = require('ioredis');

const client = new redis(process.env.REDIS_URL);

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  store: new RedisStore({ sendCommand: (...args) => client.call(...args) }),
});
```

The API stays identical. Only the store changes.

## Respond correctly on 429

Include a `Retry-After` header in 429 responses. It tells clients when they can try again:

```js
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  handler: (req, res, next, options) => {
    res.set('Retry-After', Math.ceil(options.windowMs / 1000));
    res.status(429).json({ error: options.message });
  },
});
```

Well-behaved clients respect this header and back off instead of retrying immediately.

## Where to start

Apply a broad global limiter to everything, then add stricter per-endpoint limits to your auth routes and any endpoint that's expensive to compute. The global limit protects against obvious abuse; the per-endpoint limits protect against credential stuffing on login and brute force on other sensitive actions.

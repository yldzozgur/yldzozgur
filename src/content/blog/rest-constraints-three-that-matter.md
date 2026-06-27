---
title: "REST constraints: the 3 that actually change how you write code."
description: "REST has six architectural constraints. Three of them directly shape how you design endpoints and handle state. Here's what they mean in practice."
pubDate: 2024-05-30
tags: ["REST API"]
draft: false
---

REST (Representational State Transfer) is an architectural style defined by a set of constraints. Roy Fielding defined six of them in his 2000 dissertation. Most discussions stop at the surface level — "use nouns in URLs" and "return JSON" — without explaining the constraints that actually change how you design and implement an API.

Three constraints have real, practical consequences for how you write code.

## 1. Stateless

Every request must contain all information necessary to process it. The server stores no session state between requests.

What this means in practice: you can't rely on the server remembering who the user is from one request to the next. Every request must authenticate itself.

**What violates this:**

```
POST /login       → server creates session, stores in memory
GET /profile      → server looks up session to know who's asking
```

If the session lives in server memory and you add a second server instance, the second server has no session. The client is sticky to the first server or breaks.

**What conforms:**

```
POST /auth/token  → server returns a signed JWT
GET /profile      → client sends JWT in every request header
```

The JWT contains the user identity. Any server can verify it without shared state. You can scale horizontally, restart instances, or add servers without affecting active sessions.

This constraint is why JWT and token-based auth exist in their current form. It's not just a pattern choice — it's a consequence of building a stateless API.

**Practical implication:** Never store user context in server-side sessions tied to a specific process. Put it in the token, or look it up from the database on each request using an ID in the token.

## 2. Uniform interface

REST APIs should expose a consistent, predictable interface. Resources are identified in requests (by URL), and clients interact with those resources through a standard set of operations (HTTP methods).

What this means in practice: your URL structure and method usage should be consistent enough that a developer can predict how to use an endpoint they've never seen before.

**What violates this:**

```
GET  /getUsers
POST /createUser
GET  /deleteUser?id=5
POST /user_update
```

Inconsistent naming, using GET for mutations, verbs in URLs — these make every endpoint a new thing to learn.

**What conforms:**

```
GET    /users          → list users
POST   /users          → create user
GET    /users/:id      → get one user
PUT    /users/:id      → replace user
PATCH  /users/:id      → update user fields
DELETE /users/:id      → delete user
```

The resource is `users`. The operation is expressed by the HTTP method. Any developer familiar with REST can guess this structure.

**Practical implication:** Use HTTP methods for what they mean. GET must be safe (no side effects). PUT must be idempotent (same result if called multiple times). POST is not idempotent. These aren't suggestions — clients, proxies, and caching layers rely on these semantics.

## 3. Layered system

A client shouldn't need to know whether it's talking directly to the server or through intermediaries. Load balancers, caches, gateways, and proxies should be invisible to the client.

What this means in practice: your API should behave identically whether a request goes directly to your Node.js process or through nginx, a CDN, an API gateway, or a load balancer.

**What violates this:**

Relying on client IP address stored in `req.socket.remoteAddress` when the app is behind a proxy. The IP will be the proxy's, not the client's. Or using `http://` URLs in responses when the app is behind an HTTPS terminator.

**What conforms:**

Respecting `X-Forwarded-For`, `X-Forwarded-Proto`, and other proxy headers. Setting `app.set('trust proxy', 1)` in Express when behind a proxy. Using relative URLs or protocol-relative URLs in response bodies.

**Practical implication:** Design your app to work behind a reverse proxy from day one. Log `req.ip` with proxy trust enabled. Use environment variables for your base URL rather than hardcoding protocol and host. Your API should be transparent to the infrastructure layer in front of it.

## The three constraints working together

These three constraints reinforce each other. Stateless auth (JWTs) is compatible with a layered system because any server in the cluster can verify the same token. A uniform interface is compatible with caching (the fourth constraint, worth reading about separately) because GET requests are predictable and safe to cache at any layer.

Most API design debates — "should this be POST or PUT?", "where do I store user state?" — resolve cleanly once you understand which constraint applies.

---
title: "API versioning: 3 strategies, 1 that doesn't create maintenance debt."
description: "API versioning is how you change your API without breaking existing clients. Here are three common strategies, their trade-offs, and the one that scales without accumulating maintenance burden."
pubDate: 2024-06-10
tags: ["REST API"]
draft: false
---

Once clients depend on your API, you can't change it without breaking them. Versioning is how you introduce breaking changes while keeping existing clients working. There are three common approaches, each with different trade-offs.

## Strategy 1: URL versioning

The version is part of the URL path:

```
GET /api/v1/users
GET /api/v2/users
```

This is the most common approach. It's visible, explicit, and easy to route at the infrastructure level. A load balancer or API gateway can route `/v1` and `/v2` to different backends without reading the request body or headers.

```js
const v1Router = require('./routes/v1');
const v2Router = require('./routes/v2');

app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);
```

**Advantage:** Easy to implement, easy to understand, easy to test. Clients know exactly which version they're using just by looking at the URL.

**Problem:** It encourages running multiple complete versions in parallel. If you have v1 and v2 of 40 endpoints and only 3 of them actually changed, you're maintaining 40 v2 routes where 37 of them are copies of v1. Teams often handle this by importing v1 handlers from v2 routes, which creates coupling, or by copying them, which creates drift.

## Strategy 2: Header versioning

The version is specified in a request header:

```
GET /api/users
Accept: application/vnd.myapi.v2+json
```

Or a custom header:

```
GET /api/users
API-Version: 2
```

URLs stay clean. The same URL serves all versions, differentiated by the header.

```js
app.get('/api/users', (req, res, next) => {
  const version = req.headers['api-version'] || '1';
  if (version === '2') return getUsersV2(req, res, next);
  return getUsersV1(req, res, next);
});
```

**Advantage:** Clean URLs. You're technically more REST-compliant since the URL identifies the resource, not a version of the resource.

**Problem:** The version is invisible. You can't tell which version a URL uses by looking at it. Debugging is harder. Browser testing is harder. Sharing URLs doesn't share version context. Most developers find this approach harder to work with day-to-day.

## Strategy 3: Additive versioning (the one that doesn't create debt)

Instead of maintaining multiple versions, only add new things. Never remove or rename existing fields. When you need a breaking change, add a new field alongside the old one and deprecate the old one.

```json
// v1 response
{
  "name": "Jane Smith"
}

// After change — both fields present
{
  "name": "Jane Smith",        // deprecated
  "firstName": "Jane",
  "lastName": "Smith"
}
```

You send a `Deprecation` header with existing responses to signal that a field is going away:

```
Deprecation: true
Sunset: Sat, 01 Jan 2025 00:00:00 GMT
Link: <https://docs.example.com/migration>; rel="deprecation"
```

Clients have time to migrate. Once the sunset date passes, you remove the deprecated field.

**Advantage:** One codebase. No parallel versions to maintain. No routing complexity. Every client is always on the "current" version — they're just using different fields.

**Problem:** You can't actually remove things until every client has migrated, which requires tracking usage or trusting clients to self-report. Some breaking changes can't be handled additively (changing authentication mechanisms, restructuring nested resources). And the response payload can grow bloated during the deprecation window.

## How to choose

For internal APIs (where you control every client), additive versioning is the best default. You can coordinate migrations directly, track who's using deprecated fields, and move at your own pace.

For public APIs (where clients are third parties you can't contact), URL versioning is the pragmatic choice. It's what AWS, Stripe, and GitHub use. The maintenance burden is real but manageable if you limit parallel versions to two or three and have a documented sunset policy.

For teams that find themselves adding `/v2` to every endpoint: add versioning per resource, not per API. Only the endpoints that actually changed need a new version.

## Starting with versioning

Even if you think you won't need versioning, add `/api/v1` to your URL structure from the start. It costs nothing and avoids a forced migration later when you inevitably need to make a breaking change. The worst time to add versioning is after clients already depend on non-versioned URLs.

---
title: "HTTP 200 is not always success. The status codes that make a difference."
description: "Using 200 for everything is technically wrong and makes error handling harder for API consumers. Here are the status codes worth using and what each one communicates."
pubDate: 2024-06-06
tags: ["REST-API"]
draft: false
---

Some APIs return 200 for everything â€” successful responses, errors, even "not found" â€” and put the real status in the response body. This forces every client to parse the response body before knowing whether the request succeeded. HTTP already has a mechanism for this: the status code. Use it.

## The codes that matter

You don't need to memorize all 70+ HTTP status codes. A handful covers nearly every case in a typical REST API.

### 2xx â€” Success

**200 OK**
The generic success. Use it for GET, PATCH, and PUT responses that return the updated resource.

**201 Created**
For POST requests that create a new resource. Return it with a `Location` header pointing to the new resource:

```
HTTP/1.1 201 Created
Location: /api/v1/users/42
```

**204 No Content**
For DELETE requests and PUT/PATCH requests when there's nothing meaningful to return. Tells the client "it worked, there's nothing to show you."

Don't return 200 with an empty body when 204 is appropriate. Empty bodies on 200 are ambiguous; 204 is explicit.

### 3xx â€” Redirection

**301 Moved Permanently**
The resource has a new permanent URL. Clients and search engines should update their links. Appropriate when renaming an endpoint.

**304 Not Modified**
The client sent a conditional request (with `If-None-Match` or `If-Modified-Since`) and the resource hasn't changed. Clients can use their cached copy. Relevant if you implement ETags.

### 4xx â€” Client errors

These are the client's fault. Return them when the request is wrong, not when something fails internally.

**400 Bad Request**
The request is malformed or contains invalid data. Use this for validation failures:

```json
HTTP/1.1 400 Bad Request
{
  "errors": [
    { "field": "email", "message": "Invalid email format" },
    { "field": "age", "message": "Must be a positive number" }
  ]
}
```

**401 Unauthorized**
The request lacks valid authentication credentials. Despite the name, this is about authentication, not authorization. The user isn't logged in (or their token is expired/invalid).

**403 Forbidden**
The user is authenticated but not allowed to do this. The difference from 401: the server knows who they are; they just don't have permission.

```
GET /admin/users
â†’ 401 if no auth token present
â†’ 403 if token is valid but user is not an admin
```

**404 Not Found**
The resource doesn't exist. Use this when a specific resource ID is requested and nothing is found. Do not use it for empty collections â€” an empty list is a valid 200 response.

**409 Conflict**
The request conflicts with the current state of the resource. Classic use: creating a resource with a unique field (like email) that already exists.

**422 Unprocessable Entity**
The request is syntactically valid JSON but semantically wrong. Some teams use 400 for both malformed and invalid input; others use 400 for malformed (unparseable JSON) and 422 for invalid (parseable but fails business rules). Either approach is defensible, but pick one and be consistent.

**429 Too Many Requests**
Rate limit exceeded. Include `Retry-After` in the response:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

### 5xx â€” Server errors

These are your fault. Return them when something goes wrong on the server side that isn't caused by the client's request.

**500 Internal Server Error**
The catch-all for unexpected errors. Log the details server-side; return only a generic message to the client.

**503 Service Unavailable**
The server is temporarily unable to handle the request â€” overloaded, or down for maintenance. Include `Retry-After` if you know when it'll be back.

## The 200 trap

```js
// Wrong â€” forces clients to parse body to know if it worked
app.post('/users', async (req, res) => {
  const result = await createUser(req.body);
  res.status(200).json({
    success: result.ok,
    data: result.ok ? result.user : null,
    error: result.ok ? null : result.message,
  });
});

// Right â€” status code carries the result
app.post('/users', async (req, res, next) => {
  try {
    const user = await createUser(req.body);
    res.status(201).json(user);
  } catch (err) {
    next(err);
  }
});
```

With the second pattern, clients can check `response.ok` or the status code directly, and handle success and failure paths without parsing JSON first.

## Let HTTP do the work

Status codes are part of the protocol for a reason. Middleware, proxies, monitoring tools, and client libraries all understand them. A 429 response automatically tells rate-limiting-aware clients to back off. A 301 tells browsers to update their bookmark. A 404 tells search engines to deindex the URL.

Using 200 for everything opts out of all of that infrastructure. The rule is simple: use the most specific code that accurately describes what happened. When in doubt between two options, pick the more specific one.


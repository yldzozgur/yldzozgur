---
title: "Swagger UI without polluting your app: CDN-hosted docs in 10 lines."
description: "Swagger UI can be served from a CDN with a single HTML file and no npm packages. Here's how to wire it to your OpenAPI spec without adding dependencies to your app."
pubDate: 2024-06-27
tags: ["REST-API", "Swagger"]
draft: false
---

Swagger UI provides an interactive browser interface for your OpenAPI spec. The standard approach installs `swagger-ui-express` and mounts it on your Express app, which adds a dependency and serves the UI from the same process as your API. A simpler alternative: serve a single HTML file from a CDN build, with no npm packages required.

## The CDN approach

Swagger maintains an official CDN build of Swagger UI. A single HTML file that references it is all you need:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>API Docs</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link
      rel="stylesheet"
      href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"
    />
  </head>
  <body>
    <div id="swagger-ui"></div>

    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({
        url: '/openapi.yaml',
        dom_id: '#swagger-ui',
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset,
        ],
        layout: 'StandaloneLayout',
        deepLinking: true,
      });
    </script>
  </body>
</html>
```

Save this as `public/docs/index.html`. Your Express app serves it as a static file â€” no extra middleware, no npm package.

## Wiring it in Express

```js
const express = require('express');
const path = require('path');

const app = express();

// Serve your spec file
app.get('/openapi.yaml', (req, res) => {
  res.sendFile(path.join(__dirname, 'openapi.yaml'));
});

// Serve static files including the docs HTML
app.use(express.static(path.join(__dirname, 'public')));
```

With this setup:
- `GET /openapi.yaml` returns your spec
- `GET /docs/` serves the Swagger UI HTML
- The HTML loads the CDN scripts and fetches your spec from `/openapi.yaml`

## Pinning the CDN version

Using `unpkg.com/swagger-ui-dist` without a version number gets the latest release, which can change behavior unexpectedly. Pin it:

```html
<link
  rel="stylesheet"
  href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css"
/>
<script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
```

Check the latest version at [npmjs.com/package/swagger-ui-dist](https://www.npmjs.com/package/swagger-ui-dist).

## Restricting docs to non-production

If you don't want public API docs in production:

```js
if (process.env.NODE_ENV !== 'production') {
  app.get('/openapi.yaml', (req, res) => {
    res.sendFile(path.join(__dirname, 'openapi.yaml'));
  });

  app.use('/docs', express.static(path.join(__dirname, 'public/docs')));
}
```

Or protect it with basic auth:

```js
const basicAuth = require('express-basic-auth');

app.use(
  '/docs',
  basicAuth({
    users: { admin: process.env.DOCS_PASSWORD },
    challenge: true,
  }),
  express.static(path.join(__dirname, 'public/docs'))
);
```

## Using the npm package instead

If you prefer not to depend on a CDN at runtime (for offline environments or strict security policies), install the dist package:

```bash
npm install swagger-ui-dist
```

Serve its files statically:

```js
const swaggerUiDist = require('swagger-ui-dist');

app.use('/docs/assets', express.static(swaggerUiDist.getAbsoluteFSPath()));
```

Update the HTML to reference local paths:

```html
<link rel="stylesheet" href="/docs/assets/swagger-ui.css" />
<script src="/docs/assets/swagger-ui-bundle.js"></script>
```

No CDN dependency, but now the package is in your `node_modules`.

## Swagger UI configuration options

The `SwaggerUIBundle` call accepts configuration:

```js
SwaggerUIBundle({
  url: '/openapi.yaml',
  dom_id: '#swagger-ui',
  deepLinking: true,             // enables URL fragments per operation
  displayRequestDuration: true,  // shows how long each request took
  filter: true,                  // adds a search bar
  tryItOutEnabled: true,         // opens "Try it out" by default
  requestInterceptor: (request) => {
    // Add auth token to every request from the UI
    request.headers['Authorization'] = `Bearer ${getStoredToken()}`;
    return request;
  },
});
```

The `requestInterceptor` is useful for authentication: users log in once, store their token, and the interceptor adds it to every test request without copying it manually.

## The trade-off

The CDN approach has one real downside: the docs depend on CDN availability. If `unpkg.com` is down, the docs UI won't load (though your API still works). For internal tools where reliability matters more than avoiding a dependency, pin and serve the npm package. For public-facing docs or early-stage projects, the CDN build is significantly less setup.

Either way, the spec is the valuable artifact. The UI is just a reader for it.


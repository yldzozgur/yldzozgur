---
title: "Helmet adds 11 security headers in one line. Here's what each does."
description: "Helmet is a collection of Express middleware that sets HTTP security headers. Here's what each header actually does and why you want it enabled."
pubDate: 2024-05-20
tags: ["Security", "Express"]
draft: false
---

Security headers are HTTP response headers that tell browsers how to behave when handling your content. They're not hard to add manually, but Helmet bundles the most important ones into a single package with sensible defaults.

```bash
npm install helmet
```

```js
const helmet = require('helmet');
app.use(helmet());
```

That one line sets 11 headers. Here's what each one does.

## Content-Security-Policy

```
Content-Security-Policy: default-src 'self'; ...
```

CSP tells the browser which sources are allowed to load scripts, styles, images, and other resources. `default-src 'self'` restricts everything to the same origin, blocking inline scripts and resources loaded from external domains. This is the primary defense against cross-site scripting (XSS) attacks.

Helmet's default CSP is strict. Most apps need to customize it to allow their CDN or analytics:

```js
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", 'https://cdn.example.com'],
      imgSrc: ["'self'", 'data:', 'https:'],
    },
  },
}));
```

## Cross-Origin-Embedder-Policy

```
Cross-Origin-Embedder-Policy: require-corp
```

Requires that any resource loaded by your page has opted in to cross-origin embedding. Needed to enable powerful browser features like `SharedArrayBuffer`. Safe to leave on.

## Cross-Origin-Opener-Policy

```
Cross-Origin-Opener-Policy: same-origin
```

Isolates your browsing context from other origins in the same browser process. Prevents pages from accessing your window via `window.opener` after a navigation. Protects against tab-napping attacks.

## Cross-Origin-Resource-Policy

```
Cross-Origin-Resource-Policy: same-origin
```

Prevents other origins from loading your resources (images, scripts) via `<img>` or `<script>` tags. Protects against cross-origin information leaks.

## Origin-Agent-Cluster

```
Origin-Agent-Cluster: ?1
```

Requests that the browser isolate your origin in its own agent cluster, improving memory isolation between origins. A relatively new header with limited browser support, but harmless to send.

## Referrer-Policy

```
Referrer-Policy: no-referrer
```

Controls how much URL information is sent in the `Referer` header when users navigate away from your site. `no-referrer` sends nothing. This prevents leaking sensitive query parameters (like auth tokens in URLs) to third-party sites.

## Strict-Transport-Security

```
Strict-Transport-Security: max-age=15552000; includeSubDomains
```

Tells browsers to only connect to your site over HTTPS for the next 180 days. After the first visit, the browser refuses HTTP connections entirely, preventing SSL stripping attacks. Only effective if you're serving over HTTPS.

## X-Content-Type-Options

```
X-Content-Type-Options: nosniff
```

Prevents browsers from guessing (sniffing) the content type of a response. Without this, a browser might execute a file uploaded as an image if it looks like JavaScript. With `nosniff`, it uses the declared `Content-Type` header only.

## X-DNS-Prefetch-Control

```
X-DNS-Prefetch-Control: off
```

Disables DNS prefetching — the browser's behavior of pre-resolving domain names it finds in your HTML. Prefetching can leak information about which external domains your page links to.

## X-Download-Options

```
X-Download-Options: noopen
```

Specific to Internet Explorer. Prevents IE from opening downloaded files directly in the browser, which could allow an HTML file to execute in your site's security context. Largely irrelevant today but harmless.

## X-Frame-Options

```
X-Frame-Options: SAMEORIGIN
```

Prevents your page from being embedded in a `<frame>` or `<iframe>` on another origin. This blocks clickjacking attacks, where an attacker overlays your UI with a transparent iframe to trick users into clicking things. `SAMEORIGIN` allows your own pages to embed each other while blocking external embedding.

Note: CSP's `frame-ancestors` directive replaces this header in modern browsers, but `X-Frame-Options` remains useful for older browsers.

## Turning off specific headers

If a header conflicts with your setup, you can disable it:

```js
app.use(helmet({
  contentSecurityPolicy: false,     // manage CSP manually
  xFrameOptions: false,             // handled by CSP frame-ancestors instead
}));
```

## What Helmet doesn't do

Helmet only sets response headers. It doesn't:

- Sanitize input
- Validate request bodies
- Handle authentication
- Protect against SQL injection

Headers communicate security policies to browsers. They can't stop attacks that originate server-side. Use Helmet alongside input validation, parameterized queries, and proper auth — not instead of them.

The one-line install is the easy part. Understanding what you've enabled is what lets you tune it correctly when a header breaks something in production.

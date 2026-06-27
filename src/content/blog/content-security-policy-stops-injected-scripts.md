---
title: "Content Security Policy: the header that stops injected scripts cold."
description: "How Content Security Policy works, how to write a CSP header, and how to deploy it without breaking your application."
pubDate: 2025-11-17
tags: ["Security"]
draft: false
---

Cross-site scripting (XSS) is one of the most common web vulnerabilities. An attacker injects a script into your page and it runs with full access to the DOM, cookies, and user data. Content Security Policy (CSP) is a browser mechanism that limits what scripts can run on your page, even if an attacker manages to inject one.

## How CSP works

You send a `Content-Security-Policy` HTTP header that tells the browser which sources of content are trusted. The browser enforces these rules; it refuses to load or execute anything that doesn't match.

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example.com
```

This policy says: only load content from the same origin (`'self'`), but scripts can also come from `cdn.example.com`. A script injected from any other source will be blocked.

## The directives

CSP has directives for each type of content:

| Directive | Controls |
|-----------|---------|
| `default-src` | Fallback for unspecified directives |
| `script-src` | JavaScript |
| `style-src` | CSS |
| `img-src` | Images |
| `font-src` | Fonts |
| `connect-src` | fetch, XHR, WebSocket |
| `media-src` | Audio and video |
| `frame-src` | iframes |
| `object-src` | `<object>`, `<embed>` |

Source values:
- `'self'`: Same origin only
- `'none'`: Block everything
- `https://example.com`: Specific origin
- `https://*.example.com`: Wildcard subdomain
- `'unsafe-inline'`: Allow inline scripts/styles (defeats much of the protection)
- `'unsafe-eval'`: Allow `eval()`, `new Function()` (avoid if possible)
- `'nonce-{random}'`: Allow specific inline scripts with a matching nonce

## A practical starting policy

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://api.example.com;
  object-src 'none';
  frame-ancestors 'none';
```

`object-src 'none'` blocks Flash and other plugins. `frame-ancestors 'none'` prevents your site from being embedded in iframes (equivalent to `X-Frame-Options: DENY`).

`style-src 'unsafe-inline'` is unfortunately common because many UI libraries apply inline styles. CSS injection attacks are less severe than script injection, so this is usually acceptable.

## Nonces: allowing inline scripts without 'unsafe-inline'

If you need inline scripts (common in server-rendered apps), use nonces instead of `'unsafe-inline'`:

```javascript
// Server: generate a random nonce per request
import crypto from "crypto";

function generateNonce() {
  return crypto.randomBytes(16).toString("base64");
}

app.get("*", (req, res, next) => {
  res.locals.nonce = generateNonce();
  res.setHeader(
    "Content-Security-Policy",
    `script-src 'self' 'nonce-${res.locals.nonce}'`
  );
  next();
});
```

```html
<!-- In your HTML template -->
<script nonce="<%= nonce %>">
  // This inline script is allowed because the nonce matches
  window.__CONFIG__ = { userId: 123 };
</script>
```

An injected script cannot know the nonce (it's generated fresh per request), so it cannot include it. Only scripts rendered by your server with the correct nonce are allowed.

In Next.js:

```javascript
// middleware.ts
import { NextResponse } from "next/server";
import crypto from "crypto";

export function middleware(request: Request) {
  const nonce = crypto.randomBytes(16).toString("base64");
  const response = NextResponse.next();

  response.headers.set(
    "Content-Security-Policy",
    `default-src 'self'; script-src 'self' 'nonce-${nonce}'; style-src 'self' 'nonce-${nonce}'`
  );
  response.headers.set("x-nonce", nonce); // pass to layout

  return response;
}
```

## Report-Only mode: deploy without breaking anything

Deploying a strict CSP to production immediately will break things. Use report-only mode first:

```
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self'; report-uri /csp-violations
```

`Report-Only` enforces nothing -- violations are reported but not blocked. Your application keeps working, and you get a stream of violation reports showing what your CSP would block.

Set up an endpoint to collect reports:

```javascript
app.post("/csp-violations", express.json({ type: "application/csp-report" }), (req, res) => {
  console.log("CSP violation:", JSON.stringify(req.body));
  res.sendStatus(204);
});
```

Run in report-only mode for a week, fix the violations (add needed sources, apply nonces), then switch to enforcement mode.

## Common mistakes

**`'unsafe-inline'` on script-src**: Negates most of CSP's protection against XSS. If you have this, your CSP is theater against script injection.

**Overly permissive sources**: `script-src https:` allows scripts from any HTTPS site. If an attacker can inject a `<script src="https://evil.com/bad.js">` tag, this policy allows it.

**Missing `default-src`**: If you specify `script-src` without `default-src`, other resource types are unconstrained.

**Not handling report-uri**: If you specify `report-uri` without an endpoint that accepts POST requests, you'll get 404s in your logs.

CSP is one layer of defense. It doesn't replace input validation, output encoding, or other XSS prevention techniques. It's a last line of defense that limits the damage when an injection vulnerability exists.

---
title: "CSRF is not just a checkbox. Here's the attack and why tokens stop it."
description: "Walk through a real CSRF attack against a cookie-based session, then understand exactly why the synchronizer token pattern defeats it at the HTTP level."
pubDate: 2024-07-22
tags: ["Security"]
draft: false
---

CSRF protection gets added to forms because frameworks require it, but most developers couldn't explain the actual attack. That matters because misunderstanding the threat leads to misapplying the fix — using CSRF tokens on endpoints that don't need them, or skipping them on endpoints that do.

## The attack, concretely

The victim is logged into `bank.com`. Their session is maintained with a cookie:

```
Cookie: session=abc123
```

The attacker hosts a malicious page at `evil.com`:

```html
<!-- evil.com/steal.html -->
<html>
<body onload="document.forms[0].submit()">
  <form method="POST" action="https://bank.com/transfer">
    <input type="hidden" name="to" value="attacker-account">
    <input type="hidden" name="amount" value="5000">
  </form>
</body>
</html>
```

When the victim visits `evil.com/steal.html`, the page automatically submits a form to `bank.com/transfer`. The browser includes the victim's `bank.com` session cookie because **the browser attaches cookies based on the destination domain, not the origin domain**. The server receives a valid, authenticated request — it has no way to know it was initiated by `evil.com`.

This is CSRF: Cross-Site Request Forgery. The request is forged on behalf of the legitimate user without their knowledge.

## Why it works

The fundamental property being exploited: cookies are attached automatically by the browser to every request to the cookie's domain, regardless of which page initiated the request. The server can't tell a request that originated from its own page apart from one that originated from an attacker's page.

This does **not** apply to:
- Custom headers (e.g., `Authorization: Bearer ...`) — browsers don't automatically add these cross-origin
- JSON bodies sent via `fetch` with `Content-Type: application/json` — these require CORS preflight and won't be sent cross-origin without server permission

CSRF is only a risk when using cookie-based sessions. Applications that use JWT tokens in the `Authorization` header are not vulnerable to CSRF (though they may be vulnerable to XSS instead).

## The synchronizer token pattern

The fix: include a secret token in every state-changing form that the server generated and stored in the user's session. The attacker can't read this token from another origin due to the Same-Origin Policy.

**Server generates and stores the token:**

```js
app.use((req, res, next) => {
  if (!req.session.csrfToken) {
    req.session.csrfToken = crypto.randomBytes(32).toString("hex");
  }
  res.locals.csrfToken = req.session.csrfToken;
  next();
});
```

**Include it in every form:**

```html
<form method="POST" action="/transfer">
  <input type="hidden" name="_csrf" value="<%= csrfToken %>">
  <!-- other fields -->
</form>
```

**Validate it on every state-changing request:**

```js
function validateCsrf(req, res, next) {
  const methods = ["POST", "PUT", "PATCH", "DELETE"];
  if (!methods.includes(req.method)) {
    return next(); // GET/HEAD/OPTIONS are safe methods
  }

  const token = req.body._csrf || req.headers["x-csrf-token"];
  const sessionToken = req.session.csrfToken;

  if (!token || !sessionToken || token !== sessionToken) {
    return res.status(403).json({ error: "Invalid CSRF token" });
  }

  next();
}
```

The attacker's form on `evil.com` cannot include the victim's CSRF token because:
1. JavaScript on `evil.com` can't read cookies from `bank.com`
2. JavaScript on `evil.com` can't read the HTML of `bank.com` pages (Same-Origin Policy)
3. The attacker doesn't know the token value, so can't include it in the forged form

## The double-submit cookie pattern

An alternative that doesn't require server-side session storage: set a CSRF token as a cookie, and require the same value as a custom header or form field.

```js
// Set CSRF cookie on page load
app.use((req, res, next) => {
  if (!req.cookies.csrf) {
    const token = crypto.randomBytes(32).toString("hex");
    res.cookie("csrf", token, {
      secure: true,
      // NOT httpOnly — JavaScript needs to read this
      sameSite: "strict",
    });
  }
  next();
});

// Client-side: read cookie and send as header
const csrfToken = document.cookie
  .split("; ")
  .find((c) => c.startsWith("csrf="))
  ?.split("=")[1];

fetch("/api/transfer", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrfToken,
  },
  body: JSON.stringify({ to: "...", amount: 100 }),
});
```

The attacker can't read the cookie value from another origin, so can't set the matching header.

## SameSite cookies: the modern default

Modern browsers support the `SameSite` cookie attribute:

```js
res.cookie("session", token, {
  httpOnly: true,
  secure: true,
  sameSite: "strict", // or "lax"
});
```

- `strict`: cookie is never sent on cross-site requests (including navigation links)
- `lax`: cookie is sent on top-level navigation (clicking a link) but not on subresource requests from cross-site pages

`SameSite: lax` is now the browser default for cookies without an explicit setting, which neutralizes most CSRF attacks in modern browsers. However, you shouldn't rely solely on browser defaults — explicit CSRF tokens remain the defense-in-depth best practice for any application handling sensitive mutations.

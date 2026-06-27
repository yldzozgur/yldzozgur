---
title: "A JWT is three base64 strings. Here's what's actually inside yours."
description: "Decode a real JWT and understand what each of the three parts contains, why they're base64url encoded, and what you can and cannot trust."
pubDate: 2024-07-01
tags: ["Security"]
draft: false
---

A JSON Web Token looks like random noise — three chunks of characters separated by dots. But it's completely readable. Every JWT you've ever issued can be decoded in seconds at jwt.io or with a one-liner in Node. Understanding what's inside changes how you think about authentication.

## The structure

A JWT has exactly three parts separated by `.`:

```
header.payload.signature
```

Each part is base64url encoded — that's base64 with `+` replaced by `-`, `/` replaced by `_`, and padding stripped. It is **not** encryption. Anyone who has the token can decode the first two parts without any key.

```js
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMyIsInJvbGUiOiJhZG1pbiIsImlhdCI6MTcxOTg0MDAwMCwiZXhwIjoxNzE5ODQzNjAwfQ.abc123";

const [header, payload, sig] = token.split(".");
console.log(JSON.parse(Buffer.from(header, "base64url").toString()));
console.log(JSON.parse(Buffer.from(payload, "base64url").toString()));
```

## Part 1: the header

The header declares the token type and the signing algorithm:

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

`alg` is the most important field here. Common values are `HS256` (HMAC-SHA256, symmetric), `RS256` (RSA, asymmetric), and `ES256` (ECDSA, asymmetric). The algorithm determines what kind of key verifies the signature.

There was a famous vulnerability where servers accepted `"alg": "none"`, meaning no signature required. Any compliant JWT library today rejects this by default, but it's why you should never pass `algorithms: []` to your verification function.

## Part 2: the payload

This is where your actual data lives:

```json
{
  "sub": "user_123",
  "role": "admin",
  "iat": 1719840000,
  "exp": 1719843600
}
```

The fields here are called **claims**. Some are registered (standardized):

- `sub` — subject, typically the user ID
- `iat` — issued at, Unix timestamp
- `exp` — expiration, Unix timestamp
- `iss` — issuer, identifies who created the token
- `aud` — audience, identifies who should consume the token
- `jti` — JWT ID, a unique identifier for this specific token

Everything else is a custom claim. You can put anything here — user roles, tenant ID, feature flags — but keep the payload small because it travels in every request header.

**Critical point**: the payload is visible to anyone who holds the token. Do not put passwords, secrets, PII beyond what's necessary, or anything you wouldn't want a user to see. The only thing protecting the payload's integrity is the signature.

## Part 3: the signature

The signature is computed as:

```
HMACSHA256(
  base64url(header) + "." + base64url(payload),
  secret
)
```

For RS256 it's a private-key signature instead of a shared secret, but the principle is the same: the signature proves that a specific party produced this exact header and payload.

When your server verifies a JWT, it:
1. Splits the token into three parts
2. Recomputes the signature over the header and payload
3. Compares it to the provided signature
4. Checks that `exp` is in the future

If any bit of the header or payload was modified, the signature comparison fails. This is why you can trust the claims — not because they're secret, but because they can't be tampered with without breaking the signature.

```js
import jwt from "jsonwebtoken";

// Verify and decode in one call
const decoded = jwt.verify(token, process.env.JWT_SECRET, {
  algorithms: ["HS256"], // always specify this
});
console.log(decoded.sub); // "user_123"
```

## What to actually check on verification

The library handles signature verification, but make sure you're also enforcing:

- `exp` — reject expired tokens
- `iss` — if you have multiple token issuers, check this
- `aud` — if a token was issued for a different service, reject it

```js
const decoded = jwt.verify(token, process.env.JWT_SECRET, {
  algorithms: ["HS256"],
  issuer: "https://yourapp.com",
  audience: "api",
});
```

## The one thing most people miss

Because JWTs are stateless, you cannot invalidate a specific token before it expires. If a user logs out or you revoke access, the token is still valid until `exp`. This is why JWT expiry should be short (15 minutes to 1 hour) and paired with a refresh token mechanism. The token is a signed, readable, self-contained credential — treat it accordingly.

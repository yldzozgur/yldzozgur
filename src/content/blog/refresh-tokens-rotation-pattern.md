---
title: "Refresh tokens: the rotation pattern that lets you kick stolen sessions."
description: "Refresh token rotation solves the core problem with stateless JWTs: you can detect and invalidate stolen tokens without a server-side session store."
pubDate: 2024-07-08
tags: ["Security"]
draft: false
---

Short-lived access tokens solve the "can't invalidate a JWT" problem — but only partially. If your access token expires in 15 minutes, a user has to log in again every 15 minutes, which is unusable. Refresh tokens bridge this gap, and the rotation pattern makes them detectable when stolen.

## The basic model

The system uses two tokens:

- **Access token**: short-lived JWT (15 minutes), stateless, sent on every API request
- **Refresh token**: long-lived, opaque, stored in the database, sent only to the `/refresh` endpoint

When the access token expires, the client sends the refresh token to get a new access token without requiring the user to log in again. The user stays authenticated for days or weeks while the access token window stays narrow.

```
POST /auth/login
→ { accessToken: "eyJ...", refreshToken: "8f3a..." }

// 15 minutes later, access token expires
POST /auth/refresh
Authorization: Bearer 8f3a...
→ { accessToken: "eyJ..." }  // new access token
```

## The rotation pattern

Basic refresh tokens have a problem: if one is stolen, the attacker can keep refreshing indefinitely. Rotation solves this.

**Rule**: every time a refresh token is used, it is invalidated and a new one is issued.

```js
async function refreshTokens(incomingRefreshToken) {
  const stored = await db.refreshTokens.findOne({
    token: incomingRefreshToken,
    revoked: false,
  });

  if (!stored) {
    throw new Error("Invalid or revoked refresh token");
  }

  if (stored.expiresAt < new Date()) {
    throw new Error("Refresh token expired");
  }

  // Invalidate the used token
  await db.refreshTokens.updateOne(
    { token: incomingRefreshToken },
    { $set: { revoked: true } }
  );

  // Issue new tokens
  const newRefreshToken = crypto.randomBytes(40).toString("hex");
  await db.refreshTokens.insertOne({
    token: newRefreshToken,
    userId: stored.userId,
    family: stored.family, // important — explained below
    expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    revoked: false,
  });

  const newAccessToken = jwt.sign(
    { sub: stored.userId },
    process.env.JWT_SECRET,
    { expiresIn: "15m" }
  );

  return { accessToken: newAccessToken, refreshToken: newRefreshToken };
}
```

## Token families: detecting theft

Rotation alone isn't enough. Consider this scenario:

1. Attacker steals refresh token `A`
2. Legitimate user uses `A`, gets `B`
3. Attacker uses `A` — it's revoked, so they get an error
4. Attacker is blocked... for now

But what if the attacker uses `A` before the legitimate user does? The attacker gets `B`, and when the legitimate user later tries `A`, they get an error. From the user's perspective, they just got logged out mysteriously. From the attacker's perspective, they have a valid session.

**Token families** address this. Every refresh token belongs to a family (the initial login creates family ID). When a revoked token is used:

```js
async function refreshTokens(incomingRefreshToken) {
  const stored = await db.refreshTokens.findOne({
    token: incomingRefreshToken,
  });

  if (!stored) {
    throw new Error("Token not found");
  }

  if (stored.revoked) {
    // Someone used a revoked token — this means the family is compromised
    // Revoke ALL tokens in this family, forcing re-login
    await db.refreshTokens.updateMany(
      { family: stored.family },
      { $set: { revoked: true } }
    );
    throw new Error("Token reuse detected — session terminated");
  }

  // ... proceed with rotation
}
```

When a revoked token is presented, you assume the family is compromised and invalidate all tokens in it. Both the attacker and the legitimate user are logged out. The legitimate user re-authenticates and gets a new family. The attacker is blocked.

## Storage: where to put the refresh token

On web clients, the two standard options are:

**HttpOnly cookie** (recommended):
```js
res.cookie("refreshToken", newRefreshToken, {
  httpOnly: true,   // not accessible to JavaScript
  secure: true,     // HTTPS only
  sameSite: "strict", // CSRF protection
  maxAge: 30 * 24 * 60 * 60 * 1000,
});
```

HttpOnly cookies are invisible to JavaScript, which protects against XSS. The tradeoff is you need to handle CSRF for the `/refresh` endpoint (though `sameSite: strict` largely covers this for modern browsers).

**localStorage**: accessible to any JavaScript on the page. If there's an XSS vulnerability anywhere on your domain, the refresh token is exposed. Generally avoid for refresh tokens.

## Database schema

A minimal refresh tokens table:

```sql
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token TEXT NOT NULL UNIQUE,
  user_id UUID NOT NULL REFERENCES users(id),
  family UUID NOT NULL,
  revoked BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX ON refresh_tokens (token);
CREATE INDEX ON refresh_tokens (family);
```

Index on `token` for the lookup on every refresh. Index on `family` for the revocation sweep.

## The complete flow

```
Login      → create family, store refresh token, return both tokens
API call   → send access token in Authorization header
Token exp  → POST /refresh with refresh token (cookie or body)
           → rotate: revoke old, issue new refresh token + new access token
Logout     → revoke current refresh token (and optionally the whole family)
Stolen     → attacker uses refresh token → rotation detects reuse → family revoked
```

This gives you stateless, short-lived access tokens for performance, with server-side revocation capability for security.

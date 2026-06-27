---
title: "Google sign-in with OAuth 2.0: what happens in those 6 redirects."
description: "Step through the complete OAuth 2.0 authorization code flow that powers Google sign-in, explaining each redirect and what's being exchanged at each step."
pubDate: 2024-07-18
tags: ["Security"]
draft: false
---

"Sign in with Google" feels like magic — click a button, confirm on Google, come back logged in. Under the hood it's a specific sequence of HTTP redirects defined by the OAuth 2.0 Authorization Code flow. Understanding the sequence tells you what can go wrong, why certain security parameters exist, and how to implement it correctly.

## Why the redirect dance?

The core problem OAuth solves: your app wants to access a user's Google data (or just verify their identity) without the user giving you their Google password. The redirects ensure that Google handles credential verification, and your app only receives an authorization code — not credentials.

## The six steps

### Step 1: Your app redirects the user to Google

The user clicks "Sign in with Google." Your app redirects them to Google's authorization endpoint:

```
https://accounts.google.com/o/oauth2/v2/auth?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=https://yourapp.com/auth/callback&
  response_type=code&
  scope=openid%20email%20profile&
  state=abc123xyz&
  code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
  code_challenge_method=S256
```

Key parameters:
- `client_id`: your app's registered identifier with Google
- `redirect_uri`: where Google sends the user after authorization (must be pre-registered)
- `response_type=code`: requesting the authorization code flow
- `scope`: what permissions you're requesting
- `state`: a random value you generated, used to prevent CSRF (more on this shortly)
- `code_challenge`: part of PKCE (Proof Key for Code Exchange), a security extension

### Step 2: Google shows the consent screen

The user is now on Google's servers. They see "App X wants to access your email and profile." Your app is not involved here at all. This is the key security property: credential verification happens entirely at Google.

### Step 3: User consents, Google redirects back

After the user approves, Google redirects to your `redirect_uri` with:

```
https://yourapp.com/auth/callback?
  code=4/0AX4XfWj...&
  state=abc123xyz
```

The `code` is a short-lived authorization code (typically expires in 10 minutes, single-use). The `state` is echoed back so you can verify it.

### Step 4: Your server validates the state parameter

Before doing anything with the `code`, verify that the returned `state` matches what you generated in step 1:

```js
app.get("/auth/callback", async (req, res) => {
  const { code, state } = req.query;

  // Retrieve the state you stored in the user's session
  const expectedState = req.session.oauthState;
  if (!state || state !== expectedState) {
    return res.status(400).send("State mismatch — possible CSRF attack");
  }

  // Clear it so it can't be reused
  delete req.session.oauthState;

  // Proceed to step 5...
});
```

The state parameter prevents an attacker from tricking a user into completing an OAuth flow initiated by someone else.

### Step 5: Your server exchanges the code for tokens

This exchange happens server-to-server, not in the browser. Your server makes a POST request to Google's token endpoint:

```js
const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    code,
    client_id: process.env.GOOGLE_CLIENT_ID,
    client_secret: process.env.GOOGLE_CLIENT_SECRET,
    redirect_uri: "https://yourapp.com/auth/callback",
    grant_type: "authorization_code",
    code_verifier: req.session.codeVerifier, // PKCE verifier
  }),
});

const { access_token, id_token, refresh_token } = await tokenResponse.json();
```

Google verifies:
- The `code` is valid and unexpired
- The `client_secret` matches your registered app
- The `code_verifier` corresponds to the `code_challenge` from step 1 (PKCE)

In return you get:
- `access_token`: used to call Google APIs on behalf of the user
- `id_token`: a JWT containing the user's identity information
- `refresh_token`: (if you requested `access_type=offline`) for future token refreshes

### Step 6: Extract the user's identity from the ID token

The `id_token` is a JWT. Verify it and extract the user's information:

```js
import { OAuth2Client } from "google-auth-library";

const client = new OAuth2Client(process.env.GOOGLE_CLIENT_ID);

async function verifyIdToken(idToken) {
  const ticket = await client.verifyIdToken({
    idToken,
    audience: process.env.GOOGLE_CLIENT_ID,
  });
  const payload = ticket.getPayload();
  return {
    googleId: payload.sub,
    email: payload.email,
    name: payload.name,
    picture: payload.picture,
    emailVerified: payload.email_verified,
  };
}

const googleUser = await verifyIdToken(id_token);

// Find or create user in your database
let user = await db.users.findOne({ googleId: googleUser.googleId });
if (!user) {
  user = await db.users.create({
    googleId: googleUser.googleId,
    email: googleUser.email,
    name: googleUser.name,
  });
}

// Issue your own session/JWT for this user
const sessionToken = jwt.sign({ sub: user._id }, process.env.JWT_SECRET, {
  expiresIn: "15m",
});
```

## What PKCE adds

PKCE (Proof Key for Code Exchange) protects against authorization code interception. Before step 1, generate a random `code_verifier` and hash it to create the `code_challenge`. Store the verifier in the session. In step 5, send the verifier. Google checks that the verifier hashes to the challenge it received in step 1. An attacker who intercepts the authorization code cannot exchange it without the verifier.

```js
// Before step 1
const codeVerifier = crypto.randomBytes(32).toString("base64url");
const codeChallenge = crypto
  .createHash("sha256")
  .update(codeVerifier)
  .digest("base64url");

req.session.codeVerifier = codeVerifier;
req.session.oauthState = crypto.randomBytes(16).toString("hex");
```

For public clients (mobile apps, SPAs), PKCE is required. For confidential clients (server-side apps with a client secret), it's still recommended.

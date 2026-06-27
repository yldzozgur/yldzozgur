---
title: "Signing a token is not encrypting it. The difference matters."
description: "Signing proves integrity and authenticity. Encryption provides confidentiality. Confusing the two leads to real security vulnerabilities in authentication systems."
pubDate: 2024-07-04
tags: ["Security"]
draft: false
---

These two operations are often conflated, and the confusion shows up in production systems. A developer puts a user's email address in a JWT payload assuming it's "encrypted" because the token looks like random characters. It isn't. Understanding the difference between signing and encrypting is not academic — it changes what you put in tokens, how you store keys, and what threats your system is actually protected against.

## What signing does

A digital signature answers the question: **did a specific party produce this exact data, and has it been modified since?**

When you sign data:
1. You compute a hash of the data
2. You apply a key to that hash to produce the signature
3. The original data is sent alongside the signature, completely unmodified

The data is **readable by anyone**. The signature only proves it came from someone with the key and hasn't been altered. With HMAC-SHA256 (symmetric signing used in HS256 JWTs):

```js
import { createHmac } from "crypto";

const data = JSON.stringify({ userId: "123", role: "admin" });
const secret = process.env.JWT_SECRET;

const signature = createHmac("sha256", secret)
  .update(data)
  .digest("base64url");

// data is still plaintext — anyone can read it
// signature just proves you created it and it wasn't modified
console.log(data); // {"userId":"123","role":"admin"}
```

With asymmetric signing (RS256), the private key signs and the public key verifies. This lets you publish your public key so any service can verify your tokens without being able to issue new ones.

## What encryption does

Encryption answers the question: **can only authorized parties read this data?**

When you encrypt data, the output (ciphertext) is unreadable without the corresponding key. The original data is not present in the output — it's mathematically transformed.

```js
import { createCipheriv, randomBytes } from "crypto";

const key = randomBytes(32); // AES-256 key
const iv = randomBytes(16);
const cipher = createCipheriv("aes-256-gcm", key, iv);

const plaintext = '{"userId":"123","role":"admin"}';
const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);

// encrypted is unreadable without key + iv
// plaintext is gone — not encoded, transformed
```

Encryption provides **confidentiality**. Signing provides **integrity and authenticity**. They solve different problems.

## Why the confusion matters

### Scenario 1: PII in JWT payloads

A developer issues a JWT with this payload:

```json
{
  "sub": "user_123",
  "email": "alice@example.com",
  "ssn": "123-45-6789"
}
```

They think it's safe because "the token is cryptographically protected." But anyone who receives this token — the browser, a logging system, any intermediary — can decode the payload with:

```js
JSON.parse(Buffer.from(payload, "base64url").toString());
// {"sub":"user_123","email":"alice@example.com","ssn":"123-45-6789"}
```

The signing protected the integrity of the data, not its confidentiality. Sensitive data should never be in a JWT payload unless you're using JWE (JSON Web Encryption), which is a different, rarer standard.

### Scenario 2: trusting the algorithm field

Early JWT libraries let the token's own header specify the algorithm, including `"alg": "none"`. An attacker could:
1. Take a valid JWT
2. Change the payload to elevate their privileges
3. Set `alg` to `"none"` and remove the signature
4. Submit the modified token

If the server respected `alg: none`, it skipped signature verification entirely. The server was treating "no signature" as equivalent to "valid signature." This is a direct consequence of misunderstanding what signing guarantees — the server must verify the signature, not just check if one exists.

### Scenario 3: key reuse across environments

Because signing and encryption keys serve different purposes, they should never be shared. A key used to sign JWTs should not also be used to encrypt data at rest. If the JWT signing key is ever exposed, an attacker can forge tokens. If it's also your encryption key, the blast radius doubles.

## JWE: when you actually need confidentiality in a token

The JWT spec includes JWE (JSON Web Encryption) for when you genuinely need the payload to be unreadable. The structure has five parts instead of three:

```
header.encrypted_key.iv.ciphertext.auth_tag
```

JWE is significantly more complex to implement and has higher computational cost. Most applications don't need it — they should just keep sensitive data off the token entirely.

## The practical rule

For a standard JWT (JWS — JSON Web Signature):

- Put only what you'd be comfortable logging: user ID, roles, expiry
- Do not put: email, payment info, health data, anything sensitive
- Verify the signature algorithmically and explicitly name the allowed algorithms
- Treat the token as a signed, public-readable bearer credential

The token proves identity and grants access. It is not a secure envelope for sensitive data.

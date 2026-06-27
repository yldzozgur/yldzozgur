---
title: "bcrypt's cost factor: what changing that number actually does."
description: "The cost factor in bcrypt is not arbitrary — it controls exactly how long hashing takes and why that slowness is the entire point of the algorithm."
pubDate: 2024-07-11
tags: ["Security"]
draft: false
---

When you call `bcrypt.hash(password, 12)`, that `12` is not a salt length or an iteration count in any straightforward sense. It's a work factor, and understanding what it does explains why bcrypt has remained a solid password hashing choice for decades while faster algorithms like SHA-256 are completely wrong for passwords.

## The core idea: intentional slowness

SHA-256 hashes a string in microseconds. That's fine for checksums and signatures. It's catastrophic for passwords.

If a database of hashed passwords is stolen, an attacker can try billions of password guesses per second with commodity hardware. A GPU cluster can test ~100 billion SHA-256 hashes per second. A typical user's password will fall in minutes.

bcrypt's answer: make each hash take a measurable amount of time on purpose. With a cost factor of 12, hashing takes roughly 250ms on modern server hardware. That same GPU cluster now tests ~4,000 bcrypt(12) hashes per second instead of 100 billion. An 8-character password that falls in seconds with SHA-256 takes years with bcrypt.

## What the cost factor actually controls

The cost factor `n` means bcrypt runs its key derivation loop **2^n times**.

- Cost 10: 2^10 = 1,024 iterations
- Cost 11: 2^11 = 2,048 iterations
- Cost 12: 2^12 = 4,096 iterations
- Cost 13: 2^13 = 8,192 iterations

Each increment doubles the work. This is the key property: as hardware gets faster, you increment the cost factor by 1 and restore the same time cost.

```js
import bcrypt from "bcrypt";
import { performance } from "perf_hooks";

async function benchmark(cost) {
  const start = performance.now();
  await bcrypt.hash("test-password", cost);
  return performance.now() - start;
}

// Approximate results on a modern server
// cost 10: ~65ms
// cost 11: ~130ms
// cost 12: ~260ms
// cost 13: ~520ms
// cost 14: ~1040ms
```

## What's stored in the hash string

bcrypt stores everything needed to verify a password in a single string:

```
$2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW
 ^   ^  ^                    ^
 |   |  |                    hash (31 chars)
 |   |  salt (22 chars, random per hash)
 |   cost factor
 version
```

The salt is generated automatically and stored alongside the hash. This means:
- Two hashes of the same password look completely different
- Rainbow tables are useless — you'd need a separate table per salt
- You never store or manage the salt separately

```js
const hash1 = await bcrypt.hash("samepassword", 12);
const hash2 = await bcrypt.hash("samepassword", 12);

console.log(hash1 === hash2); // false — different random salts
console.log(await bcrypt.compare("samepassword", hash1)); // true
console.log(await bcrypt.compare("samepassword", hash2)); // true
```

## Choosing the right cost factor

The standard guidance is to choose the highest cost factor that keeps hashing under ~250-300ms on your production hardware for an individual login request. You can benchmark on your actual server:

```js
async function findOptimalCost(targetMs = 250) {
  let cost = 10;
  while (true) {
    const start = Date.now();
    await bcrypt.hash("benchmark-password", cost);
    const elapsed = Date.now() - start;
    console.log(`Cost ${cost}: ${elapsed}ms`);
    if (elapsed >= targetMs) return cost;
    cost++;
  }
}
```

For most applications in 2024, cost 12 is appropriate. If your server handles thousands of login requests per second, you may need to balance security against server load — but most apps don't have that problem.

**Never go below 10.** Below that, the protection is marginal and you're giving up the main benefit of bcrypt.

## Rehashing on login for cost upgrades

When you increase the cost factor, existing hashes stay at the old cost. You can transparently upgrade them on login, since login is the only time you have the plaintext password:

```js
async function loginUser(email, plaintextPassword) {
  const user = await db.users.findOne({ email });
  if (!user) throw new Error("Invalid credentials");

  const isValid = await bcrypt.compare(plaintextPassword, user.passwordHash);
  if (!isValid) throw new Error("Invalid credentials");

  // Rehash if stored at an old cost factor
  const currentCost = parseInt(user.passwordHash.split("$")[2]);
  const targetCost = 12;
  if (currentCost < targetCost) {
    const newHash = await bcrypt.hash(plaintextPassword, targetCost);
    await db.users.updateOne({ _id: user._id }, { $set: { passwordHash: newHash } });
  }

  return user;
}
```

Over time, all active users get upgraded. Inactive users keep the old hash until they log in.

## What bcrypt doesn't protect against

bcrypt has one notable limitation: it truncates passwords at 72 bytes. A 72-character password and a 73-character password that's identical for the first 72 characters will produce the same hash. In practice, this rarely matters — passwords that long are unusual — but if you need to support arbitrarily long passphrases, you can pre-hash with SHA-256 before bcrypt (though this has its own tradeoffs).

For most applications, bcrypt with cost 12 remains a solid choice. Argon2id is the modern recommendation for new systems, but bcrypt's track record and library support make it a defensible default.

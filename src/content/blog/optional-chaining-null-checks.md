---
title: "Optional chaining saved me from 40 null checks. Here's how."
description: "Optional chaining (?.) is not just shorter code. It changes how you navigate uncertain data structures."
pubDate: 2024-01-11
tags: ["JavaScript"]
draft: false
---

Before optional chaining, accessing a deeply nested property meant a chain of `&&` checks or a try/catch wrapped around property access. Neither is pleasant. Optional chaining (`?.`) solves this cleanly, and once you understand how it works you will use it constantly.

## The old way

Imagine an API response with optional fields:

```js
const user = {
  profile: {
    address: {
      city: "Austin"
    }
  }
};
```

But `profile` might be `null`. And `address` might not exist. And `city` might be undefined. Old code looked like this:

```js
const city = user && user.profile && user.profile.address && user.profile.address.city;
```

Or the more defensive version:

```js
let city;
try {
  city = user.profile.address.city;
} catch (e) {
  city = undefined;
}
```

Both are noise. The intent is simple: get `city` if it exists, otherwise get `undefined`. The code should say that.

## Optional chaining

```js
const city = user?.profile?.address?.city;
```

If any step in the chain is `null` or `undefined`, the whole expression short-circuits to `undefined` instead of throwing a TypeError. If every step exists, you get the value.

This is not just shorter. It communicates that you expect some parts of the path to be absent, and you are handling that expectation inline.

## How it works

`?.` checks whether the value to its left is `null` or `undefined`. If it is, the chain stops and returns `undefined`. If not, it continues with the next access.

Crucially, it only guards against `null` and `undefined`. It does not guard against other falsy values. If `user.profile` is `0` or `""`, the chain continues:

```js
const obj = { a: 0 };
obj?.a?.toString(); // "0" — 0 is not null/undefined, so .toString() runs
```

## With method calls

Optional chaining works with method calls too:

```js
const result = user.getAddress?.();
```

This calls `getAddress()` if it exists on `user`, and returns `undefined` if it does not. This is useful when working with objects that might or might not implement certain methods.

```js
// Safe event listener cleanup
element.removeEventListener?.("click", handler);
```

## With bracket notation

```js
const key = "city";
const city = user?.profile?.address?.[key];
```

Same behavior, just using dynamic key access instead of dot notation.

## With arrays

```js
const firstTag = post?.tags?.[0];
```

If `post` is null, or `tags` is null/undefined, you get `undefined`. If `tags` is an empty array, you get `undefined` because index 0 doesn't exist.

## Combining with nullish coalescing

Optional chaining pairs naturally with `??` (nullish coalescing) to provide defaults:

```js
const city = user?.profile?.address?.city ?? "Unknown";
```

`??` returns the right-hand side when the left-hand side is `null` or `undefined`. Combined with `?.`, you get a clean pattern: navigate an uncertain structure, and fall back to a default if anything was absent.

Compare this to using `||`:

```js
const city = user?.profile?.address?.city || "Unknown";
```

`||` returns the right side for any falsy value, including `0`, `""`, and `false`. If your city could legitimately be an empty string and you want to preserve it, `||` would incorrectly replace it. `??` is the safer choice.

## A real example

Suppose you get a response from an API and want to extract several optional fields:

```js
function extractUserInfo(apiResponse) {
  return {
    name: apiResponse?.user?.name ?? "Anonymous",
    email: apiResponse?.user?.contact?.email ?? null,
    city: apiResponse?.user?.profile?.address?.city ?? null,
    avatarUrl: apiResponse?.user?.profile?.avatar?.url ?? "/default-avatar.png",
    isPremium: apiResponse?.user?.subscription?.tier === "premium",
  };
}
```

Without optional chaining this is either 5 sets of `&&` chains or a lot of try/catch blocks. With it, the code is self-documenting: every `?.` tells you that field might not exist.

## When not to use it

Optional chaining can hide bugs. If you expect a property to always exist and it turns out it sometimes does not, a TypeError would alert you to the missing data. If you have `?.` everywhere, the missing data silently becomes `undefined` and surfaces as a bug somewhere else.

Use `?.` when absence is a valid state of the data. When a property should always be there, access it directly so missing data fails loudly.

The 40-null-check example was a real codebase pattern: an API response with 8 levels of optional nesting, accessed in a dozen places. Replacing each `&&` chain with `?.` reduced a 200-line file by about 60 lines and made the intent of every access obvious.

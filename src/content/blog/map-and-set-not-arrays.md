---
title: "Map and Set exist for a reason. Here's when arrays are the wrong choice."
description: "Arrays are the default collection in JavaScript, but Map and Set are more correct for specific use cases. Here's when and why."
pubDate: 2024-01-22
tags: ["JavaScript"]
draft: false
---

Most JavaScript code reaches for arrays and plain objects by default. For many problems that is fine. But `Map` and `Set` exist because arrays and objects are genuinely wrong for some use cases, not just inefficient.

## Set: when duplicates should not exist

An array does not prevent duplicates:

```js
const seen = [];
seen.push("alice");
seen.push("alice"); // no error, now you have two "alice"
```

A `Set` enforces uniqueness by design:

```js
const seen = new Set();
seen.add("alice");
seen.add("alice");
seen.size; // 1 — only one "alice"
```

The most common use case is deduplication:

```js
const ids = [1, 2, 2, 3, 3, 3, 4];
const uniqueIds = [...new Set(ids)]; // [1, 2, 3, 4]
```

Checking membership in a Set is O(1). Checking if an array includes a value is O(n). For large collections, this matters:

```js
// O(n) for each check
const processedIds = [];
if (!processedIds.includes(id)) {
  processedIds.push(id);
}

// O(1) for each check
const processedIds = new Set();
if (!processedIds.has(id)) {
  processedIds.add(id);
}
```

Set operations:

```js
const a = new Set([1, 2, 3]);
const b = new Set([2, 3, 4]);

// Union
const union = new Set([...a, ...b]); // {1, 2, 3, 4}

// Intersection
const intersection = new Set([...a].filter(x => b.has(x))); // {2, 3}

// Difference
const difference = new Set([...a].filter(x => !b.has(x))); // {1}
```

## Map: when object keys are not strings

A plain object works well when keys are strings. When keys are not strings, or when the key set is dynamic, Map is the right tool.

**Any value as a key:**

```js
const userScores = new Map();

const user1 = { id: 1 };
const user2 = { id: 2 };

userScores.set(user1, 42);
userScores.set(user2, 87);

userScores.get(user1); // 42
```

Plain objects coerce keys to strings. `obj[user1]` would store with key `"[object Object]"`, overwriting any other object key. Map uses identity comparison for objects.

**Predictable iteration order:**

Map iterates in insertion order, always. Plain objects iterate in insertion order for string keys (with some edge cases for integer-like strings). Map is explicit and reliable.

```js
const map = new Map([
  ["c", 3],
  ["a", 1],
  ["b", 2],
]);

for (const [key, value] of map) {
  console.log(key, value);
}
// c 3
// a 1
// b 2 — insertion order, guaranteed
```

**Size is built in:**

```js
const map = new Map();
map.set("a", 1);
map.size; // 1

// With objects, you need Object.keys(obj).length
```

**No prototype pollution:**

Plain objects inherit from `Object.prototype`. Keys like `constructor`, `toString`, or `hasOwnProperty` can cause issues:

```js
const obj = {};
obj["constructor"] = "something";
// Now obj.constructor doesn't return the Object constructor

const map = new Map();
map.set("constructor", "something");
// Perfectly fine — no prototype involved
```

## When to use Map vs plain object

Use a plain object when:
- Keys are known strings that map to specific typed values (a config object, a record)
- You need JSON serialization (Map doesn't serialize with JSON.stringify)
- You need to spread or use object rest

Use Map when:
- Keys are not strings
- You need to track which items you have seen (using objects as keys)
- The key set is dynamic and you need frequent insertion/deletion/lookup
- You need to know the count of entries without `Object.keys`

## WeakMap and WeakSet

For completeness: `WeakMap` and `WeakSet` hold weak references. If an object used as a key in a `WeakMap` has no other references, it can be garbage collected. The entry disappears automatically.

```js
const cache = new WeakMap();

function process(domNode) {
  if (cache.has(domNode)) {
    return cache.get(domNode);
  }
  const result = expensiveCompute(domNode);
  cache.set(domNode, result);
  return result;
}
```

When `domNode` is removed from the DOM and has no other references, the WeakMap entry is automatically freed. With a regular Map, you would have a memory leak because the Map holds a strong reference.

WeakSet works similarly for tracking object identity without preventing garbage collection.

## Real example: counting word frequency

```js
// Object version — works but has edge cases with keys like "constructor"
function wordFrequency(text) {
  const freq = Object.create(null); // Null prototype avoids edge cases
  for (const word of text.split(/\s+/)) {
    freq[word] = (freq[word] ?? 0) + 1;
  }
  return freq;
}

// Map version — explicit, no edge cases
function wordFrequency(text) {
  const freq = new Map();
  for (const word of text.split(/\s+/)) {
    freq.set(word, (freq.get(word) ?? 0) + 1);
  }
  return freq;
}
```

Both work. The Map version is explicit about what it is: a mapping from words to counts, with no prototype chain involved.

Use the right tool. Arrays for ordered sequences where position matters. Set for unique values. Map for key-value pairs where the keys are dynamic or not strings.

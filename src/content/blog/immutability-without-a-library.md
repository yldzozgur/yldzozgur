---
title: "Immutability in JavaScript without a library."
description: "You don't need Immutable.js or Immer for most immutability needs. Native JavaScript gives you the tools."
pubDate: 2024-02-01
tags: ["JavaScript"]
draft: false
---

Immutability is a useful property: if data cannot be changed after creation, a whole class of bugs disappears. Shared mutable state is the source of many hard-to-trace bugs. Immutable data does not have this problem.

The good news is that you do not need Immutable.js or Immer for most real-world code. Vanilla JavaScript has enough tools to enforce the patterns that matter.

## Why immutability matters

```js
function processCart(cart) {
  cart.items.push({ id: 99, name: "surprise" }); // mutates the caller's cart
  return cart.total;
}

const myCart = { items: [], total: 0 };
processCart(myCart);
// myCart.items now has an unexpected item — caller didn't expect this
```

Functions that mutate their inputs create invisible side effects. The caller passes in data and gets back a modified version without knowing it. Immutability prevents this by requiring you to return new data instead of modifying existing data.

## Object.freeze

`Object.freeze` prevents modification of an object's properties:

```js
const config = Object.freeze({
  apiUrl: "https://api.example.com",
  timeout: 5000,
});

config.timeout = 10000; // silently fails in non-strict mode, throws in strict mode
config.timeout; // still 5000
```

Frozen objects reject property additions, deletions, and modifications. In strict mode (including ES modules and classes), attempts throw a `TypeError`.

The limitation: `Object.freeze` is shallow.

```js
const state = Object.freeze({
  user: { name: "Alice" }, // this nested object is NOT frozen
});

state.user.name = "Bob"; // succeeds
state.user.name; // "Bob"
```

For deep freezing, you need to recurse:

```js
function deepFreeze(obj) {
  Object.getOwnPropertyNames(obj).forEach(name => {
    const value = obj[name];
    if (value && typeof value === "object") {
      deepFreeze(value);
    }
  });
  return Object.freeze(obj);
}
```

Deep freeze is useful for constants and configuration objects. It is not appropriate for application state you need to update.

## Immutable update patterns

The real use of immutability is in state updates: instead of mutating, you create new objects.

**Objects:**

```js
const user = { name: "Alice", age: 30, role: "viewer" };

// Mutable (avoid)
user.role = "admin";

// Immutable
const updatedUser = { ...user, role: "admin" };
// user is unchanged
// updatedUser = { name: "Alice", age: 30, role: "admin" }
```

**Arrays — adding:**

```js
const items = [1, 2, 3];

// Mutable
items.push(4);

// Immutable
const newItems = [...items, 4];
```

**Arrays — removing:**

```js
const items = [1, 2, 3, 4, 5];

// Remove by index
const withoutThird = [...items.slice(0, 2), ...items.slice(3)];
// or
const withoutThird = items.filter((_, i) => i !== 2);

// Remove by value
const withoutThree = items.filter(x => x !== 3);
```

**Arrays — updating by index:**

```js
const items = [10, 20, 30];

// Update index 1 to 99
const updated = items.map((item, i) => i === 1 ? 99 : item);
// [10, 99, 30]
```

**Nested objects:**

```js
const state = {
  user: { name: "Alice", address: { city: "Austin", zip: "78701" } },
  settings: { theme: "dark" },
};

// Update nested city
const newState = {
  ...state,
  user: {
    ...state.user,
    address: {
      ...state.user.address,
      city: "Houston",
    },
  },
};
```

Nested updates get verbose with deep structures. This is where Immer helps by letting you write mutating code that produces immutable updates. But for most real-world state that is 2-3 levels deep, the spread approach is manageable.

## `const` does not mean immutable

This is a common misconception:

```js
const user = { name: "Alice" };
user.name = "Bob"; // works fine
user = {}; // TypeError — can't reassign the binding
```

`const` prevents reassignment of the variable binding. It does not prevent mutation of the value. An object declared with `const` can still have its properties changed.

True immutability requires `Object.freeze` or immutable update patterns.

## Immutable arrays without mutating methods

Some array methods mutate:
- `push`, `pop`, `shift`, `unshift`
- `sort`, `reverse`
- `splice`

Their immutable alternatives:

```js
// Instead of push
const next = [...arr, item];

// Instead of pop
const next = arr.slice(0, -1);
const removed = arr[arr.length - 1];

// Instead of sort (sort mutates in place)
const sorted = [...arr].sort((a, b) => a - b);

// Instead of reverse
const reversed = [...arr].reverse(); // still mutates the copy, but not the original
// Safer:
const reversed = arr.slice().reverse();
```

## structuredClone

For deep copies without a library:

```js
const original = { a: 1, b: { c: [1, 2, 3] } };
const clone = structuredClone(original);

clone.b.c.push(4);
original.b.c; // [1, 2, 3] — unaffected
```

`structuredClone` is available in Node 17+ and all modern browsers. It handles circular references and most built-in types. It does not clone functions or class instances with methods.

Immutability is a discipline, not a requirement. But once you apply it consistently to state updates, the class of bugs caused by shared mutable state disappears.

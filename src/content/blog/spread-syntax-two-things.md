---
title: "Spread syntax does two different things depending on where you put it."
description: "The ... syntax is used in two fundamentally different ways in JavaScript. Knowing the difference makes destructuring and function signatures clearer."
pubDate: 2024-01-29
tags: ["JavaScript"]
draft: false
---

The `...` syntax in JavaScript is called spread in some contexts and rest in others. They use the same punctuation but do opposite things. Understanding both is essential because the same three dots can mean "spread this out" or "collect these together."

## Spread: expanding an iterable

When `...` appears before an iterable in a position that expects multiple values, it spreads (expands) the iterable into individual elements.

**In array literals:**

```js
const a = [1, 2, 3];
const b = [4, 5, 6];

const combined = [...a, ...b]; // [1, 2, 3, 4, 5, 6]
const withExtra = [0, ...a, 4]; // [0, 1, 2, 3, 4]
```

**In function calls:**

```js
const numbers = [1, 2, 3];
Math.max(...numbers); // same as Math.max(1, 2, 3) → 3

function greet(first, last) {
  return `Hello, ${first} ${last}`;
}
const parts = ["Alice", "Smith"];
greet(...parts); // "Hello, Alice Smith"
```

**In object literals (ES2018):**

```js
const defaults = { color: "blue", size: "medium", weight: 1 };
const custom = { size: "large", weight: 2 };

const merged = { ...defaults, ...custom };
// { color: "blue", size: "large", weight: 2 }
// custom properties overwrite defaults
```

The order matters for object spread. Later properties overwrite earlier ones. This is intentional and useful for applying overrides.

## Rest: collecting multiple values

When `...` appears on the receiving side — in a destructuring pattern or a function parameter list — it collects remaining values into an array.

**In function parameters:**

```js
function sum(...numbers) {
  return numbers.reduce((total, n) => total + n, 0);
}

sum(1, 2, 3); // 6
sum(1, 2, 3, 4, 5); // 15
```

`numbers` is an actual array. You can call any array method on it. This is unlike the old `arguments` object, which was array-like but not an array and did not work with arrow functions.

Rest parameters must come last:

```js
function log(level, ...messages) {
  messages.forEach(msg => console.log(`[${level}] ${msg}`));
}

log("INFO", "Server started", "Listening on port 3000");
// [INFO] Server started
// [INFO] Listening on port 3000
```

**In array destructuring:**

```js
const [first, second, ...rest] = [1, 2, 3, 4, 5];
// first = 1, second = 2, rest = [3, 4, 5]
```

Rest in destructuring collects everything that was not explicitly destructured.

**In object destructuring:**

```js
const { name, age, ...remaining } = { name: "Alice", age: 30, role: "admin", dept: "eng" };
// name = "Alice", age = 30, remaining = { role: "admin", dept: "eng" }
```

This is useful for extracting specific properties and passing the rest along:

```js
function createUser({ password, ...safeData }) {
  // password is extracted and not included in safeData
  const hashed = hashPassword(password);
  return db.create({ ...safeData, passwordHash: hashed });
}
```

## The mental model

The position tells you which direction things flow:

- **On the right of `=`, or in a function call:** spread. Values flow outward from the array/object into the surrounding context.
- **On the left of `=`, or in a function parameter:** rest. Values flow inward from the surrounding context into an array/object.

```js
// Spread: expanding [1, 2, 3] into three arguments
Math.max(...[1, 2, 3]);

// Rest: collecting three arguments into an array
function max(...args) { ... }
```

## Shallow copy with spread

Spread creates a shallow copy:

```js
const original = { name: "Alice", address: { city: "Austin" } };
const copy = { ...original };

copy.name = "Bob"; // does not affect original
copy.address.city = "Dallas"; // DOES affect original — same reference
```

This is a shallow copy. Primitive values are copied by value. Objects and arrays are copied by reference. For deep cloning you need `structuredClone` or a library.

## Spread with strings

Spread works on any iterable, including strings:

```js
const chars = [..."hello"]; // ["h", "e", "l", "l", "o"]
const uniqueChars = [...new Set("abracadabra")]; // ["a", "b", "r", "c", "d"]
```

## Spread vs Object.assign

`Object.assign` was the pre-spread way to merge objects:

```js
const merged = Object.assign({}, defaults, custom);
// same result as { ...defaults, ...custom }
```

Spread is cleaner and more commonly used today. The difference: `Object.assign` calls setters on the target object, spread does not. This matters when working with class instances, but for plain objects they behave the same.

Three dots. Two directions. Knowing which one you are looking at comes down to where in the expression it appears.

---
title: "Stop writing for loops. These 7 array methods do it better."
description: "For loops are verbose, error-prone, and harder to read. Modern array methods express intent and reduce bugs."
pubDate: 2024-01-01
tags: ["JavaScript"]
draft: false
---

If you are still writing `for (let i = 0; i < arr.length; i++)` for every array operation, you are doing more work than necessary. JavaScript has had higher-order array methods since ES5, and they are not just syntactic sugar. They express intent, eliminate off-by-one errors, and compose cleanly.

Here are the seven methods that cover the vast majority of real-world array work.

## 1. `map` — transform every element

```js
// for loop version
const prices = [10, 20, 30];
const withTax = [];
for (let i = 0; i < prices.length; i++) {
  withTax.push(prices[i] * 1.08);
}

// map version
const withTax = prices.map(p => p * 1.08);
```

`map` returns a new array of the same length. Use it when you want to transform every element without changing the count.

## 2. `filter` — keep only what passes a test

```js
const users = [
  { name: "Alice", active: true },
  { name: "Bob", active: false },
  { name: "Carol", active: true },
];

const activeUsers = users.filter(u => u.active);
// [{ name: "Alice", active: true }, { name: "Carol", active: true }]
```

`filter` never mutates. It returns a new array with only the elements for which the callback returned truthy.

## 3. `reduce` — collapse an array into a single value

```js
const cart = [
  { item: "shirt", price: 25 },
  { item: "pants", price: 50 },
  { item: "shoes", price: 80 },
];

const total = cart.reduce((sum, item) => sum + item.price, 0);
// 155
```

The second argument to `reduce` is the initial accumulator value. Always provide it explicitly. Omitting it works only when the array is non-empty and the first element happens to be the right type.

`reduce` is also the right tool for grouping:

```js
const byCategory = items.reduce((acc, item) => {
  const key = item.category;
  acc[key] = acc[key] ?? [];
  acc[key].push(item);
  return acc;
}, {});
```

## 4. `find` — get the first match

```js
const users = [
  { id: 1, name: "Alice" },
  { id: 2, name: "Bob" },
];

const user = users.find(u => u.id === 2);
// { id: 2, name: "Bob" }
```

`find` stops as soon as it finds a match. For large arrays this matters. It returns `undefined` if nothing matches, so guard the result before using it.

## 5. `some` and `every` — boolean checks without loops

```js
const scores = [72, 85, 91, 60];

const anyFailing = scores.some(s => s < 70); // true
const allPassing = scores.every(s => s >= 70); // false
```

Both short-circuit. `some` stops at the first truthy result; `every` stops at the first falsy one. There is no reason to use a for loop with a flag variable for this.

## 6. `flatMap` — map then flatten

```js
const sentences = ["hello world", "foo bar"];
const words = sentences.flatMap(s => s.split(" "));
// ["hello", "world", "foo", "bar"]
```

Without `flatMap` you would need `.map(...).flat()`, which creates an intermediate array. `flatMap` handles this in one pass. It only flattens one level deep, which is intentional.

## 7. `findIndex` — get the position, not the item

```js
const tasks = [
  { id: 1, done: false },
  { id: 2, done: true },
  { id: 3, done: false },
];

const idx = tasks.findIndex(t => t.id === 2);
// 1

// Now you can splice or replace by index
const updated = [...tasks.slice(0, idx), { id: 2, done: false }, ...tasks.slice(idx + 1)];
```

Use `findIndex` when you need to know where something is so you can remove or replace it without mutating the original array.

## Chaining them together

The real power shows when you chain:

```js
const result = orders
  .filter(o => o.status === "completed")
  .map(o => o.total)
  .reduce((sum, t) => sum + t, 0);
```

This reads like a sentence. A for loop doing the same thing would require a variable accumulator, a conditional inside the loop body, and careful reading to understand what the end state looks like.

## When to still use a for loop

These methods are not universally better. Use a `for...of` loop when:
- You need to `break` or `continue` early and `some`/`every`/`find` do not fit the shape of the logic.
- You are doing async work and need `await` inside the body (`map` with async callbacks gives you an array of Promises, not resolved values).
- Performance profiling has shown a specific hot path where the method call overhead matters (rare).

For async iteration, use `for...of` with `await`:

```js
for (const user of users) {
  await sendEmail(user.email);
}
```

`Promise.all(users.map(...))` is correct when the async operations are independent and you want them to run concurrently. Sequential async work needs `for...of`.

The default should be array methods. Reach for the for loop only when you have a specific reason.

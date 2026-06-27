---
title: "Destructuring looks simple. It has one trap that breaks real code."
description: "Destructuring is convenient, but renaming, defaults, and nested patterns have edge cases that catch everyone at some point."
pubDate: 2024-01-08
tags: ["JavaScript"]
draft: false
---

Destructuring is one of those features that looks like pure convenience. Pull values out of objects and arrays with less code. No footguns. Except there is one trap that breaks real code more often than it should.

Let's cover how destructuring actually works, then get to the trap.

## Basic object destructuring

```js
const user = { name: "Alice", age: 30, role: "admin" };

const { name, age } = user;
// name = "Alice", age = 30
```

The variable names must match the property names. This is the whole mechanism: the key on the left maps to the property with that name on the object.

## Renaming while destructuring

You can rename with a colon:

```js
const { name: userName, age: userAge } = user;
// userName = "Alice", userAge = 30
```

The syntax is `{ propertyName: variableName }`. The property name comes first; the variable you are creating comes second. This is backwards from how most people read it the first time.

## Default values

```js
const { name, role = "viewer" } = user;
// role = "admin" (the property exists, so default is ignored)

const { permissions = [] } = user;
// permissions = [] (the property doesn't exist, default is used)
```

Defaults only apply when the value is `undefined`. They do not apply when the value is `null`:

```js
const obj = { value: null };
const { value = "default" } = obj;
// value = null — NOT "default"
```

This trips people up when an API returns `null` for missing fields and they expect defaults to kick in.

## The trap: renaming with defaults

Here is the one that breaks real code. Combining renaming and defaults looks like this:

```js
const { name: userName = "Anonymous" } = user;
```

Read it as: take the `name` property, rename it to `userName`, and if it was `undefined` use `"Anonymous"`.

The trap is that the syntax looks like the default applies to the property name, but it applies to the variable name. When people write this for the first time they often accidentally write:

```js
// WRONG: trying to rename name to userName and set default
const { name = "Anonymous": userName } = user; // SyntaxError
```

Or they forget the default is applied to the renamed variable and write code that relies on the wrong behavior. The rule is: `{ source: target = default }`.

## Nested destructuring

```js
const response = {
  data: {
    user: {
      id: 1,
      profile: { bio: "developer" }
    }
  }
};

const { data: { user: { profile: { bio } } } } = response;
// bio = "developer"
```

Nested destructuring works, but becomes unreadable past two levels. More importantly, it throws if any intermediate property is `null` or `undefined`:

```js
const { data: { user: { id } } } = { data: null };
// TypeError: Cannot destructure property 'user' of null
```

For deeply nested API responses, either use optional chaining before destructuring or pull each level out separately:

```js
const { data } = response;
const { user } = data ?? {};
const { id } = user ?? {};
```

## Array destructuring

```js
const [first, second, , fourth] = [1, 2, 3, 4];
// first = 1, second = 2, fourth = 4 (third is skipped with empty comma)
```

Array destructuring uses position, not keys. It works on any iterable, including strings:

```js
const [a, b, c] = "xyz";
// a = "x", b = "y", c = "z"
```

Rest element in arrays:

```js
const [head, ...tail] = [1, 2, 3, 4];
// head = 1, tail = [2, 3, 4]
```

## Destructuring in function parameters

This is where destructuring sees heavy daily use:

```js
function createUser({ name, email, role = "viewer" }) {
  return { name, email, role };
}

createUser({ name: "Alice", email: "alice@example.com" });
// { name: "Alice", email: "alice@example.com", role: "viewer" }
```

The trap here: if the caller passes `undefined` as the argument, or calls the function with no argument at all, JavaScript tries to destructure `undefined` and throws:

```js
createUser(); // TypeError: Cannot destructure property 'name' of undefined
```

Fix it with a default for the whole parameter:

```js
function createUser({ name, email, role = "viewer" } = {}) {
  return { name, email, role };
}

createUser(); // { name: undefined, email: undefined, role: "viewer" }
```

## Destructuring in loops

A common pattern with `Object.entries`:

```js
const config = { host: "localhost", port: 3000, debug: true };

for (const [key, value] of Object.entries(config)) {
  console.log(`${key}: ${value}`);
}
```

And with arrays of objects:

```js
const users = [
  { id: 1, name: "Alice" },
  { id: 2, name: "Bob" },
];

for (const { id, name } of users) {
  console.log(id, name);
}
```

## Swap without a temp variable

One of the cleaner uses of array destructuring:

```js
let a = 1, b = 2;
[a, b] = [b, a];
// a = 2, b = 1
```

Destructuring is not complicated, but the rename-plus-default syntax is genuinely non-obvious. Once you know that `{ source: target = default }` is the order, everything else follows from it.

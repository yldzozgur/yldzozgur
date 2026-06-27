---
title: "JavaScript engine optimization: the hidden classes that matter."
description: "How V8 and other JS engines optimize objects using hidden classes, and the coding patterns that keep your code on the fast path."
pubDate: 2026-01-26
tags: ["Architecture"]
draft: false
---

JavaScript is a dynamic language. Objects can have properties added or removed at any time. Naively implemented, property access would require a hash table lookup on every read or write. V8 avoids this by tracking the "shape" of objects with a structure called hidden classes (also called shapes or maps).

## What hidden classes are

When you create an object, V8 assigns it a hidden class that describes its property layout. Hidden classes are like the struct definitions your JavaScript never had to write. When all objects with the same shape use the same hidden class, V8 can compile property access into direct memory offset reads -- as fast as a C struct.

```javascript
function Point(x, y) {
  this.x = x;
  this.y = y;
}

const p1 = new Point(1, 2);
const p2 = new Point(3, 4);
```

Both `p1` and `p2` share the same hidden class. V8 knows that the `x` property is always at offset 0 and `y` is always at offset 1. Accessing `p1.x` compiles to "read memory at offset 0 from this object."

## How you break the fast path

Hidden classes transition whenever you change an object's shape. The transition is tracked, but it creates a new hidden class, and objects with different shapes can't share compiled code.

**Adding properties in different orders:**

```javascript
const a = {};
a.x = 1;
a.y = 2;
// Hidden class: { x@0, y@1 }

const b = {};
b.y = 2;
b.x = 1;
// Different hidden class: { y@0, x@1 }
```

These two objects look the same to you but have different hidden classes. Code that processes both can't be optimized as well as code that processes only one shape.

**Adding properties outside the constructor:**

```javascript
function User(name) {
  this.name = name;
  // Hidden class: { name@0 }
}

const user = new User("Alice");
user.email = "alice@example.com";
// Different hidden class: { name@0, email@1 }
// Any User without email has a different shape
```

Adding properties after construction creates a hidden class transition. If only some objects get the extra property, you now have objects with two different shapes in the same code path.

**Deleting properties:**

```javascript
const obj = { x: 1, y: 2 };
delete obj.x;
// V8 may fall back to dictionary mode -- much slower
```

Deleting a property can cause V8 to abandon hidden class tracking entirely and fall back to a hash map for property storage ("dictionary mode"). Setting the property to `undefined` or `null` is almost always better than deleting it.

## The practical rules

**Initialize all properties in the constructor:**

```javascript
// Good: all instances have the same shape
function User(name, email) {
  this.name = name;
  this.email = email;
}

// Or with class syntax:
class User {
  constructor(name, email) {
    this.name = name;
    this.email = email;
  }
}
```

Even if some properties will be `null` initially, initializing them in the constructor means all instances share one hidden class.

**Keep object shapes stable:**

```javascript
// Bad: shape varies at runtime
function configureUser(user, opts) {
  if (opts.premium) user.subscriptionId = opts.subscriptionId;
  if (opts.admin) user.adminLevel = opts.adminLevel;
}

// Better: define all properties upfront
function configureUser(user, opts) {
  user.subscriptionId = opts.subscriptionId ?? null;
  user.adminLevel = opts.adminLevel ?? null;
}
```

**Avoid mixing types in the same property:**

```javascript
// Bad: type changes cause deoptimization
const items = [];
items.push({ value: 1 });    // value is a number (Smi)
items.push({ value: "one" }); // value is now a string -- different shape
```

When the type of a property changes, V8 may deoptimize the code that accesses it.

## Seeing it in action

V8's `--trace-opt` and `--trace-deopt` flags log optimization and deoptimization events. In Node.js:

```bash
node --trace-deopt --trace-opt my-script.js
```

You'll see lines like `[deoptimizing ...]` with a reason. Common reasons:
- "wrong type": a property had an unexpected type
- "out of bounds": an array access went out of bounds
- "not a heap number": expected float, got something else

For production, Chrome DevTools' CPU profiler shows "megamorphic" call sites -- code paths where V8 has given up on optimizing because it has seen too many different object shapes.

The payoff for consistent object shapes is real. Tight loops over arrays of objects with uniform shapes run orders of magnitude faster than the same loops over heterogeneous objects.

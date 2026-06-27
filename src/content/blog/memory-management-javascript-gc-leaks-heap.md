---
title: "Memory management in JavaScript: GC, leaks, and the heap snapshot."
description: "How JavaScript's garbage collector works, what causes memory leaks, and how to find them with a heap snapshot in Chrome DevTools."
pubDate: 2026-01-22
tags: ["Architecture"]
draft: false
---

JavaScript manages memory automatically. You allocate objects and the garbage collector frees them when they're no longer reachable. But "automatic" doesn't mean "perfect." Memory leaks in JavaScript are real, they happen in production, and they're subtle enough that most developers don't realize they've written one.

## How the garbage collector works

JavaScript engines use **mark-and-sweep** garbage collection. The GC starts from a set of roots (global variables, the current call stack, active closures) and marks every object it can reach by following references. Anything not marked is unreachable and gets swept -- its memory is reclaimed.

The key insight: an object is alive as long as *something* holds a reference to it. Memory leaks in JavaScript are almost always a case of an object that should be dead still having a live reference somewhere.

```javascript
let leaked = [];

function createLeak() {
  const bigArray = new Array(100000).fill('data');
  leaked.push(() => bigArray.length); // closure holds reference to bigArray
}

// bigArray can never be collected as long as leaked[] holds the closure
```

## The four common leak patterns

**1. Accidental globals**

Variables declared without `var`, `let`, or `const` in non-strict mode become properties of `window`:

```javascript
function foo() {
  bar = []; // creates window.bar, never collected
}
```

Use strict mode (`'use strict'` or ES modules) to catch this.

**2. Forgotten event listeners**

Listeners hold references to everything in their closure scope. If the element is removed from the DOM but the listener isn't removed, the closure (and everything it references) stays alive:

```javascript
// Leak: listener keeps `heavyData` alive even after element is removed
const heavyData = loadHeavyData();
element.addEventListener('click', () => process(heavyData));
document.body.removeChild(element); // element removed, but listener still registered

// Fix: remove listener or use AbortController
const controller = new AbortController();
element.addEventListener('click', handler, { signal: controller.signal });
// Later:
controller.abort(); // removes all listeners with this signal
```

**3. Detached DOM nodes**

Keeping a JavaScript reference to a DOM node that's been removed from the document keeps the entire subtree in memory:

```javascript
let detached;
function createDetachedTree() {
  const root = document.createElement('div');
  for (let i = 0; i < 1000; i++) {
    root.appendChild(document.createElement('span'));
  }
  detached = root; // removed from DOM but referenced here
}
```

**4. Closures capturing large objects**

Closures capture their entire lexical scope. A tiny callback can hold a massive object alive:

```javascript
function setupHandler(config) {
  const largeBuffer = new ArrayBuffer(10 * 1024 * 1024); // 10MB
  
  return function handler() {
    // Only uses config, but largeBuffer is also captured
    return config.name;
  };
}
```

Fix: extract only what's needed:

```javascript
function setupHandler(config) {
  const largeBuffer = new ArrayBuffer(10 * 1024 * 1024);
  const name = config.name; // extract needed value
  // largeBuffer goes out of scope here, can be collected
  return function handler() {
    return name;
  };
}
```

## Finding leaks with heap snapshots

Chrome DevTools' Memory panel takes heap snapshots -- a point-in-time view of all objects currently in memory.

**The three-snapshot technique:**

1. Take snapshot 1 (baseline)
2. Perform the action you suspect leaks (navigate to a page, use a feature)
3. Take snapshot 2
4. Repeat the action several times
5. Take snapshot 3

Compare snapshot 3 to snapshot 1. Objects that exist in snapshot 3 but not in snapshot 1 are candidates for leaks.

In the snapshot view, switch to "Comparison" mode and sort by "# Delta" (count increase). Look for:

- `(array)` growing -- often backing stores for leaked collections
- `Detached HTMLElement` -- DOM nodes no longer in the tree but held by JS
- Named closures or constructor functions you recognize

Click any entry to see what's holding a reference to it. The retainer tree shows the chain of references keeping the object alive.

## WeakMap and WeakRef

For cases where you want to associate data with an object without preventing its collection, use `WeakMap`:

```javascript
const cache = new WeakMap();

function process(element) {
  if (cache.has(element)) return cache.get(element);
  const result = expensiveOperation(element);
  cache.set(element, result); // won't prevent element from being collected
  return result;
}
```

When `element` is collected, its entry in the `WeakMap` is automatically removed. Regular `Map` would keep `element` alive indefinitely.

`WeakRef` lets you hold a weak reference that you can dereference if the object is still alive:

```javascript
const ref = new WeakRef(largeObject);
// Later:
const obj = ref.deref(); // undefined if collected
if (obj) { /* use it */ }
```

The GC is your friend, but only if you let it work. The patterns above are the main ways developers accidentally fight it.

---
title: "Why setTimeout(fn, 0) doesn't run immediately."
description: "setTimeout with a zero delay is not immediate. Understanding why requires understanding the event loop."
pubDate: 2024-01-18
tags: ["JavaScript"]
draft: false
---

```js
setTimeout(() => console.log("timeout"), 0);
console.log("sync");

// Output:
// sync
// timeout
```

The timeout fires after the synchronous code, even though the delay is zero. This confuses most people the first time they see it. The explanation lies in how the JavaScript runtime works.

## The event loop in one paragraph

JavaScript is single-threaded. It executes one piece of code at a time. It has a call stack where function calls live. When the call stack is empty, the event loop picks the next task from the task queue and pushes it onto the stack. Timers, I/O callbacks, and event listeners all put their callbacks into the task queue.

`setTimeout(fn, 0)` schedules `fn` to run no sooner than 0ms from now, but it cannot run until the current task completes and the call stack is empty. It goes into the task queue, and it will be picked up on the next iteration of the event loop.

## The call stack must be empty first

```js
console.log("1");

setTimeout(() => console.log("3"), 0);

console.log("2");

// Output: 1, 2, 3
```

When `setTimeout` is called, the callback is handed to the browser or Node runtime, which registers a timer. The timer fires after ~0ms and places the callback in the task queue. But the current synchronous script is still running. The event loop does not interrupt running tasks. Only once `console.log("2")` has run and the call stack is empty does the event loop pick up the timer callback.

## Microtasks run before the next task

There is a second queue: the microtask queue. Microtasks include Promise callbacks and `queueMicrotask()`. Microtasks are processed after every task, before the event loop picks the next task. This means Promises resolve before `setTimeout` callbacks, even if the `setTimeout` was registered first.

```js
setTimeout(() => console.log("timeout"), 0);

Promise.resolve().then(() => console.log("microtask"));

console.log("sync");

// Output:
// sync
// microtask
// timeout
```

Order of execution:
1. Synchronous code runs: "sync"
2. Current task ends, microtask queue is drained: "microtask"
3. Event loop picks next task from task queue: "timeout"

## Why setTimeout(fn, 0) exists

If it does not run immediately, why use it? Several legitimate reasons:

**Deferring work to after the current task:**

```js
button.addEventListener("click", () => {
  // Update state synchronously
  state.clicked = true;

  // Let the browser render first, then do expensive work
  setTimeout(() => {
    doExpensiveComputation();
  }, 0);
});
```

The browser can repaint between the click handler and the timeout callback. Without `setTimeout`, the expensive computation would block rendering.

**Breaking up long tasks:**

```js
function processLargeArray(items) {
  const chunk = items.splice(0, 100);
  processChunk(chunk);

  if (items.length > 0) {
    setTimeout(() => processLargeArray(items), 0);
  }
}
```

Each call to `processLargeArray` processes 100 items, then yields to the event loop. The UI stays responsive because the call stack clears between chunks.

**Ensuring DOM updates have applied:**

```js
input.value = "";
setTimeout(() => {
  input.focus(); // DOM has updated by the time this runs
}, 0);
```

## The minimum delay is not always 0

Browsers clamp `setTimeout` delays to a minimum of 1ms (some older browsers used 4ms). When a page is in a background tab, the minimum rises to 1000ms to reduce CPU usage.

Node.js has its own event loop phases. `setImmediate` in Node runs before timers in the I/O phase, which is why `setImmediate` and `setTimeout(fn, 0)` can fire in different orders depending on where in the event loop they are called.

## `queueMicrotask` vs `Promise.resolve().then()`

Both schedule microtasks. `queueMicrotask` is more explicit:

```js
queueMicrotask(() => {
  // Runs before next task, after current task
  console.log("microtask");
});
```

Use `queueMicrotask` when you want to schedule microtask-priority work without wrapping it in a Promise.

## Visualizing the order

```js
// What runs when?
console.log("A");

setTimeout(() => console.log("D"), 0);

Promise.resolve()
  .then(() => console.log("B"))
  .then(() => console.log("C"));

console.log("E");

// A, E, B, C, D
```

- A, E: synchronous, runs in order
- B: microtask queued by the first `.then()`, runs after sync
- C: microtask queued by the second `.then()`, runs after B
- D: task queued by setTimeout, runs after all microtasks are drained

`setTimeout(fn, 0)` is a way to say "run this, but not right now." The event loop determines when "not right now" actually is.

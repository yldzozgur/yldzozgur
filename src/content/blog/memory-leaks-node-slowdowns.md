---
title: "Memory leaks in Node look like slowdowns. Here's how to find them."
description: "Memory leaks in Node.js cause gradual performance degradation. Here's how to identify common patterns and use heap snapshots to find them."
pubDate: 2024-04-25
tags: ["Node.js"]
draft: false
---

A Node.js memory leak is when the process retains memory that should have been released. The garbage collector cannot free it because something still holds a reference. The symptom is a process that starts fast and slows down over hours or days, eventually running out of memory or getting restarted by a process manager.

## Common leak patterns

**Global variables:**

```js
// Leak: every request appends to a global array that never shrinks
const requestLog = [];

app.use((req, res, next) => {
  requestLog.push({ url: req.url, time: Date.now() }); // grows forever
  next();
});
```

Fix: use a bounded structure, or stream to a database.

**Event listeners that are never removed:**

```js
// Leak: a new listener is added on every request, never removed
app.get("/start", (req, res) => {
  someEmitter.on("data", (data) => {
    // process data
  });
  res.json({ started: true });
});
```

Every request registers a new listener. After 1000 requests, there are 1000 listeners. They all hold references to closure variables.

Fix: remove listeners when done, or use `once` for one-time events.

**Closures retaining large objects:**

```js
function setup() {
  const largeData = loadHugeDataset(); // 50MB

  return function process(input) {
    // Only needs input, but retains largeData in closure
    return input.toString();
  };
}
```

The returned `process` function retains `largeData` even though it never uses it, because JavaScript closures capture the entire scope.

Fix: extract the function or explicitly null out unneeded references.

**Timers not cleared:**

```js
class PollingService {
  start() {
    this.timer = setInterval(() => this.poll(), 5000);
  }

  // Missing: stop() that calls clearInterval(this.timer)
}

// If instances are created and not stopped, they keep polling forever
```

## Detecting a leak

The first sign is memory usage growing over time. Monitor it:

```js
setInterval(() => {
  const { heapUsed, heapTotal } = process.memoryUsage();
  console.log({
    heapUsed: Math.round(heapUsed / 1024 / 1024) + "MB",
    heapTotal: Math.round(heapTotal / 1024 / 1024) + "MB",
  });
}, 30_000);
```

If `heapUsed` grows without bound, there is a leak.

## Heap snapshots

The most effective tool for finding leaks is heap snapshots in Chrome DevTools.

```bash
node --inspect app.js
```

1. Open `chrome://inspect` and connect
2. Go to the Memory tab
3. Take a heap snapshot (baseline)
4. Trigger the suspected leak (make requests, run operations)
5. Take another heap snapshot
6. Use the "Comparison" view to see what was added

The Comparison view shows every object allocated between the two snapshots. Look for growing arrays, unexpected object counts, and closures holding large objects.

## Using the --expose-gc flag

```bash
node --inspect --expose-gc app.js
```

With `--expose-gc`, you can trigger garbage collection manually:

```js
// In the DevTools console or your code:
global.gc();
```

Force GC before taking a snapshot to eliminate objects that are eligible for collection. This makes the snapshot show only genuine leaks, not objects waiting to be collected.

## A diagnostic script

```js
const v8 = require("v8");

function takeHeapSnapshot(label) {
  const filename = `heap-${label}-${Date.now()}.heapsnapshot`;
  const snapshot = v8.writeHeapSnapshot(filename);
  console.log(`Heap snapshot written to ${snapshot}`);
}

// Take snapshots before and after an operation
takeHeapSnapshot("before");
runOperation();
takeHeapSnapshot("after");
```

The `.heapsnapshot` file can be loaded directly in Chrome DevTools Memory tab.

## WeakRef and FinalizationRegistry

For cache patterns where you want objects to be GC-able:

```js
const cache = new Map();

function getOrCreate(key, factory) {
  const ref = cache.get(key);
  if (ref) {
    const value = ref.deref();
    if (value !== undefined) return value;
  }

  const value = factory();
  cache.set(key, new WeakRef(value));
  return value;
}
```

`WeakRef` holds a weak reference. The referenced object can be garbage collected if there are no strong references. `ref.deref()` returns the object or `undefined` if it was collected.

This is useful for caches: if memory is needed, the cache entries can be freed automatically.

## Production memory monitoring

In production, use a metrics system to track memory over time:

```js
const { heapUsed } = process.memoryUsage();
metrics.gauge("node.heap_used_bytes", heapUsed);
```

Set an alert if memory grows by more than X% per hour. A slowly growing heap is often the first sign of a leak that will cause an outage in a few days.

Memory leaks in Node are usually deterministic once you find them. The challenge is finding them. Heap snapshots are the most direct tool.

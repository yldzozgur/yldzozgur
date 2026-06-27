---
title: "Worker threads: CPU-bound work that doesn't block your server."
description: "Node.js is single-threaded, but worker threads let you run CPU-intensive code in parallel without blocking the event loop."
pubDate: 2024-04-15
tags: ["Node.js"]
draft: false
---

Node.js is excellent for I/O-bound work. Thousands of concurrent requests reading from databases or calling APIs work well because they spend most of their time waiting, not computing. CPU-bound work is different.

When you run a heavy computation on the main thread, you block the event loop. No other requests are processed until the computation finishes. This is the problem worker threads solve.

## What blocks the event loop

```js
app.get("/slow", (req, res) => {
  // This blocks the event loop for ~1 second
  const result = expensiveComputation();
  res.json(result);
});

function expensiveComputation() {
  let result = 0;
  for (let i = 0; i < 1_000_000_000; i++) {
    result += Math.sqrt(i);
  }
  return result;
}
```

During that loop, no other HTTP requests can be handled. The server is effectively single-threaded and frozen.

## Worker threads

```js
// worker.js
const { workerData, parentPort } = require("worker_threads");

function expensiveComputation(n) {
  let result = 0;
  for (let i = 0; i < n; i++) {
    result += Math.sqrt(i);
  }
  return result;
}

const result = expensiveComputation(workerData.n);
parentPort.postMessage({ result });
```

```js
// main.js
const { Worker } = require("worker_threads");
const path = require("path");

function runWorker(data) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(path.join(__dirname, "worker.js"), {
      workerData: data,
    });

    worker.on("message", (msg) => resolve(msg.result));
    worker.on("error", reject);
    worker.on("exit", (code) => {
      if (code !== 0) reject(new Error(`Worker exited with code ${code}`));
    });
  });
}

app.get("/compute", async (req, res) => {
  const result = await runWorker({ n: 1_000_000_000 });
  res.json({ result });
  // Main thread was free during the computation
});
```

The heavy computation runs in the worker thread. The main thread is free to handle other requests.

## Worker thread vs child_process

Both can run CPU work in parallel. Key differences:

**Worker threads:**
- Share memory with the main thread via `SharedArrayBuffer`
- Lighter weight — workers share the same process
- Can transfer data with zero copy using `transferList`
- Same memory space means shared V8 heap limits apply

**child_process.fork:**
- Separate process — separate memory space
- Higher overhead per instance
- Complete isolation (a crash in the child doesn't affect the parent)
- Better for running separate programs or scripts

Use worker threads for parallelizing CPU-intensive JavaScript work. Use `child_process` when you need process isolation or are running a separate program.

## Thread pool pattern

Creating a new worker per request is expensive. A thread pool reuses workers:

```js
const { Worker } = require("worker_threads");

class WorkerPool {
  constructor(workerPath, size) {
    this.workers = Array.from({ length: size }, () =>
      new Worker(workerPath)
    );
    this.queue = [];
    this.available = [...this.workers];

    for (const worker of this.workers) {
      worker.on("message", (result) => {
        const resolve = worker._resolve;
        worker._resolve = null;
        this.available.push(worker);
        this._processQueue();
        resolve(result);
      });
    }
  }

  run(data) {
    return new Promise((resolve, reject) => {
      this.queue.push({ data, resolve, reject });
      this._processQueue();
    });
  }

  _processQueue() {
    if (this.queue.length === 0 || this.available.length === 0) return;
    const worker = this.available.pop();
    const { data, resolve, reject } = this.queue.shift();
    worker._resolve = resolve;
    worker.postMessage(data);
  }
}

const pool = new WorkerPool(
  path.join(__dirname, "worker.js"),
  require("os").cpus().length
);

app.get("/compute", async (req, res) => {
  const result = await pool.run({ n: 1_000_000_000 });
  res.json({ result });
});
```

This pool creates one worker per CPU core. Workers are reused across requests.

## Shared memory

Worker threads can share memory via `SharedArrayBuffer`:

```js
// main.js
const shared = new SharedArrayBuffer(4);
const view = new Int32Array(shared);

const worker = new Worker("./worker.js", {
  workerData: { shared }
});

worker.on("message", () => {
  console.log(view[0]); // Read result written by worker
});

// worker.js
const { workerData } = require("worker_threads");
const view = new Int32Array(workerData.shared);

Atomics.store(view, 0, 42); // Thread-safe write
parentPort.postMessage("done");
```

`Atomics` provides thread-safe operations on shared memory. Use it when coordinating between threads.

## When to use worker threads

Worker threads are worth the added complexity when:
- A single operation takes more than a few hundred milliseconds of CPU time
- The operation cannot be broken into smaller async pieces
- You need more throughput than a single CPU core can provide

For most web servers, the bottleneck is I/O, not CPU. Reach for worker threads when profiling shows CPU-bound work is affecting response times.

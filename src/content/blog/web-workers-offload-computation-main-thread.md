---
title: "Web Workers: offloading computation without blocking the main thread."
description: "How Web Workers move CPU-intensive tasks off the main thread, with examples for parsing, image processing, and communication patterns."
pubDate: 2025-10-16
tags: ["JavaScript", "Performance"]
draft: false
---

JavaScript is single-threaded. When your code is running, the browser cannot respond to user input, cannot repaint the screen, cannot do anything else. A 500ms computation freezes the UI for half a second. Web Workers solve this by running code on a separate thread.

## Why the main thread freezes

The browser's main thread handles everything: JavaScript execution, DOM updates, CSS calculation, user input, animations. When a long-running script runs, it blocks all of this.

```javascript
// This freezes the UI for the duration
function processLargeArray(data) {
  return data.map(item => expensiveTransform(item)); // 800ms of CPU work
}

button.addEventListener("click", () => {
  const result = processLargeArray(largeDataset); // UI freezes here
  displayResult(result);
});
```

The user clicks the button and the page becomes unresponsive until the computation finishes.

## Creating a Web Worker

A worker runs in a separate JavaScript environment. It has no access to the DOM, no `window` object, no `document`. It communicates with the main thread through message passing.

```javascript
// worker.js
self.addEventListener("message", (event) => {
  const { data } = event.data;
  const result = processLargeArray(data);
  self.postMessage({ result });
});

function processLargeArray(data) {
  return data.map(item => expensiveTransform(item));
}

function expensiveTransform(item) {
  // CPU-intensive work
  return { ...item, processed: true };
}
```

```javascript
// main.js
const worker = new Worker("/worker.js");

worker.addEventListener("message", (event) => {
  const { result } = event.data;
  displayResult(result);
});

button.addEventListener("click", () => {
  worker.postMessage({ data: largeDataset }); // Non-blocking
  showLoadingSpinner(); // UI stays responsive
});
```

`postMessage` is non-blocking. The main thread sends the data and immediately continues. The worker processes it on a separate thread. When done, it posts back and the main thread's message handler receives the result.

## Transferable objects: avoiding data copy overhead

By default, `postMessage` copies data using the structured clone algorithm. For large arrays or ArrayBuffers, this copy can itself take significant time.

Use transferable objects to move the data without copying:

```javascript
// main.js
const buffer = new ArrayBuffer(1024 * 1024 * 10); // 10 MB

// Transfer ownership to worker (no copy)
worker.postMessage({ buffer }, [buffer]);

// buffer is now detached in the main thread
console.log(buffer.byteLength); // 0 - ownership transferred
```

```javascript
// worker.js
self.addEventListener("message", (event) => {
  const { buffer } = event.data;
  // Process buffer...
  
  // Transfer back to main thread
  self.postMessage({ buffer }, [buffer]);
});
```

Transferring ownership is O(1) regardless of data size. This matters when working with audio samples, image pixel data, or large datasets.

## Inline workers with Blob URLs

For small workers or build system complications, create a worker from a string:

```javascript
const workerCode = `
  self.addEventListener("message", (event) => {
    const result = event.data.numbers.reduce((a, b) => a + b, 0);
    self.postMessage({ sum: result });
  });
`;

const blob = new Blob([workerCode], { type: "application/javascript" });
const workerUrl = URL.createObjectURL(blob);
const worker = new Worker(workerUrl);
```

Clean up the object URL when the worker is no longer needed:

```javascript
worker.terminate();
URL.revokeObjectURL(workerUrl);
```

## Worker pools

Creating a worker has overhead. For repeated short tasks, maintain a pool of workers:

```javascript
class WorkerPool {
  constructor(workerUrl, size = navigator.hardwareConcurrency ?? 4) {
    this.workers = Array.from({ length: size }, () => ({
      worker: new Worker(workerUrl),
      busy: false
    }));
    this.queue = [];
  }

  run(data) {
    return new Promise((resolve, reject) => {
      const idle = this.workers.find(w => !w.busy);

      if (idle) {
        this.dispatch(idle, data, resolve, reject);
      } else {
        this.queue.push({ data, resolve, reject });
      }
    });
  }

  dispatch(entry, data, resolve, reject) {
    entry.busy = true;
    entry.worker.onmessage = (e) => {
      resolve(e.data);
      entry.busy = false;
      if (this.queue.length > 0) {
        const next = this.queue.shift();
        this.dispatch(entry, next.data, next.resolve, next.reject);
      }
    };
    entry.worker.postMessage(data);
  }
}

const pool = new WorkerPool("/processor.js", 4);
const result = await pool.run({ imageData });
```

## Good use cases for Web Workers

**CSV/JSON parsing**: Large files that take hundreds of milliseconds to parse in the main thread. Parse in a worker, post back the structured data.

**Image processing**: Apply filters, resize, or compress images using pixel manipulation on an OffscreenCanvas.

**Cryptography**: Hashing large files, key derivation functions that are intentionally slow (bcrypt, Argon2 running via WebAssembly).

**Search indexing**: Build and query an in-memory search index without blocking user interaction.

**Data visualization**: Pre-compute layout positions for large graphs or charts.

## Using workers in frameworks

In Vite-based projects, the `?worker` suffix creates typed worker modules:

```javascript
import DataWorker from "./dataWorker?worker";

const worker = new DataWorker();
worker.postMessage({ data });
```

In Next.js, workers must be initialized client-side only:

```javascript
useEffect(() => {
  const worker = new Worker(new URL("./worker.js", import.meta.url));
  worker.onmessage = (e) => setResult(e.data);
  return () => worker.terminate();
}, []);
```

The key rule: any computation that might take more than 50ms belongs off the main thread. That's the threshold where users start to perceive unresponsiveness.

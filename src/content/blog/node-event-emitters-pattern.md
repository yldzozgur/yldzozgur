---
title: "Node event emitters: the pattern under half of the ecosystem."
description: "EventEmitter is the backbone of Node.js streams, HTTP servers, and many popular packages. Understanding it makes the rest of Node.js click."
pubDate: 2024-03-28
tags: ["Node.js"]
draft: false
---

If you have used Node.js streams, the HTTP module, or many npm packages, you have used `EventEmitter` without necessarily knowing it. Streams emit `data` and `end`. HTTP servers emit `request`. The file watcher emits `change`. Understanding `EventEmitter` directly makes all of these easier to work with.

## The basic API

```js
const { EventEmitter } = require("events");

const emitter = new EventEmitter();

// Register a listener
emitter.on("greet", (name) => {
  console.log(`Hello, ${name}!`);
});

// Emit the event
emitter.emit("greet", "Alice"); // "Hello, Alice!"
emitter.emit("greet", "Bob"); // "Hello, Bob!"
```

`on` registers a listener for an event name. `emit` fires the event and passes arguments to all registered listeners. An emitter can have multiple listeners for the same event — all of them run.

## One-time listeners

```js
emitter.once("ready", () => {
  console.log("Ready fired once");
});

emitter.emit("ready"); // "Ready fired once"
emitter.emit("ready"); // Nothing — listener was removed after first call
```

`once` registers a listener that automatically removes itself after firing.

## Removing listeners

```js
function handleData(data) {
  console.log(data);
}

emitter.on("data", handleData);

// Later:
emitter.off("data", handleData); // Remove the specific listener
// or
emitter.removeListener("data", handleData); // Same thing
// or
emitter.removeAllListeners("data"); // Remove all listeners for "data"
```

Removing listeners when they are no longer needed is important for preventing memory leaks. If you add listeners inside loops or repeatedly called functions without removing them, the emitter accumulates listeners indefinitely.

## The error event

`EventEmitter` has special handling for the `"error"` event:

```js
emitter.on("error", (err) => {
  console.error("Error:", err.message);
});

emitter.emit("error", new Error("Something went wrong"));
```

If an `"error"` event is emitted and there is no listener for it, Node.js throws the error and crashes the process. Always add an error listener to emitters that might emit errors.

## Extending EventEmitter

The most common use is extending it to build your own event-driven classes:

```js
const { EventEmitter } = require("events");

class DataProcessor extends EventEmitter {
  process(items) {
    this.emit("start", items.length);

    for (const item of items) {
      try {
        const result = this.processItem(item);
        this.emit("item", result);
      } catch (err) {
        this.emit("error", err);
      }
    }

    this.emit("done");
  }

  processItem(item) {
    // ... processing logic
    return item;
  }
}

const processor = new DataProcessor();

processor.on("start", (count) => console.log(`Processing ${count} items`));
processor.on("item", (result) => console.log("Processed:", result));
processor.on("error", (err) => console.error("Failed:", err));
processor.on("done", () => console.log("All done"));

processor.process([1, 2, 3]);
```

The caller registers interest in specific events. The emitter fires events as things happen. Neither side needs to know the details of the other's logic.

## EventEmitter and streams

Node.js streams extend `EventEmitter`. Reading a file stream:

```js
const fs = require("fs");

const stream = fs.createReadStream("large-file.txt", { encoding: "utf8" });

stream.on("data", (chunk) => {
  process.stdout.write(chunk);
});

stream.on("end", () => {
  console.log("\nDone reading");
});

stream.on("error", (err) => {
  console.error("Read error:", err);
});
```

The stream emits `data` for each chunk, `end` when finished, and `error` if something goes wrong. The EventEmitter pattern is what makes this work.

## Listener count and memory leak warning

```js
// Default max listeners: 10
// Exceeding this prints a warning
for (let i = 0; i < 15; i++) {
  emitter.on("event", () => {});
}
// MaxListenersExceededWarning: Possible EventEmitter memory leak detected

// Increase the limit if you legitimately need more:
emitter.setMaxListeners(20);

// Or suppress the warning entirely (use carefully):
emitter.setMaxListeners(0);
```

This warning is useful. If you are accidentally adding listeners in a loop, it will tell you.

## Async listeners

EventEmitter listeners can be async, but errors in async listeners are not automatically caught:

```js
emitter.on("data", async (data) => {
  await processData(data); // if this throws, the error is an unhandled rejection
});

// Safe version:
emitter.on("data", async (data) => {
  try {
    await processData(data);
  } catch (err) {
    emitter.emit("error", err); // route errors through the emitter's error event
  }
});
```

EventEmitter is synchronous by default — all listeners run synchronously when `emit` is called. Async listeners do not block the emitter and do not report errors back to it automatically.

The event emitter pattern is one of the most fundamental patterns in Node.js. Once you understand it directly, reading the documentation for any event-based API becomes much more straightforward.

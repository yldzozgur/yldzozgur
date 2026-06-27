---
title: "Backpressure: what happens when your consumer is slower than your producer."
description: "Understanding backpressure in data pipelines, streams, and message queues -- and the patterns that prevent your system from falling over."
pubDate: 2026-01-01
tags: ["Architecture"]
draft: false
---

Imagine a garden hose connected to a fire hydrant. The hydrant produces water faster than the hose can carry it. Something has to give: the hose bursts, or the hydrant is throttled back, or water spills everywhere. This is the backpressure problem, and it shows up constantly in software systems.

## What backpressure actually is

Backpressure is a signal that flows upstream: "slow down, I can't keep up." Without it, the producer keeps generating data and the consumer's buffer fills until the system either drops data, crashes, or runs out of memory.

The term comes from fluid dynamics but maps cleanly to:

- A Kafka consumer that processes messages slower than the topic receives them
- A Node.js readable stream piped to a slow writable stream
- An API client calling a downstream service faster than it can respond
- A UI rendering updates faster than the browser can paint

## Backpressure in Node.js streams

Node.js streams have backpressure built in via the `highWaterMark` and the return value of `.write()`:

```javascript
const readable = fs.createReadStream('large-file.csv');
const writable = fs.createWriteStream('output.csv');

// pipe() handles backpressure automatically
readable.pipe(writable);
```

`pipe()` works because it listens for the `drain` event. When `writable.write()` returns `false` (the internal buffer is full), `pipe()` pauses the readable. When the writable drains, it resumes.

Doing this manually shows why `pipe()` exists:

```javascript
readable.on('data', (chunk) => {
  const ok = writable.write(chunk);
  if (!ok) {
    readable.pause();
    writable.once('drain', () => readable.resume());
  }
});
```

Skip this and you're reading from disk into memory faster than you can write it out. For small files it doesn't matter. For a 10 GB file, you run out of RAM.

## Message queues and consumer lag

In Kafka, backpressure manifests as consumer lag: the difference between the latest offset in a partition and the consumer's current offset. If lag grows continuously, the consumer can never catch up.

Strategies:

**Scale consumers horizontally.** Add more consumer instances up to the number of partitions. Beyond that, extra consumers sit idle -- Kafka assigns one consumer per partition per group.

**Reduce processing time.** Profile what the consumer actually does. Often a slow database call or a synchronous HTTP request is the bottleneck. Batch the DB writes:

```typescript
const buffer: Message[] = [];

consumer.on('message', async (msg) => {
  buffer.push(msg);
  if (buffer.length >= 100) {
    await db.bulkInsert(buffer);
    buffer.length = 0;
  }
});
```

**Use a semaphore to limit concurrency.** If your consumer processes messages concurrently, unbounded concurrency can overwhelm downstream dependencies:

```typescript
import { Semaphore } from 'async-mutex';

const sem = new Semaphore(10); // max 10 concurrent

consumer.on('message', async (msg) => {
  const [, release] = await sem.acquire();
  try {
    await processMessage(msg);
  } finally {
    release();
  }
});
```

## RxJS and reactive backpressure

RxJS operators give you fine-grained control over how fast events flow through a pipeline:

```typescript
import { fromEvent, debounceTime, throttleTime } from 'rxjs';

// Only emit the last value in a 300ms window
fromEvent(input, 'keyup').pipe(
  debounceTime(300)
).subscribe(search);

// Emit at most one value per 1000ms, drop the rest
fromEvent(button, 'click').pipe(
  throttleTime(1000)
).subscribe(submitOrder);
```

`debounceTime` is for "I only care about when the user stops typing." `throttleTime` is for "I only care about the first event in each window." Both are forms of backpressure -- they deliberately discard events to keep the downstream from being overwhelmed.

For cases where you don't want to drop events but want to buffer them:

```typescript
import { bufferTime } from 'rxjs';

events$.pipe(
  bufferTime(500) // collect into arrays every 500ms
).subscribe(batch => processBatch(batch));
```

## The three failure modes

When backpressure isn't handled, systems fail in one of three ways:

**Drop:** Events are discarded silently. Fast and safe, but you lose data. Appropriate for metrics and logs where losing a few samples is acceptable.

**Block:** The producer stalls waiting for the consumer. This preserves every event but reduces throughput and can cause timeouts higher up the call stack.

**Crash:** The buffer grows unboundedly until OOM kills the process. This is what happens when you ignore the problem.

## Designing for backpressure

When you design a data pipeline or streaming system, ask:

1. What is the maximum rate the consumer can sustain?
2. What happens when the producer exceeds that rate?
3. Is data loss acceptable or must every event be processed?

The answer determines your strategy: rate limiting at the source, load shedding with explicit drop policies, buffering with a bounded queue, or horizontal scaling of consumers. The worst answer is no answer -- letting the system figure it out at 3am under production load.

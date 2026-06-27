---
title: "Graceful shutdown: the signal handler every production Node app needs."
description: "Without a shutdown handler, your Node process drops active connections when it stops. Here's how to finish in-flight requests before exiting."
pubDate: 2024-04-18
tags: ["Node.js"]
draft: false
---

When you deploy a new version of your application, the old process needs to stop. If you kill it abruptly, active connections are dropped, in-flight database transactions may be left incomplete, and users get errors. Graceful shutdown finishes what is in progress before exiting.

## How processes are stopped

When you kill a Node.js process, the operating system sends a signal:
- `SIGTERM`: polite stop request. Docker, Kubernetes, and process managers send this first.
- `SIGINT`: interrupt from terminal (Ctrl+C). Also used in development.
- `SIGKILL`: forced kill. Cannot be caught. Always terminates immediately.

A proper shutdown handler responds to `SIGTERM` and `SIGINT` by:
1. Stopping acceptance of new requests
2. Waiting for in-flight requests to complete
3. Closing database connections and other resources
4. Exiting cleanly

## Basic shutdown handler

```js
const http = require("http");

const server = http.createServer(app);
server.listen(3000);

async function shutdown() {
  console.log("Shutting down...");

  // Stop accepting new connections
  server.close(async () => {
    console.log("HTTP server closed");

    // Close database connection
    await db.end();
    console.log("Database connection closed");

    process.exit(0);
  });

  // Force exit if graceful shutdown takes too long
  setTimeout(() => {
    console.error("Shutdown timed out, forcing exit");
    process.exit(1);
  }, 10_000);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
```

`server.close()` stops accepting new connections but waits for existing connections to close before calling the callback.

## The timeout is essential

Without a timeout, a single long-lived connection (a WebSocket client, a slow request) could prevent the process from ever exiting. The timeout ensures the process always exits within a bounded time.

The timeout duration depends on your SLA and the nature of your requests. 10-30 seconds is typical.

## Tracking in-flight requests

`server.close()` waits for connections to end, but HTTP/1.1 keep-alive connections stay open even after a request finishes. You may need to track active requests and close idle connections:

```js
let activeRequests = 0;

app.use((req, res, next) => {
  activeRequests++;
  res.on("finish", () => activeRequests--);
  next();
});

async function shutdown() {
  console.log(`Shutdown: ${activeRequests} active requests`);

  server.close(async () => {
    await db.end();
    process.exit(0);
  });

  // For keep-alive connections, set Connection: close header
  // so clients don't reuse the connection after this response
  app.use((req, res, next) => {
    res.set("Connection", "close");
    next();
  });

  setTimeout(() => process.exit(1), 10_000);
}
```

## Preventing double shutdown

If both SIGTERM and SIGINT arrive (possible during restart scripts), you should not call shutdown twice:

```js
let shuttingDown = false;

async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;

  console.log(`Received ${signal}, shutting down`);

  server.close(async () => {
    await db.end();
    process.exit(0);
  });

  setTimeout(() => process.exit(1), 10_000);
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
```

## Cleanup for other resources

Database connections are not the only resources that need cleanup:

```js
async function cleanup() {
  const cleanups = [
    db.end(),
    redisClient.quit(),
    messageQueue.close(),
    scheduler.stop(),
  ];

  await Promise.allSettled(cleanups); // use allSettled so one failure doesn't block others
}

async function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;

  server.close(async () => {
    await cleanup();
    process.exit(0);
  });

  setTimeout(() => process.exit(1), 15_000);
}
```

`Promise.allSettled` ensures all cleanup attempts run even if one fails. You do not want a failing Redis cleanup to prevent the database connection from closing.

## With Express and a typical stack

```js
const express = require("express");
const { createServer } = require("http");

const app = express();
const server = createServer(app);

// ... routes and middleware ...

server.listen(process.env.PORT ?? 3000, () => {
  console.log("Server started");
});

let shuttingDown = false;

async function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;

  // Return 503 for new requests during shutdown
  app.use((req, res) => {
    res.status(503).json({ error: "Server is shutting down" });
  });

  server.close(async () => {
    await db.end();
    process.exit(0);
  });

  setTimeout(() => process.exit(1), 15_000);
}

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
```

Adding the 503 middleware after shutdown starts means any requests that slip through after `server.close()` is called get a meaningful error instead of hanging.

Graceful shutdown is one of those things that seems optional until a deployment causes 5 seconds of errors for every user with an active request. Add it before your first production deployment.

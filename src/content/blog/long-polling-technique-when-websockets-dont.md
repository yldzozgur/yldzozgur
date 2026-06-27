---
title: "Long polling: the technique that works when WebSockets don't."
description: "Long polling simulates real-time updates using regular HTTP requests held open until data is available. It's a reliable fallback and sometimes the right primary approach."
pubDate: 2026-05-14
tags: ["HTTP", "JavaScript"]
draft: false
---

WebSockets and server-sent events require persistent connections. Some environments — certain proxies, load balancers, or corporate firewalls — terminate idle connections or don't support upgraded protocols. Long polling works in all of these environments because it's just HTTP.

## How it works

In regular short polling, the client asks "do you have anything for me?" at a fixed interval. If the server has nothing, it responds immediately with an empty result. The client waits, then asks again.

Long polling inverts the pattern. The client sends a request and the server holds it open — suspending the response — until it has something to send. When data arrives, the server responds with it. The client immediately makes another request. From the outside it looks like a continuous stream of updates; under the hood it's a sequence of HTTP requests.

```
Client                           Server
  |                                |
  |-------- GET /poll ------------>|
  |                                | (holds request, waiting for data)
  |                                | (data becomes available)
  |<------- 200 {event: ...} ------|
  |-------- GET /poll ------------>| (immediately reconnects)
  |                                | (holds request again)
```

## Server implementation

The key is holding the connection open and checking for data asynchronously:

```typescript
// Express server with long polling
const waitingClients = new Map<string, (data: unknown) => void>();

app.get('/poll', async (req, res) => {
  const userId = req.query.userId as string;
  const lastEventId = req.query.lastEventId as string;

  // Check if there's already queued data for this user
  const pending = await messageQueue.getPending(userId, afterId: lastEventId);
  if (pending.length > 0) {
    return res.json({ events: pending });
  }

  // No data yet — hold the request open
  const timeout = setTimeout(() => {
    waitingClients.delete(userId);
    // Respond with empty result after timeout; client will reconnect
    res.json({ events: [], nextPollAfter: 0 });
  }, 30_000); // 30 second timeout

  waitingClients.set(userId, (data) => {
    clearTimeout(timeout);
    waitingClients.delete(userId);
    res.json({ events: [data] });
  });

  // Clean up if client disconnects before response
  req.on('close', () => {
    clearTimeout(timeout);
    waitingClients.delete(userId);
  });
});

// When new data arrives, wake up any waiting client
async function publishToUser(userId: string, data: unknown) {
  await messageQueue.enqueue(userId, data);

  const resolve = waitingClients.get(userId);
  if (resolve) {
    resolve(data);
  }
}
```

## Client implementation

```typescript
async function startLongPolling(userId: string, onEvent: (event: Event) => void) {
  let lastEventId = '';
  let active = true;

  async function poll() {
    if (!active) return;

    try {
      const url = new URL('/poll', window.location.origin);
      url.searchParams.set('userId', userId);
      if (lastEventId) url.searchParams.set('lastEventId', lastEventId);

      const response = await fetch(url, {
        signal: AbortSignal.timeout(35_000), // slightly more than server timeout
      });

      if (!response.ok) throw new Error(`Poll failed: ${response.status}`);

      const { events } = await response.json();

      for (const event of events) {
        lastEventId = event.id;
        onEvent(event);
      }

      // Immediately reconnect
      poll();
    } catch (error) {
      if (!active) return;
      // Back off on error, then retry
      console.warn('Poll error, retrying in 5s:', error);
      setTimeout(poll, 5_000);
    }
  }

  poll();

  return () => { active = false; };
}
```

## Handling the timeout case

The server must respond before the connection times out (either at the server, proxy, or load balancer level). Sending an empty response with a 200 status is the standard approach. The client treats an empty response as "nothing happened, reconnect immediately."

Setting the server timeout slightly below the infrastructure timeout (proxy, load balancer) prevents the infrastructure from returning a 504 that the client might misinterpret as an error.

## Comparing the approaches

Long polling creates more HTTP connections than WebSockets or SSE, which creates more per-connection overhead. For applications where WebSockets are viable, they're more efficient.

Long polling advantages:
- Works through proxies that don't support WebSocket upgrades or persistent connections
- Works in HTTP/1.1 environments without concerns about connection limits
- Simple to implement without any protocol upgrade machinery
- Easy to add standard HTTP caching, auth headers, and retry logic

A common pattern is to try WebSockets first and fall back to long polling when the upgrade fails. Libraries like Socket.io do this automatically. But for internal tools, admin dashboards, or environments where you control the network, starting with long polling and skipping WebSockets is a perfectly reasonable choice.

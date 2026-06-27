---
title: "Server-sent events: one-way streaming without WebSocket complexity."
description: "Server-sent events push data from server to client over a persistent HTTP connection. For many real-time use cases they're simpler and more appropriate than WebSockets."
pubDate: 2026-05-11
tags: ["HTTP", "JavaScript"]
draft: false
---

WebSockets get reached for whenever "real-time" comes up, but most real-time use cases only need data to flow one way: from server to client. Live notifications, progress updates, activity feeds, log streaming — all of these are server-to-client pushes. WebSockets add bidirectional complexity that these use cases don't need.

Server-sent events (SSE) are a simpler alternative. They're a standard browser API that opens a persistent HTTP connection and receives a stream of events from the server. No protocol upgrade, no separate port, no special handling for firewalls.

## The server side

SSE uses a specific content type (`text/event-stream`) and a simple text format: lines prefixed with `data:`, separated by blank lines.

```javascript
// Node.js with Express
app.get('/events', (req, res) => {
  // Set headers for SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  // Send an event every second
  const interval = setInterval(() => {
    const data = JSON.stringify({ timestamp: Date.now(), value: Math.random() });

    // SSE format: "data: <payload>\n\n"
    res.write(`data: ${data}\n\n`);
  }, 1000);

  // Named events
  res.write(`event: connected\ndata: {"status":"ready"}\n\n`);

  // Retry interval hint (ms) — how long client waits before reconnecting
  res.write(`retry: 3000\n\n`);

  // Clean up when client disconnects
  req.on('close', () => {
    clearInterval(interval);
    res.end();
  });
});
```

## The client side

The browser's `EventSource` API handles connection, reconnection, and event parsing:

```javascript
const source = new EventSource('/events');

// Default message handler
source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data.timestamp);
};

// Named event handler
source.addEventListener('connected', (event) => {
  const status = JSON.parse(event.data);
  console.log('Connection status:', status.status);
});

// Error and reconnection
source.onerror = (error) => {
  if (source.readyState === EventSource.CLOSED) {
    console.log('Connection closed');
  }
  // EventSource reconnects automatically
};

// Stop listening
function cleanup() {
  source.close();
}
```

The browser reconnects automatically when the connection drops. It sends the `Last-Event-ID` header if the server included event IDs, so you can resume from the last received event:

```javascript
// Server: include event IDs for resumable streams
let eventId = 0;
const interval = setInterval(() => {
  eventId++;
  const lastId = req.headers['last-event-id'];
  // Resume from where the client left off if reconnecting
  res.write(`id: ${eventId}\ndata: ${JSON.stringify({ seq: eventId })}\n\n`);
}, 1000);
```

## Next.js app router example

```typescript
// app/api/stream/route.ts
export async function GET(request: Request) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const sendEvent = (data: object) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(data)}\n\n`)
        );
      };

      sendEvent({ type: 'start', timestamp: Date.now() });

      // Stream progress updates from a long-running job
      for await (const update of longRunningJob()) {
        sendEvent({ type: 'progress', progress: update.progress });

        if (update.done) {
          sendEvent({ type: 'complete', result: update.result });
          controller.close();
          break;
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });
}
```

## SSE vs WebSockets

| | SSE | WebSockets |
|---|---|---|
| Direction | Server to client only | Bidirectional |
| Protocol | HTTP | Upgraded connection |
| Reconnection | Automatic | Manual |
| Browser support | All modern browsers | All modern browsers |
| Proxy/firewall support | Better (standard HTTP) | Sometimes blocked |
| Max connections per domain | 6 (HTTP/1.1), unlimited (HTTP/2) | No limit |

Use SSE when the client only needs to receive data. Use WebSockets when the client also needs to send data (chat, collaborative editing, games).

## Limitations worth knowing

Over HTTP/1.1, browsers limit SSE connections per domain to 6. HTTP/2 removes this limit. For applications with many SSE connections per user — multiple browser tabs — this can be an issue on HTTP/1.1. The fix is HTTP/2 on the server side, which is standard practice for any modern deployment.

SSE also doesn't support binary data directly. If you need to send binary payloads, encode them as base64 and decode on the client.

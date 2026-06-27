---
title: "HTTP keeps closing. WebSocket stays open. Here's why that changes everything."
description: "The fundamental difference between HTTP's request-response model and WebSocket's persistent connection, and why persistent connections unlock real-time applications."
pubDate: 2025-03-10
tags: ["WebSocket", "Networking"]
draft: false
---

## How HTTP works

Every HTTP interaction follows the same pattern: client opens a connection, sends a request, server sends a response, connection closes. The connection's lifetime is the duration of one request.

This model is excellent for most of the web. Load a page, fetch some JSON, upload a file -- each is a discrete request/response pair. HTTP/1.1 added keep-alive to reuse connections across multiple requests, and HTTP/2 added multiplexing. But the fundamental model is still request-response: the client asks, the server answers.

The constraint: the server cannot send data to the client unless the client asks first. If the client loaded a page two minutes ago and something changed on the server, the client won't know until it makes another request.

## Polling as a workaround

The common workaround is polling: the client asks every N seconds.

```javascript
// Poll every 5 seconds
setInterval(async () => {
  const response = await fetch('/api/messages/new');
  const messages = await response.json();
  updateMessages(messages);
}, 5000);
```

This works, but it has problems:

- **Latency**: new data arrives up to 5 seconds after it's created
- **Wasted requests**: most polls return "nothing new"
- **Server load**: 1000 clients polling every 5 seconds = 200 requests/second of mostly-empty responses

Long-polling (the client holds the connection open until data arrives) improves latency but is complex to implement correctly and still has per-request overhead.

## WebSocket: a persistent bidirectional channel

WebSocket is a different protocol. After a brief HTTP handshake, the connection upgrades to a persistent TCP channel. Both client and server can send frames at any time. The connection stays open until either side closes it.

```javascript
const ws = new WebSocket('wss://api.example.com/chat');

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'general' }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  displayMessage(message);
};

ws.onclose = () => {
  console.log('Connection closed');
};
```

When a new message arrives on the server, it pushes it directly to all connected clients. No polling. No latency beyond network propagation time. No wasted requests.

## The practical difference

Consider a live auction. A bid comes in. With HTTP polling:

1. Bid is placed (server processes it)
2. Other clients are polling; on average half their interval has elapsed
3. Next poll fires, they see the new bid
4. Average latency: half the poll interval (2.5 seconds at 5s polling)

With WebSocket:

1. Bid is placed (server processes it)
2. Server pushes the new bid to all connected clients
3. Average latency: network propagation time (milliseconds)

For a live auction, a 2.5 second update delay is unusable. For a chat app, a 5 second delay makes the experience feel broken. WebSocket is the correct solution for any feature that requires the server to proactively notify clients.

## When to use each

**Use HTTP** for:
- Loading data when a user navigates to a screen
- Submitting forms
- CRUD operations
- Any interaction where the client initiates and the server responds once

**Use WebSocket** for:
- Chat and messaging
- Live notifications
- Collaborative editing (multiple users editing the same document)
- Real-time dashboards (live metrics, stock tickers)
- Multiplayer games
- Live audio/video transcription

The connection overhead of WebSocket (a persistent TCP socket) is only worth it if you need server-initiated pushes. For ordinary data fetching, HTTP is simpler and more cacheable.

## The mental model shift

HTTP is a vending machine: you put in a request, you get out a response. WebSocket is a phone call: the connection is live, both sides talk when they have something to say, and either side can hang up.

Real-time features require the phone call model.

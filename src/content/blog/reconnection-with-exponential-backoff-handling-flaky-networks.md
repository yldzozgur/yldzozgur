---
title: "Reconnection with exponential backoff: handling flaky networks."
description: "WebSocket connections drop. The reconnection strategy matters: naive immediate reconnection can overload a recovering server. Exponential backoff is the standard solution."
pubDate: 2025-03-20
tags: ["WebSocket", "Networking"]
draft: false
---

## Why immediate reconnection fails

When a WebSocket connection drops -- because of a network hiccup, server restart, or temporary outage -- the client needs to reconnect. The naive approach reconnects immediately, and if that fails, reconnects again, and again.

If a server restarts and 10,000 clients all reconnect within the same second, the server gets a connection storm that can prevent it from starting cleanly. Even if the server is fine, hammering it with connection attempts every 100ms wastes resources on both sides.

Exponential backoff spaces out reconnection attempts: wait 1 second, then 2, then 4, then 8, up to a maximum. The load distributes over time instead of concentrating at a single moment.

## Basic exponential backoff

```javascript
class ReconnectingWebSocket {
  constructor(url) {
    this.url = url;
    this.reconnectDelay = 1000;     // start: 1 second
    this.maxReconnectDelay = 30000; // cap: 30 seconds
    this.reconnectDecay = 2;        // double each attempt
    this.reconnectAttempts = 0;
    this.ws = null;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected');
      this.reconnectDelay = 1000;   // reset on successful connection
      this.reconnectAttempts = 0;
    };

    this.ws.onclose = (event) => {
      if (!event.wasClean) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws.close();
    };
  }

  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(this.reconnectDecay, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }
}
```

The delay sequence: 1s, 2s, 4s, 8s, 16s, 30s, 30s, 30s... (capped at 30 seconds).

## Adding jitter

If many clients disconnect at the same time (a server restart), they'll all start their backoff from the same moment and retry at the same intervals. The reconnection storm is delayed but not prevented.

Jitter adds randomness to the delay, distributing clients across time:

```javascript
scheduleReconnect() {
  this.reconnectAttempts++;
  const base = Math.min(
    this.reconnectDelay * Math.pow(this.reconnectDecay, this.reconnectAttempts - 1),
    this.maxReconnectDelay
  );
  // Add up to 30% random jitter
  const jitter = base * 0.3 * Math.random();
  const delay = base + jitter;

  console.log(`Reconnecting in ${Math.round(delay)}ms`);
  setTimeout(() => this.connect(), delay);
}
```

With 10,000 clients and 30% jitter, a capped 30-second retry distributes connections across a 30-39 second window instead of all arriving at once.

## Handling the message queue

When the connection is down, outgoing messages queue up or are dropped. A simple queue that drains on reconnect:

```javascript
class ReconnectingWebSocket {
  constructor(url) {
    this.url = url;
    this.messageQueue = [];
    // ... other setup
    this.connect();
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      this.messageQueue.push(data);
    }
  }

  onOpen() {
    // Drain the queue
    while (this.messageQueue.length > 0) {
      this.ws.send(this.messageQueue.shift());
    }
  }
}
```

For critical messages (user input, form submissions), queuing is appropriate. For real-time data (cursor positions, live metrics), queuing may deliver stale data -- dropping is often better.

## Clean vs unclean closes

The `close` event has a `wasClean` property. A clean close (`wasClean: true`) means the server sent a proper close frame -- either it intentionally closed the connection or the client closed it. An unclean close indicates a network failure.

Reconnecting on unclean closes and not on clean closes prevents infinite reconnection loops when the server intentionally closes a connection (e.g., authentication failed, session expired).

```javascript
this.ws.onclose = (event) => {
  if (event.wasClean) {
    console.log(`Closed cleanly, code=${event.code}, reason=${event.reason}`);
    // Don't reconnect -- the server intentionally closed
  } else {
    this.scheduleReconnect();
  }
};
```

## Max attempts

For some scenarios, it makes sense to give up after N attempts and show the user an error state:

```javascript
const MAX_ATTEMPTS = 10;

scheduleReconnect() {
  if (this.reconnectAttempts >= MAX_ATTEMPTS) {
    this.onPermanentFailure?.();
    return;
  }
  // ... schedule reconnect
}
```

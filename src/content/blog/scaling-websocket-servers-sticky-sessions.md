---
title: "Scaling WebSocket servers: why sticky sessions aren't the only answer."
description: "WebSockets make horizontal scaling harder than stateless HTTP. Sticky sessions are the simple solution. Redis pub/sub is the scalable one. When each approach is right."
pubDate: 2025-04-07
tags: ["WebSocket", "Networking", "Architecture", "Backend"]
draft: false
---

## The stateful scaling problem

HTTP is largely stateless -- each request carries all the information needed to handle it, and any server can handle any request. This makes horizontal scaling straightforward: add servers behind a load balancer, distribute requests round-robin.

WebSocket connections are stateful. A connected client has an ongoing relationship with a specific server process. The server holds the socket object in memory. If a client connects to Server A and a message is published that should reach them, Server B can't deliver it -- it doesn't have the socket.

## Sticky sessions

The simplest solution is sticky sessions: configure the load balancer to always route a given client to the same server. The client's first request establishes which server "owns" them. Subsequent requests (and the WebSocket upgrade) go to the same server.

```nginx
upstream websocket_servers {
    ip_hash;  # route by client IP -- simple sticky session
    server ws1.internal:8080;
    server ws2.internal:8080;
    server ws3.internal:8080;
}
```

With sticky sessions, the in-memory pub/sub approach works. All clients assigned to a server communicate directly. The problem is server failures: if Server A goes down, all clients on it are disconnected. They reconnect and land on the remaining servers, which have no knowledge of their subscriptions. Clients need to re-subscribe.

Sticky sessions are appropriate for:
- Moderate scale (thousands, not millions of connections)
- Use cases where reconnection + re-subscription is acceptable
- Simple deployments where operational simplicity outweighs perfect availability

## Redis pub/sub for horizontal broadcast

For true horizontal scalability, use a shared message broker. All server instances publish to and subscribe from a central Redis instance. When a message needs to go to clients on any server, it's published to Redis. All servers receive it and deliver it to their local clients.

```javascript
const Redis = require('ioredis');
const { WebSocketServer } = require('ws');

const subscriber = new Redis();
const publisher = new Redis();
const wss = new WebSocketServer({ port: 8080 });

// Each server process tracks its own clients
const localClients = new Map(); // userId -> WebSocket

// Subscribe to the global channel
subscriber.subscribe('broadcast');
subscriber.on('message', (channel, message) => {
  const { targetUserId, payload } = JSON.parse(message);

  // Deliver to local clients if they're connected to this server
  if (targetUserId) {
    const ws = localClients.get(targetUserId);
    if (ws?.readyState === 1) {
      ws.send(payload);
    }
  } else {
    // Broadcast to all local clients
    localClients.forEach(ws => {
      if (ws.readyState === 1) ws.send(payload);
    });
  }
});

wss.on('connection', (ws, request) => {
  const userId = request.user.id;
  localClients.set(userId, ws);

  ws.on('close', () => localClients.delete(userId));
});

// To send a message (from anywhere in the codebase):
function sendToUser(userId, data) {
  publisher.publish('broadcast', JSON.stringify({
    targetUserId: userId,
    payload: JSON.stringify(data),
  }));
}
```

Now any server instance can trigger delivery to any client, regardless of which server they're connected to.

## Channel-based routing

For pub/sub with channels, extend the Redis pattern:

```javascript
// Each server subscribes all its clients' channels to Redis
function subscribeToChannel(ws, channel) {
  localSubscriptions.get(channel)?.add(ws) 
    ?? localSubscriptions.set(channel, new Set([ws]));

  // Subscribe this server process to the Redis channel if not already
  if (!redisSubscriptions.has(channel)) {
    subscriber.subscribe(channel);
    redisSubscriptions.add(channel);
  }
}

// Publish to a channel
function publish(channel, data) {
  publisher.publish(channel, JSON.stringify(data));
}
```

## When to use each approach

**Sticky sessions** when:
- Single-digit server count
- Simplicity matters more than perfect availability
- Reconnection is acceptable and re-subscription is cheap

**Redis pub/sub** when:
- More than a few servers
- Server failure should not cause message loss
- Clients should receive messages regardless of which server they connect to

A third option worth knowing: managed services like Ably, Pusher, and Socket.io's hosted platform handle all of this for you. For large scale, the operational complexity of managing Redis + WebSocket servers often outweighs the cost of a managed service.

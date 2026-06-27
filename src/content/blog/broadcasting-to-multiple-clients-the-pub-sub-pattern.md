---
title: "Broadcasting to multiple clients: the pub/sub pattern."
description: "When a WebSocket server needs to send a message to many clients, pub/sub is the natural model. How to implement channels, subscriptions, and broadcasts in Node.js."
pubDate: 2025-03-27
tags: ["WebSocket", "Networking", "Architecture"]
draft: false
---

## The broadcast requirement

A single WebSocket connection is a pipe between one client and one server. Most real-time features require more: a message sent by one user should be received by many. A chat room, a live dashboard, a collaborative document -- all require broadcasting to a group.

The pub/sub (publish/subscribe) pattern organizes this: clients subscribe to named channels, and publishing to a channel delivers the message to all subscribers.

## In-memory pub/sub with the ws library

For a single server process, a `Map` of channels to subscriber sets is sufficient:

```javascript
const { WebSocketServer } = require('ws');

const wss = new WebSocketServer({ port: 8080 });

// Map of channel name -> Set of WebSocket connections
const channels = new Map();

function subscribe(ws, channel) {
  if (!channels.has(channel)) {
    channels.set(channel, new Set());
  }
  channels.get(channel).add(ws);
}

function unsubscribe(ws, channel) {
  channels.get(channel)?.delete(ws);
}

function broadcast(channel, message, excludeWs = null) {
  const subscribers = channels.get(channel);
  if (!subscribers) return;

  const payload = JSON.stringify(message);
  subscribers.forEach(ws => {
    if (ws !== excludeWs && ws.readyState === WebSocket.OPEN) {
      ws.send(payload);
    }
  });
}

// Clean up when a client disconnects
function unsubscribeAll(ws) {
  channels.forEach(subscribers => subscribers.delete(ws));
}
```

## Handling client subscriptions

Clients send subscription messages to declare which channels they're interested in:

```javascript
wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    const message = JSON.parse(data);

    switch (message.type) {
      case 'subscribe':
        subscribe(ws, message.channel);
        ws.send(JSON.stringify({ type: 'subscribed', channel: message.channel }));
        break;

      case 'unsubscribe':
        unsubscribe(ws, message.channel);
        break;

      case 'publish':
        // Validate the client is allowed to publish to this channel
        broadcast(message.channel, {
          type: 'message',
          channel: message.channel,
          payload: message.payload,
          from: ws.userId,
        }, ws); // exclude sender
        break;
    }
  });

  ws.on('close', () => {
    unsubscribeAll(ws);
  });
});
```

## Client-side subscription

```javascript
const ws = new WebSocket('wss://api.example.com');

ws.onopen = () => {
  // Subscribe to a channel on connection
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'room:42' }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'message' && message.channel === 'room:42') {
    displayChatMessage(message.payload);
  }
};

// Send a message to the room
function sendMessage(text) {
  ws.send(JSON.stringify({
    type: 'publish',
    channel: 'room:42',
    payload: { text },
  }));
}
```

## Channel naming conventions

A common convention is hierarchical channel names:

- `room:42` -- a chat room with ID 42
- `user:7` -- private messages for user 7
- `dashboard:metrics` -- live metrics for a dashboard
- `game:xyz:state` -- game state for a specific game session

The naming is arbitrary -- it's just a string key in the channels Map. Namespacing with colons makes it easy to identify the type of channel.

## Room presence tracking

Track who's in each room by maintaining a set of user IDs alongside the socket set:

```javascript
const rooms = new Map();
// rooms: Map<channelName, { sockets: Set<WebSocket>, users: Set<userId> }>

function joinRoom(ws, roomId, userId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, { sockets: new Set(), users: new Set() });
  }
  const room = rooms.get(roomId);
  room.sockets.add(ws);
  room.users.add(userId);

  // Notify others that someone joined
  broadcast(roomId, { type: 'user_joined', userId }, ws);
}
```

## Scaling beyond a single process

This in-memory approach works on one server process. When you scale horizontally (multiple server instances), clients on different processes can't see each other's messages. That requires a shared pub/sub broker -- Redis Pub/Sub is the standard solution. The server subscribes to Redis channels and forwards messages to local WebSocket clients.

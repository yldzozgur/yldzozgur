---
title: "ws vs Socket.io: when the abstraction is worth the overhead."
description: "ws is a minimal WebSocket library. Socket.io adds rooms, auto-reconnection, fallbacks, and events on top. What you get from each and when the tradeoffs make sense."
pubDate: 2025-04-10
tags: ["WebSocket", "Networking", "Node.js"]
draft: false
---

## ws: minimal and explicit

`ws` is a Node.js WebSocket library that implements the WebSocket protocol and nothing else. You get a server that accepts connections and an interface to send and receive messages.

```javascript
const { WebSocketServer } = require('ws');

const wss = new WebSocketServer({ port: 8080 });

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    const message = JSON.parse(data);
    // Handle message
  });

  ws.send(JSON.stringify({ type: 'welcome' }));
});
```

Everything else -- rooms, reconnection, event routing, authentication -- you build yourself. The library is small (~25KB), fast, and has no opinion about your application structure.

**What ws gives you:**
- WebSocket server and client
- Text and binary frame support
- Ping/pong
- Per-connection `readyState`

**What ws does not give you:**
- Rooms or channels (you build with Map/Set)
- Auto-reconnection (you build with retry logic)
- Event namespacing (you build with a message type field)
- Fallback to long-polling
- Broadcasting helpers beyond `wss.clients`

## Socket.io: convention and features

Socket.io is built on top of WebSocket (and falls back to long-polling for environments without WebSocket support). It adds a structured event model, rooms, namespaces, and reconnection.

```javascript
const { Server } = require('socket.io');
const httpServer = require('http').createServer();

const io = new Server(httpServer, {
  cors: { origin: '*' }
});

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Event-based message handling
  socket.on('join_room', (roomId) => {
    socket.join(roomId);
  });

  socket.on('chat_message', ({ roomId, text }) => {
    // Broadcast to everyone in the room
    io.to(roomId).emit('chat_message', { text, from: socket.id });
  });
});
```

Client side:

```javascript
import { io } from 'socket.io-client';

const socket = io('https://api.example.com');

socket.on('connect', () => {
  socket.emit('join_room', 'general');
});

socket.on('chat_message', ({ text, from }) => {
  displayMessage({ text, from });
});

function sendMessage(text) {
  socket.emit('chat_message', { roomId: 'general', text });
}
```

**What Socket.io gives you:**
- Event-based API (emit/on) instead of raw message parsing
- Rooms (built-in pub/sub)
- Namespaces (logical separation within one server)
- Auto-reconnection with exponential backoff
- Acknowledgements (confirm the server received a message)
- Long-polling fallback
- Broadcast helpers (`io.to(room).emit(...)`)

**What Socket.io costs you:**
- Custom protocol on top of WebSocket -- Socket.io clients and plain WebSocket clients are not compatible
- Larger bundle (~40KB gzipped on the client)
- Slightly more overhead per message (framing, event encoding)

## The compatibility issue

Socket.io uses a custom encoding format. A plain WebSocket client cannot connect to a Socket.io server and vice versa. If you need to support WebSocket clients that aren't Socket.io (mobile apps using the standard WebSocket API, other languages), Socket.io is the wrong choice unless you explicitly support both.

`ws` uses standard WebSocket protocol -- any WebSocket client can connect.

## When to choose each

**Choose ws when:**
- You need to support non-JavaScript clients (mobile apps, other languages)
- You want minimal dependencies and full control
- Your real-time protocol is already well-defined
- You're building infrastructure and need predictable performance

**Choose Socket.io when:**
- You're building a JavaScript-to-JavaScript application (Next.js frontend to Node.js backend)
- You want rooms and namespaces without building them
- Reconnection handling out-of-the-box matters
- You're prototyping and want to move fast

The Socket.io abstraction pays for itself in a chat application or collaborative tool where the room/event model is exactly what you need. For a custom binary protocol or a mobile client in Swift, `ws` with a handcrafted message layer is the better foundation.

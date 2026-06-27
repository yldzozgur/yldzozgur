---
title: "Heartbeat / ping-pong: detecting dead WebSocket connections."
description: "A WebSocket connection can appear open while the underlying TCP connection is gone. Ping-pong heartbeats detect these zombie connections before they cause problems."
pubDate: 2025-03-24
tags: ["WebSocket", "Networking"]
draft: false
---

## The zombie connection problem

TCP connections can die silently. A phone loses network signal, a router reboots, a NAT table entry expires -- the connection is gone, but neither the client nor the server has sent a FIN packet to notify the other side.

In this state, the WebSocket connection appears `OPEN` on both sides. The server may continue broadcasting to this client. Messages are lost silently. The server holds a socket object consuming resources for a connection that cannot deliver data.

The OS has a TCP keepalive mechanism, but it typically fires after hours of silence -- far too slow for real-time applications.

## The WebSocket ping/pong mechanism

WebSocket defines protocol-level ping and pong control frames. A sender sends a ping. The receiver must respond with a pong containing the same payload. This is separate from the application data frames.

In browser WebSockets, the JavaScript API doesn't expose ping/pong directly -- the browser handles them internally. In server-to-server or server implementations, you manage them explicitly.

## Server-side heartbeat (Node.js ws library)

```javascript
const { WebSocketServer } = require('ws');

const wss = new WebSocketServer({ port: 8080 });

function heartbeat() {
  this.isAlive = true;
}

wss.on('connection', (ws) => {
  ws.isAlive = true;
  ws.on('pong', heartbeat);
});

// Ping all clients every 30 seconds
const interval = setInterval(() => {
  wss.clients.forEach((ws) => {
    if (ws.isAlive === false) {
      // Didn't respond to last ping -- terminate
      console.log('Terminating dead connection');
      return ws.terminate();
    }

    ws.isAlive = false;
    ws.ping();
  });
}, 30000);

wss.on('close', () => clearInterval(interval));
```

Every 30 seconds:
1. Mark all connections as "suspected dead" (`isAlive = false`)
2. Send a ping to each
3. If a client receives the ping, it automatically sends back a pong
4. The pong handler (`heartbeat`) marks the connection as alive again
5. On the next cycle, connections that didn't respond are terminated

Connections that are truly gone (no pong received within the interval) are terminated. The server's resources are freed.

## Client-side application-level heartbeat

Browsers handle WebSocket pings from the server automatically. But in React Native, or for application-level heartbeats, you can implement it at the message level:

```javascript
class HeartbeatWebSocket {
  constructor(url) {
    this.url = url;
    this.heartbeatInterval = 30000;
    this.heartbeatTimeout = 5000; // time to wait for pong
    this.pingTimer = null;
    this.pongTimer = null;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'pong') {
        // Received pong, connection is alive
        clearTimeout(this.pongTimer);
      } else {
        this.handleMessage(data);
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
    };
  }

  startHeartbeat() {
    this.pingTimer = setInterval(() => {
      if (this.ws.readyState !== WebSocket.OPEN) return;

      this.ws.send(JSON.stringify({ type: 'ping' }));

      // If no pong within 5 seconds, close and reconnect
      this.pongTimer = setTimeout(() => {
        console.log('Pong timeout -- reconnecting');
        this.ws.close();
        this.connect();
      }, this.heartbeatTimeout);
    }, this.heartbeatInterval);
  }

  stopHeartbeat() {
    clearInterval(this.pingTimer);
    clearTimeout(this.pongTimer);
  }
}
```

## Server-side pong handler for application-level heartbeat

```javascript
wss.on('connection', ws => {
  ws.on('message', (data) => {
    const message = JSON.parse(data);

    if (message.type === 'ping') {
      ws.send(JSON.stringify({ type: 'pong' }));
      return;
    }

    handleMessage(ws, message);
  });
});
```

## Choosing the interval

A 30-second heartbeat interval works for most applications. Shorter intervals detect dead connections faster but add overhead. Longer intervals are cheaper but leave zombie connections open longer.

For mobile apps where battery matters, avoid intervals shorter than 30 seconds. For server-to-server connections where latency detection matters, 10-15 seconds is reasonable.

The timeout (how long to wait for a pong) should be shorter than the interval -- 5 seconds for a 30-second interval gives the network a reasonable window without overlapping with the next ping cycle.

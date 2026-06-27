---
title: "The WebSocket handshake: what's happening in that HTTP upgrade."
description: "WebSocket connections start as HTTP requests. The upgrade handshake is the mechanism that switches protocols. What each header means and how the switch works."
pubDate: 2025-03-13
tags: ["WebSocket", "Networking", "HTTP"]
draft: false
---

## Why the handshake starts as HTTP

WebSocket doesn't have its own connection mechanism. It reuses HTTP to establish the initial connection, then upgrades that connection to the WebSocket protocol. This design was intentional: it allows WebSocket to work on port 80 and 443 (the same ports as HTTP/HTTPS), passes through existing firewalls and proxies that understand HTTP, and lets the handshake carry authentication data in standard HTTP headers.

## The client's opening request

A WebSocket connection starts with a standard HTTP GET request with specific headers:

```
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: https://example.com
```

Breaking these down:

**`Upgrade: websocket`**: tells the server the client wants to switch protocols. This is the core of the upgrade mechanism.

**`Connection: Upgrade`**: required alongside `Upgrade`. Tells intermediate proxies that this connection upgrade request should not be forwarded as a normal request.

**`Sec-WebSocket-Key`**: a base64-encoded random 16-byte value, generated fresh for each connection. This is not for security in the cryptographic sense -- it's for preventing cache poisoning by confirming the server actually understands WebSocket.

**`Sec-WebSocket-Version: 13`**: specifies the WebSocket protocol version. Version 13 is the current standard (RFC 6455).

## The server's response

If the server supports WebSocket on that endpoint, it responds with HTTP 101:

```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

**101 Switching Protocols**: the status code that means "I'm accepting the protocol upgrade."

**`Sec-WebSocket-Accept`**: the server takes the `Sec-WebSocket-Key` from the client, concatenates it with the fixed GUID string `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`, hashes the result with SHA-1, and base64-encodes it. The client verifies this computation to confirm the server understood the handshake.

After this exchange, the HTTP connection is "upgraded." The same TCP socket that carried the HTTP request now carries WebSocket frames. No new connection is established.

## WebSocket subprotocols

During the handshake, the client can request a subprotocol:

```
Sec-WebSocket-Protocol: chat, superchat
```

The server picks one and confirms it:

```
Sec-WebSocket-Protocol: chat
```

Subprotocols are application-level agreements about message format -- they're just strings that both sides recognize. They don't change anything at the transport level.

## Extensions

WebSocket supports extensions, negotiated in the handshake:

```
Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
```

`permessage-deflate` compresses message payloads. If the server supports it and accepts the extension, subsequent frames are compressed, saving bandwidth for text-heavy applications.

## Viewing the handshake

In browser DevTools, go to the Network tab and filter by WS. Click a WebSocket connection to see the Headers tab -- it shows the full handshake request and response. The Messages tab shows each frame exchanged after the handshake.

In Node.js server code (using the `ws` library), the upgrade event fires for each new connection:

```javascript
const { WebSocketServer } = require('ws');
const wss = new WebSocketServer({ port: 8080 });

wss.on('connection', function(ws, request) {
  // request is the original HTTP upgrade request
  console.log('Handshake headers:', request.headers);
  console.log('Client IP:', request.socket.remoteAddress);
});
```

The `request` object is the full Node.js `IncomingMessage` from the HTTP upgrade request. Headers like `Authorization`, cookies, and query parameters in the URL are accessible here -- this is where WebSocket authentication happens.

## WSS (WebSocket Secure)

`wss://` uses the same upgrade mechanism over a TLS connection. The TLS handshake happens first (establishing the encrypted channel), then the WebSocket upgrade happens inside the encrypted channel. From the server's perspective, handling `wss://` requires a TLS certificate, the same as HTTPS.

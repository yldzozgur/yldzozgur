---
title: "Text vs binary frames: choosing the right format for real-time data."
description: "WebSocket supports text and binary frames. When to use each, what the tradeoffs are, and how to handle both on the client and server."
pubDate: 2025-03-17
tags: ["WebSocket", "Networking"]
draft: false
---

## WebSocket frames

The WebSocket protocol defines two primary data frame types: text and binary. Each `send()` call produces one frame (or multiple frames for large messages, via fragmentation). The receiver knows which type to expect from the frame header.

## Text frames

Text frames carry UTF-8 encoded strings. This is the most common choice for application-level messaging.

```javascript
// Client sending
ws.send(JSON.stringify({ type: 'chat_message', text: 'Hello', userId: 42 }));

// Client receiving
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleMessage(message);
};
```

JSON over text frames is the default pattern for most WebSocket applications. It's readable, debuggable, and universally supported.

**When text makes sense:**
- Application events and commands (chat messages, user actions, state updates)
- Structured data where human readability during debugging is valuable
- Any payload where parsing cost is negligible compared to the business logic

## Binary frames

Binary frames carry raw bytes -- ArrayBuffer in the browser, Buffer in Node.js. No encoding overhead, no JSON parsing.

```javascript
// Client: configure to receive binary as ArrayBuffer
ws.binaryType = 'arraybuffer';

ws.onmessage = (event) => {
  if (event.data instanceof ArrayBuffer) {
    const buffer = new Uint8Array(event.data);
    processAudioData(buffer);
  }
};

// Sending binary
const audioBuffer = new Uint8Array(recordedAudio);
ws.send(audioBuffer.buffer);
```

**When binary makes sense:**
- Audio or video data
- Image data
- Large payloads where JSON encoding overhead matters
- Situations where you're using a binary serialization format like MessagePack or Protocol Buffers

## MessagePack: binary with structure

Pure binary frames are efficient but lose the self-describing nature of JSON. A middle ground is MessagePack -- a binary serialization format that represents the same data types as JSON but in a more compact binary encoding.

```javascript
import { encode, decode } from '@msgpack/msgpack';

// Sending structured data in binary
const data = { type: 'sensor_reading', value: 23.4, timestamp: Date.now() };
ws.send(encode(data));

// Receiving
ws.binaryType = 'arraybuffer';
ws.onmessage = (event) => {
  const data = decode(new Uint8Array(event.data));
};
```

For high-frequency numerical data (IoT sensors, game state updates, financial ticks), MessagePack reduces payload size by 30-40% compared to JSON.

## Mixing types on one connection

A single WebSocket connection can send both text and binary frames. The receiver detects the type from the frame header. This is useful for a protocol that mixes control messages (text/JSON) with data payloads (binary):

```javascript
ws.onmessage = (event) => {
  if (typeof event.data === 'string') {
    // Control message
    const cmd = JSON.parse(event.data);
    handleCommand(cmd);
  } else {
    // Binary payload
    const buffer = new Uint8Array(event.data);
    handleBinaryData(buffer);
  }
};
```

## Server-side handling (Node.js ws library)

```javascript
const { WebSocketServer } = require('ws');
const wss = new WebSocketServer({ port: 8080 });

wss.on('connection', ws => {
  ws.on('message', (data, isBinary) => {
    if (isBinary) {
      // data is a Buffer
      processBuffer(data);
    } else {
      // data is a Buffer containing UTF-8 text
      const message = JSON.parse(data.toString());
      handleMessage(message);
    }
  });
});
```

The `ws` library passes an `isBinary` flag as the second argument to the message handler.

## The practical choice

For most application-level messaging, text frames with JSON are the right default. The encoding overhead is negligible for typical message sizes, and the debuggability advantage is real -- you can read the messages in browser DevTools or network logs without a decoder.

Switch to binary when:
- Messages are large (above a few KB) and sent frequently
- You're transmitting inherently binary data (audio, images)
- You've profiled and identified serialization as a bottleneck

Start with text/JSON, measure, and optimize with binary if the data shows a real problem.

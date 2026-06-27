---
title: "HTTP streaming: chunked transfer and what it enables."
description: "Chunked transfer encoding lets servers send response data before they know the total size. Here's how it works and what patterns it unlocks."
pubDate: 2026-05-18
tags: ["HTTP", "Node.js"]
draft: false
---

A standard HTTP response sends a `Content-Length` header telling the client how many bytes to expect. This requires the server to know the full response size before sending anything. Chunked transfer encoding removes that requirement — the server can start sending data and keep sending until it's done, without knowing the total size upfront.

## How chunked encoding works

When a server responds with `Transfer-Encoding: chunked`, the response body is split into chunks. Each chunk is preceded by its size in hexadecimal, followed by the data, followed by a CRLF. A zero-length chunk signals the end.

```
HTTP/1.1 200 OK
Content-Type: application/json
Transfer-Encoding: chunked

1a\r\n
{"users":[{"id":1,"name":\r\n
10\r\n
"Alice"}]}\r\n
0\r\n
\r\n
```

The browser and HTTP clients reassemble the chunks transparently. From the application code's perspective, you're reading a stream.

## Streaming in Node.js

Node.js streams align naturally with chunked transfer:

```javascript
import { createReadStream } from 'fs';
import http from 'http';

const server = http.createServer((req, res) => {
  if (req.url === '/large-file') {
    res.setHeader('Content-Type', 'application/octet-stream');
    // No Content-Length — Node.js uses chunked transfer automatically
    const stream = createReadStream('./large-dataset.json');
    stream.pipe(res);
  }
});
```

For database results, instead of loading everything into memory and sending at once, you can stream rows as they arrive:

```javascript
app.get('/export', async (req, res) => {
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="export.csv"');

  res.write('id,email,name,created_at\n');

  // Stream rows from the database cursor
  const cursor = db.query('SELECT id, email, name, created_at FROM users ORDER BY id');

  cursor.on('row', (row) => {
    res.write(`${row.id},${row.email},${row.name},${row.created_at}\n`);
  });

  cursor.on('end', () => res.end());
  cursor.on('error', (err) => {
    console.error(err);
    res.end();
  });
});
```

This handles tables with millions of rows without loading them all into memory.

## Streaming JSON with newline-delimited format

JSON isn't inherently streamable because a parser needs the full document to validate bracket matching. Newline-delimited JSON (NDJSON) solves this — each line is a complete JSON object:

```javascript
app.get('/stream-events', async (req, res) => {
  res.setHeader('Content-Type', 'application/x-ndjson');

  const events = getEventStream(); // returns an async generator

  for await (const event of events) {
    // Each line is a complete JSON object
    res.write(JSON.stringify(event) + '\n');
  }

  res.end();
});
```

Client-side, you read the response as a stream and process each line:

```javascript
const response = await fetch('/stream-events');
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop() ?? ''; // Keep incomplete line in buffer

  for (const line of lines) {
    if (line.trim()) {
      const event = JSON.parse(line);
      processEvent(event);
    }
  }
}
```

## AI response streaming

The pattern behind AI chat interfaces is the same mechanism. When a language model generates tokens, you stream them to the client as they're produced rather than waiting for the full response:

```typescript
// Next.js route streaming an AI response
export async function POST(request: Request) {
  const { prompt } = await request.json();

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      // Each token gets written as it arrives
      for await (const chunk of aiModel.stream(prompt)) {
        controller.enqueue(encoder.encode(chunk.text));
      }

      controller.close();
    },
  });

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
```

## Backpressure

Streaming without backpressure can cause memory problems. If you write to a response faster than the client can consume, Node.js buffers the data in memory. The `drain` event signals that the buffer has cleared:

```javascript
function writeWithBackpressure(res, data, callback) {
  const canContinue = res.write(data);
  if (canContinue) {
    callback();
  } else {
    res.once('drain', callback);
  }
}
```

Node.js streams in pipelines handle backpressure automatically — another reason to prefer `stream.pipe(res)` over manual `write` calls when the source is a stream.

Chunked transfer is most valuable when the total response size is unknown, very large, or when getting data to the client faster matters more than knowing the total size. For typical API responses with small, bounded payloads, it adds complexity without meaningful benefit.

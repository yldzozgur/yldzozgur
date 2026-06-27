---
title: "Latency budget in a real-time AI app: where the milliseconds go."
description: "How to break down end-to-end latency in a real-time AI application and identify which hops to optimize first."
pubDate: 2025-05-15
tags: ["AI", "WebSocket"]
draft: false
---

When a user sends a message and nothing happens for three seconds, that feels broken. But where did those three seconds go? Without measuring each segment of the request path, optimization is guesswork.

## Defining a latency budget

A latency budget is the maximum acceptable time for an end-to-end operation, broken into allocations for each stage. For a chat application targeting 1500ms to first token rendered on screen:

| Stage | Budget |
|-------|--------|
| Client to server (network) | 50ms |
| Auth middleware | 10ms |
| Context retrieval (DB/cache) | 100ms |
| LLM first token | 800ms |
| Server to client (network + streaming setup) | 100ms |
| Client render | 50ms |
| **Total** | **1110ms** |

That leaves 390ms of headroom, which sounds comfortable until you add logging, error handling, and the reality that P99 latency is 3-4x the median.

## Instrumenting each hop

You cannot manage what you do not measure. Add timestamps at each boundary:

```javascript
async function handleChatRequest(req, res) {
  const timings = { start: Date.now() };

  // Auth
  const user = await authenticate(req);
  timings.auth = Date.now();

  // Context retrieval
  const context = await fetchUserContext(user.id);
  timings.context = Date.now();

  // LLM call - track first token separately
  const stream = await client.chat.completions.create({
    model: "gpt-4o",
    messages: buildMessages(context, req.body.message),
    stream: true
  });
  timings.llmCallSent = Date.now();

  let firstToken = true;
  for await (const chunk of stream) {
    if (firstToken) {
      timings.firstToken = Date.now();
      firstToken = false;
    }
    const content = chunk.choices[0]?.delta?.content ?? "";
    if (content) res.write(`data: ${JSON.stringify({ content })}\n\n`);
  }
  timings.llmComplete = Date.now();
  res.end();

  // Log the breakdown
  console.log({
    authMs: timings.auth - timings.start,
    contextMs: timings.context - timings.auth,
    llmSetupMs: timings.llmCallSent - timings.context,
    ttftMs: timings.firstToken - timings.llmCallSent, // time to first token
    generationMs: timings.llmComplete - timings.firstToken,
    totalMs: timings.llmComplete - timings.start
  });
}
```

TTFT (time to first token) is the most important number for perceived responsiveness. Users tolerate slow generation better than they tolerate a blank screen.

## WebSocket vs HTTP streaming

For real-time AI apps, the transport choice affects latency:

**HTTP with Server-Sent Events (SSE)**: Simple, works over HTTP/1.1, supported natively by browsers. Each request opens a connection, the server streams events, the connection closes. Overhead per request: one TCP handshake, optionally one TLS handshake.

**WebSocket**: Persistent connection, lower per-message overhead once established. Better for bidirectional communication (chat, voice). The initial handshake takes one round trip more than a plain HTTP request.

For a chat interface where the user sends a message and waits, SSE is simpler and has comparable latency. For voice pipelines where audio is flowing continuously in both directions, WebSocket is the right choice.

```javascript
// SSE setup
app.get("/stream", (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  // stream events...
});

// WebSocket setup with ws library
const wss = new WebSocketServer({ port: 8080 });
wss.on("connection", (ws) => {
  ws.on("message", async (data) => {
    const response = await getAIResponse(data.toString());
    ws.send(JSON.stringify({ type: "chunk", content: response }));
  });
});
```

## Where latency hides

**Cold starts**: If your server is serverless, the first request after inactivity includes function initialization. This can add 500ms to 2 seconds. Warm the function with a scheduled ping, or use an always-on server for latency-sensitive paths.

**Context retrieval**: Fetching chat history from a database before every LLM call is a common hidden cost. Cache the last N messages in memory or Redis keyed to the session.

**Token count**: Longer prompts mean more tokens for the model to process before generating. Summarize old conversation history instead of sending the full log.

**Model selection**: GPT-4o mini has roughly 2-3x lower TTFT than GPT-4o at the cost of response quality. Route simple queries to the smaller model.

**Region mismatch**: If your server is in us-east-1 but your AI API endpoint is optimized for us-west-2, you're adding a cross-region hop on every request. Check which regions your AI provider's APIs are physically closest to.

## Perceived vs actual latency

A spinner that appears immediately makes a 1.5-second wait feel shorter than a blank screen for 800ms. Optimistic UI patterns matter:

1. Show the user's message immediately on send
2. Show a typing indicator within 100ms of send
3. Start rendering the streaming response character by character

Streaming to the client and rendering tokens as they arrive converts a "waiting for response" experience into a "watching it think" experience. The total time is the same; the perceived responsiveness is completely different.

Track P50, P90, and P99 latency separately. A mean of 800ms with a P99 of 5 seconds means a significant fraction of your users are having a bad experience that your average hides.

---
title: "Streaming LLM responses: why waiting for the full answer feels broken."
description: "LLMs generate tokens one at a time. Streaming sends them as they're produced instead of waiting for completion. How to implement streaming with the OpenAI API and handle it on the client."
pubDate: 2025-04-28
tags: ["AI", "OpenAI"]
draft: false
---

## Why non-streaming feels slow

A non-streaming LLM response waits until the model has generated every token before sending anything. For a 500-word response at typical generation speeds, that's 5-15 seconds of silence before the user sees anything.

Users have been trained by typewriter animations, loading spinners, and real-time search suggestions to expect progressive feedback. A blank screen that suddenly fills with text feels like a bug.

Streaming sends tokens as they're generated. The first token arrives in ~500ms. The user sees text appearing character by character. Even if the total time is the same, streaming feels significantly faster.

## Server-side streaming with the OpenAI SDK

```javascript
import OpenAI from 'openai';

const openai = new OpenAI();

const stream = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Explain how neural networks work.' }],
  stream: true,
});

for await (const chunk of stream) {
  const delta = chunk.choices[0]?.delta?.content;
  if (delta) {
    process.stdout.write(delta); // or send to client
  }
}
```

Each `chunk` contains a `delta` with the incremental text. The loop ends when the stream closes.

## Streaming to a browser client

The standard approach is Server-Sent Events (SSE) over HTTP. The browser's `EventSource` API handles SSE natively:

```javascript
// Express server endpoint
app.post('/api/chat', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const stream = await openai.chat.completions.create({
    model: 'gpt-4o',
    messages: req.body.messages,
    stream: true,
  });

  for await (const chunk of stream) {
    const delta = chunk.choices[0]?.delta?.content;
    if (delta) {
      res.write(`data: ${JSON.stringify({ text: delta })}\n\n`);
    }
  }

  res.write('data: [DONE]\n\n');
  res.end();
});
```

Client:

```javascript
const eventSource = new EventSource('/api/chat');

eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
    return;
  }
  const { text } = JSON.parse(event.data);
  appendToMessage(text); // update the UI incrementally
};
```

## Using the Vercel AI SDK

For React applications, the Vercel AI SDK abstracts the streaming plumbing:

```javascript
// app/api/chat/route.ts (Next.js App Router)
import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

export async function POST(req) {
  const { messages } = await req.json();

  const result = streamText({
    model: openai('gpt-4o'),
    messages,
  });

  return result.toDataStreamResponse();
}
```

```javascript
// React component
import { useChat } from 'ai/react';

function ChatInterface() {
  const { messages, input, handleInputChange, handleSubmit } = useChat();

  return (
    <div>
      {messages.map(m => (
        <div key={m.id}>
          <strong>{m.role}:</strong> {m.content}
        </div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
```

`useChat` handles the streaming, updating `messages` in real time as tokens arrive.

## Handling streaming in React state

For custom implementations, accumulate the streaming text in state:

```javascript
const [response, setResponse] = useState('');
const [isStreaming, setIsStreaming] = useState(false);

async function sendMessage(userMessage) {
  setIsStreaming(true);
  setResponse('');

  const res = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message: userMessage }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value, { stream: true });
    setResponse(prev => prev + text);
  }

  setIsStreaming(false);
}
```

## What streaming can't do

Streaming doesn't work with Structured Outputs (JSON schema mode) -- you need the complete response before it can be validated against a schema. For structured output use cases, non-streaming is required, and you should communicate progress differently (a loading spinner, not incremental text).

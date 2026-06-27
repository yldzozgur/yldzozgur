---
title: "Gemini vs OpenAI: the API differences that matter when you use both."
description: "A practical comparison of the Gemini and OpenAI APIs covering authentication, message format, tool calling, and streaming."
pubDate: 2025-05-05
tags: ["AI"]
draft: false
---

If you have worked with the OpenAI API and then picked up Gemini, or vice versa, the conceptual model is similar enough to feel familiar but different enough to cause bugs. Here are the differences that actually bite you.

## Authentication and SDK setup

OpenAI uses a single API key passed via the `Authorization` header. The official Node SDK handles this automatically:

```javascript
import OpenAI from "openai";
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
```

Gemini's Google AI SDK also uses a single key:

```javascript
import { GoogleGenerativeAI } from "@google/generative-ai";
const genai = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genai.getGenerativeModel({ model: "gemini-1.5-pro" });
```

If you're using Vertex AI instead of Google AI Studio, authentication switches to Application Default Credentials (ADC) and the endpoint changes. That's a meaningful architectural decision to make early.

## Message structure

OpenAI uses a flat array of messages with `role` and `content`:

```javascript
const messages = [
  { role: "system", content: "You are a helpful assistant." },
  { role: "user", content: "Explain closures." }
];
```

Gemini separates the system instruction from the conversation history:

```javascript
const model = genai.getGenerativeModel({
  model: "gemini-1.5-pro",
  systemInstruction: "You are a helpful assistant."
});

const chat = model.startChat({
  history: [
    { role: "user", parts: [{ text: "Explain closures." }] }
  ]
});
```

The `parts` array inside each message is the key difference. Gemini supports multimodal content natively in the parts format -- text, images, and function responses all go in that array. OpenAI uses a different content array format for multimodal inputs.

## Roles

OpenAI roles: `system`, `user`, `assistant`, `tool`.

Gemini roles: `user`, `model`. There is no `system` role in the history. The system instruction is set at model initialization. Function responses go into a `user` turn with a `functionResponse` part.

This means you cannot naively map between the two. An OpenAI `assistant` message becomes a Gemini `model` message. An OpenAI `tool` result becomes a Gemini `user` message with a function response part.

## Tool calling format

OpenAI tool definition:

```javascript
{
  type: "function",
  function: {
    name: "get_weather",
    description: "...",
    parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] }
  }
}
```

Gemini tool definition:

```javascript
{
  functionDeclarations: [
    {
      name: "get_weather",
      description: "...",
      parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] }
    }
  ]
}
```

The schema shape inside `parameters` is similar but Gemini groups multiple functions under one `functionDeclarations` array per tool object. OpenAI treats each function as a separate item in the `tools` array.

Detecting a tool call also differs. OpenAI: check `response.choices[0].message.tool_calls`. Gemini: check `response.response.functionCalls()`.

## Streaming

OpenAI streaming with the Node SDK:

```javascript
const stream = await client.chat.completions.create({
  model: "gpt-4o",
  messages,
  stream: true
});

for await (const chunk of stream) {
  const delta = chunk.choices[0]?.delta?.content ?? "";
  process.stdout.write(delta);
}
```

Gemini streaming:

```javascript
const result = await model.generateContentStream(prompt);

for await (const chunk of result.stream) {
  const text = chunk.text();
  process.stdout.write(text);
}
```

Gemini's `chunk.text()` is a method call, not a property access. This trips up developers copying patterns from OpenAI code.

## Token counting

OpenAI includes token usage in every response under `response.usage`. You get `prompt_tokens` and `completion_tokens`.

Gemini includes `usageMetadata` with `promptTokenCount` and `candidatesTokenCount`. It also exposes a `countTokens` method you can call before generation to estimate cost.

## Context windows and pricing model

Both providers offer large context windows, but the pricing tiers differ. Gemini 1.5 Pro has a 1M token context window and prices change at different breakpoints than GPT-4o. If you're building something that passes large documents, check the per-million-token pricing for the specific context lengths you're using.

## Error shapes

OpenAI errors are typed exceptions with a `.status` code and `.error.message`. Gemini errors come back as standard HTTP errors or SDK-specific `GoogleGenerativeAIError` objects. If you have unified error handling middleware, you will need adapter logic for each SDK.

The biggest operational difference: OpenAI has well-established rate limit headers (`x-ratelimit-remaining-tokens`, etc.) that many libraries read automatically. Gemini's rate limit signaling is less standardized at this writing, which matters for building retry logic.

When you're supporting both APIs, the cleanest approach is a thin adapter layer that normalizes inputs and outputs to your own internal schema. Passing raw SDK objects through your application makes the differences impossible to contain.

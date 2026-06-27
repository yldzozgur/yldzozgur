---
title: "JSON mode in the OpenAI API: getting structured output you can actually use."
description: "Getting consistent, parseable JSON from LLMs requires more than asking nicely. JSON mode, structured outputs, and the patterns that make LLM output reliable."
pubDate: 2025-04-24
tags: ["AI", "OpenAI"]
draft: false
---

## The problem with asking for JSON

Asking an LLM to "respond in JSON" sometimes works and sometimes returns JSON wrapped in a markdown code block, or JSON with a brief explanation prepended, or JSON with trailing comments that break parsing. The output is inconsistent.

For production applications that need to parse the response programmatically, inconsistency is a bug.

## JSON mode

The OpenAI API has a `response_format` parameter that enforces JSON output:

```javascript
const response = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [
    {
      role: 'system',
      content: 'Extract the event details from the user\'s message. Return a JSON object.',
    },
    {
      role: 'user',
      content: 'I have a meeting with Sarah on Friday at 3pm about the Q3 budget.',
    },
  ],
  response_format: { type: 'json_object' },
});

const data = JSON.parse(response.choices[0].message.content);
// { "title": "Meeting with Sarah", "date": "Friday", "time": "3:00 PM", "topic": "Q3 budget" }
```

With `json_object` mode, the API guarantees valid JSON in the response. It will never return text outside of a JSON object. The response will always be parseable with `JSON.parse()`.

**Important caveat**: the system prompt must mention JSON. The API requires the word "JSON" in the system or user message when JSON mode is enabled, or it returns an error.

## Structured Outputs (schema enforcement)

JSON mode guarantees valid JSON but not a specific shape. Structured Outputs (available on newer models) go further -- you provide a JSON Schema and the API guarantees the response matches it exactly.

```javascript
const response = await openai.chat.completions.create({
  model: 'gpt-4o-2024-08-06',
  messages: [
    {
      role: 'user',
      content: 'I have a meeting with Sarah on Friday at 3pm about the Q3 budget.',
    },
  ],
  response_format: {
    type: 'json_schema',
    json_schema: {
      name: 'event_extraction',
      strict: true,
      schema: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          date: { type: 'string' },
          time: { type: 'string' },
          attendees: {
            type: 'array',
            items: { type: 'string' },
          },
          topic: { type: 'string' },
        },
        required: ['title', 'date', 'time', 'attendees', 'topic'],
        additionalProperties: false,
      },
    },
  },
});
```

With `strict: true`, the response is guaranteed to have exactly the specified fields and types. No extra fields, no missing required fields.

## The OpenAI SDK's `parse` helper

The TypeScript SDK has a `.beta.chat.completions.parse()` method that combines structured outputs with Zod schema validation:

```typescript
import OpenAI from 'openai';
import { zodResponseFormat } from 'openai/helpers/zod';
import { z } from 'zod';

const EventSchema = z.object({
  title: z.string(),
  date: z.string(),
  time: z.string(),
  attendees: z.array(z.string()),
  topic: z.string(),
});

const completion = await openai.beta.chat.completions.parse({
  model: 'gpt-4o-2024-08-06',
  messages: [
    { role: 'user', content: 'Meeting with Sarah Friday 3pm about Q3 budget' },
  ],
  response_format: zodResponseFormat(EventSchema, 'event'),
});

const event = completion.choices[0].message.parsed;
// event is typed as EventSchema -- TypeScript knows the shape
```

`parsed` is automatically typed and validated. If the model produces output that doesn't match the Zod schema, an error is thrown.

## When to use each

**Prompt engineering (ask for JSON)**: for simple, one-off extractions in non-critical contexts. Fast to write, unreliable at scale.

**JSON mode**: when you need valid JSON but the schema is flexible. Good for exploratory work.

**Structured Outputs with schema**: when the shape of the data matters to your application. Required for any production pipeline that processes LLM output.

## Handling refusals

With Structured Outputs, the model can still refuse to answer. Check `finish_reason` and the `refusal` field:

```javascript
const message = completion.choices[0].message;
if (message.refusal) {
  console.error('Model refused:', message.refusal);
} else {
  const data = message.parsed;
}
```

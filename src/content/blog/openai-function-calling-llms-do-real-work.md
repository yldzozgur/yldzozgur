---
title: "OpenAI function calling: the feature that makes LLMs do real work."
description: "How OpenAI function calling works, how to define tools, and how to wire the model's output back into your application."
pubDate: 2025-05-01
tags: ["AI", "OpenAI"]
draft: false
---

Large language models are good at generating text. But generating text is not the same as doing something. Function calling is the bridge between the two.

## What function calling actually is

When you send a message to the OpenAI API with a list of function definitions, the model can decide to call one of those functions instead of writing a prose response. It returns a structured JSON payload telling you which function it wants to call and with what arguments. Your code then executes the function and sends the result back to the model for a final response.

The model does not call your function. You do. The model just tells you what to call.

## Defining a tool

Tools are defined as JSON Schema objects under the `tools` parameter:

```javascript
const tools = [
  {
    type: "function",
    function: {
      name: "get_weather",
      description: "Get current weather for a city.",
      parameters: {
        type: "object",
        properties: {
          city: {
            type: "string",
            description: "City name, e.g. Austin"
          },
          unit: {
            type: "string",
            enum: ["celsius", "fahrenheit"]
          }
        },
        required: ["city"]
      }
    }
  }
];
```

The `description` field matters more than you might think. The model reads it to decide whether to invoke the function. Be specific about what it does and when it applies.

## Making the call

```javascript
import OpenAI from "openai";

const client = new OpenAI();

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "What's the weather in Austin?" }],
  tools,
  tool_choice: "auto"
});

const message = response.choices[0].message;
```

`tool_choice: "auto"` lets the model decide whether to call a function. You can also pass `"none"` to force text output, or `{ type: "function", function: { name: "get_weather" } }` to force a specific call.

## Handling the response

When the model calls a function, `message.tool_calls` is an array of call objects:

```javascript
if (message.tool_calls) {
  const call = message.tool_calls[0];
  const args = JSON.parse(call.function.arguments);

  // Execute the actual function
  const weatherData = await getWeather(args.city, args.unit);

  // Send the result back
  const finalResponse = await client.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "user", content: "What's the weather in Austin?" },
      message, // the assistant's tool_call message
      {
        role: "tool",
        tool_call_id: call.id,
        content: JSON.stringify(weatherData)
      }
    ],
    tools
  });

  console.log(finalResponse.choices[0].message.content);
}
```

You include the original assistant message and a `tool` role message with the function result. The model uses both to generate a final, grounded response.

## Parallel tool calls

GPT-4o can request multiple function calls in a single response. `message.tool_calls` will contain more than one entry. You should run those in parallel and return all results before making the next completion call:

```javascript
const results = await Promise.all(
  message.tool_calls.map(async (call) => {
    const args = JSON.parse(call.function.arguments);
    const result = await dispatch(call.function.name, args);
    return {
      role: "tool",
      tool_call_id: call.id,
      content: JSON.stringify(result)
    };
  })
);
```

## Structured output vs function calling

OpenAI also offers a `response_format: { type: "json_schema" }` option for structured output. The difference: structured output guarantees the shape of the model's text response. Function calling is for triggering side effects — searching a database, calling an API, writing a file. Use structured output when you need the model's reasoning in a parseable shape. Use function calling when you need the model to reach outside itself.

## Common mistakes

**Vague descriptions.** If the model doesn't understand what a function does, it won't call it at the right time, or will call it when it shouldn't.

**Not handling the tool_call case.** If you only read `message.content`, you'll silently drop function calls. Always check `message.tool_calls` first.

**Trusting the arguments blindly.** The model generates arguments; they can be malformed or out of range. Parse and validate before passing to your actual logic.

**Forgetting the follow-up call.** After executing the function, you must make another completion call with the tool result. The model hasn't seen the output yet.

Function calling turns a text predictor into an agent that can interact with real systems. Most of the interesting things you can build with LLMs depend on it.

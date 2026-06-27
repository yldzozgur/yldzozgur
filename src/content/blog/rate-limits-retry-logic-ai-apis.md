---
title: "Rate limits and retry logic for AI APIs."
description: "How OpenAI and other AI API rate limits work, and how to build retry logic that handles them without hammering the provider."
pubDate: 2025-05-22
tags: ["AI", "Node.js"]
draft: false
---

AI APIs have rate limits measured in two dimensions: requests per minute (RPM) and tokens per minute (TPM). Hit either one and you get a 429. Without retry logic, that means a failed user request. With naive retry logic, you make the problem worse.

## How rate limits work

OpenAI rate limits are set per model, per API key, and change based on your usage tier. A new account on GPT-4o might have 500 RPM and 30,000 TPM. A production account might have 10,000 RPM and 2,000,000 TPM.

When you exceed a limit, the API returns:

```json
{
  "error": {
    "message": "Rate limit reached for gpt-4o in organization ...",
    "type": "requests",
    "code": "rate_limit_exceeded"
  }
}
```

The response also includes headers telling you when you can retry:

```
x-ratelimit-limit-requests: 500
x-ratelimit-remaining-requests: 0
x-ratelimit-reset-requests: 2025-05-22T10:00:01Z
retry-after: 1
```

The `retry-after` header gives you the number of seconds to wait. This is the authoritative source for when to retry.

## Exponential backoff with jitter

The wrong approach: retry immediately in a loop. If you have 10 concurrent requests all hitting the rate limit, retrying immediately at the same moment just creates a thundering herd.

The right approach: exponential backoff with jitter.

```javascript
async function withRetry(fn, options = {}) {
  const {
    maxAttempts = 5,
    baseDelayMs = 1000,
    maxDelayMs = 60000,
    retryOnStatus = [429, 500, 502, 503]
  } = options;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isRetryable = retryOnStatus.includes(error.status);
      const isLastAttempt = attempt === maxAttempts;

      if (!isRetryable || isLastAttempt) throw error;

      // Check for explicit retry-after header
      const retryAfter = error.headers?.["retry-after"];
      if (retryAfter) {
        const waitMs = parseFloat(retryAfter) * 1000;
        await sleep(waitMs);
        continue;
      }

      // Exponential backoff: 1s, 2s, 4s, 8s...
      const exponentialDelay = baseDelayMs * Math.pow(2, attempt - 1);
      // Add jitter: random offset up to 50% of delay
      const jitter = Math.random() * exponentialDelay * 0.5;
      const delay = Math.min(exponentialDelay + jitter, maxDelayMs);

      await sleep(delay);
    }
  }
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
```

Usage:

```javascript
const response = await withRetry(() =>
  client.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "Hello" }]
  })
);
```

## Token counting before you send

A request that exceeds TPM limits wastes a round trip. Count tokens before sending large prompts:

```javascript
import { encoding_for_model } from "tiktoken";

function countTokens(messages, model = "gpt-4o") {
  const enc = encoding_for_model(model);
  let total = 0;

  for (const msg of messages) {
    total += 4; // per-message overhead
    total += enc.encode(msg.content).length;
    total += enc.encode(msg.role).length;
  }
  total += 2; // priming tokens

  enc.free();
  return total;
}

const tokenCount = countTokens(messages);
if (tokenCount > TPM_BUDGET_PER_REQUEST) {
  // Truncate or summarize history before sending
}
```

## Request queuing

When you have bursts of requests (e.g., batch processing), a queue with rate limiting prevents hitting the API limit in the first place:

```javascript
import PQueue from "p-queue";

// Stay under 400 RPM by spacing requests ~150ms apart
const queue = new PQueue({
  concurrency: 5,
  interval: 1000,
  intervalCap: 8 // max 8 requests per second = 480 RPM, under the 500 limit
});

async function batchProcess(items) {
  const results = await Promise.all(
    items.map(item =>
      queue.add(() =>
        client.chat.completions.create({
          model: "gpt-4o-mini",
          messages: [{ role: "user", content: item.prompt }]
        })
      )
    )
  );
  return results;
}
```

`p-queue` is a small library that handles concurrency limits cleanly. The `interval` and `intervalCap` settings let you target a specific RPM.

## Handling 500-series errors differently

Rate limit errors (429) are the provider saying "slow down." Server errors (500, 502, 503) are the provider saying "something is wrong on our end." Both are worth retrying, but with different urgency.

For 500s, retry quickly the first time (it might be a blip) then back off. For 429s, respect the `retry-after` header exactly.

Also important: **do not retry on 400 errors** (bad request, invalid API key, context length exceeded). These will not succeed no matter how many times you retry.

```javascript
function isRetryable(error) {
  if (error.status === 429) return true;
  if (error.status >= 500) return true;
  return false; // 4xx are not retryable
}
```

## Monitoring rate limit pressure

Log rate limit errors with enough context to understand the pattern:

```javascript
catch (error) {
  if (error.status === 429) {
    metrics.increment("openai.rate_limit_hit", {
      model: params.model,
      type: error.error?.type ?? "unknown"
    });
  }
  throw error;
}
```

If you're hitting rate limits regularly on a specific model, that's a signal to either upgrade your tier, distribute load across API keys, or switch lower-stakes requests to a cheaper model with higher limits.

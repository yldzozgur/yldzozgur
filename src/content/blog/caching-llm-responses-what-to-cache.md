---
title: "Caching LLM responses: what to cache, what not to, and the key design."
description: "A practical guide to caching LLM API responses, including what makes a good cache key and when caching backfires."
pubDate: 2025-05-19
tags: ["AI", "Caching"]
draft: false
---

LLM API calls are expensive and slow. Caching the responses seems obvious. But LLM outputs are non-deterministic, prompts include dynamic context, and users ask the same question in a hundred different ways. Naive caching rarely works. Thoughtful caching can cut costs by 40-60% on the right workloads.

## What is worth caching

Not all LLM calls are equal. The best candidates for caching share these properties:

- **Deterministic or near-deterministic inputs**: The same prompt reliably produces the same useful output
- **High reuse rate**: Multiple users or requests trigger the same or very similar prompts
- **Expensive generation**: Long outputs, large models, or high request volume

Good candidates:
- Product description generation (same SKU = same prompt)
- FAQ answers where the question is standardized
- Document summarization (same document = same output)
- Code explanation for specific library functions
- Template-based content generation

Poor candidates:
- Conversational chat with user-specific context
- Responses that depend on current time or real-time data
- Highly personalized recommendations
- Any prompt where temperature > 0 is intentional

## The cache key problem

The hardest part of LLM caching is the key. Two prompts that produce identical useful outputs may look completely different as strings:

- "Summarize this article" vs "Give me a summary of this article"
- "What is React?" vs "Can you explain what React is?"

Exact string matching only works when prompts are programmatically generated and stable. For user-generated prompts, you need semantic similarity.

### Exact match caching

For programmatic prompts, normalize the input before hashing:

```javascript
import crypto from "crypto";

function makeCacheKey(model, messages, temperature) {
  const normalized = JSON.stringify({
    model,
    messages: messages.map(m => ({ role: m.role, content: m.content.trim() })),
    temperature: temperature ?? 1.0
  });
  return crypto.createHash("sha256").update(normalized).digest("hex");
}

async function cachedCompletion(params) {
  const key = makeCacheKey(params.model, params.messages, params.temperature);
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached);

  const response = await client.chat.completions.create(params);
  await redis.setex(key, 3600, JSON.stringify(response)); // 1h TTL
  return response;
}
```

### Semantic caching

For user queries, embed the query and find cached responses whose embeddings are close enough:

```javascript
async function semanticCachedCompletion(userQuery, systemPrompt) {
  const queryEmbedding = await embed(userQuery);

  // Search vector store for similar past queries
  const similar = await vectorStore.search(queryEmbedding, { threshold: 0.95, limit: 1 });

  if (similar.length > 0) {
    return similar[0].cachedResponse;
  }

  const response = await client.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userQuery }
    ]
  });

  // Store for future lookups
  await vectorStore.insert({
    embedding: queryEmbedding,
    query: userQuery,
    cachedResponse: response.choices[0].message.content
  });

  return response.choices[0].message.content;
}
```

A cosine similarity threshold of 0.95 is conservative. At 0.90 you'll get more cache hits but risk serving slightly mismatched responses.

## Provider-side prompt caching

OpenAI and Anthropic both offer prompt caching at the API level. When a large system prompt (>1024 tokens for Anthropic, >128 tokens for OpenAI) is sent repeatedly, the provider caches the KV state and charges less for cached tokens.

This is different from response caching. It speeds up generation and reduces cost even when the response itself is unique.

To use Anthropic prompt caching:

```javascript
const response = await anthropic.messages.create({
  model: "claude-3-5-sonnet-20241022",
  max_tokens: 1024,
  system: [
    {
      type: "text",
      text: veryLongSystemPrompt, // thousands of tokens
      cache_control: { type: "ephemeral" }
    }
  ],
  messages: [{ role: "user", content: userMessage }]
});
```

Cached prompt tokens cost 10% of normal input token price. For a system prompt that is 10k tokens and sent 1000 times a day, this is meaningful savings.

## TTL strategy

How long to cache depends on how often the "right" answer changes:

- Product info that changes quarterly: TTL of days to weeks
- News summaries: TTL of hours
- API documentation explanations: TTL of weeks
- Responses that depend on user state: do not cache at application level

Cache invalidation for LLM responses is the same problem as everywhere else. If the underlying data changes (a product description is updated), you need a way to invalidate the cached LLM response. A common pattern: namespace cache keys with a version or hash of the source data.

## When caching backfires

Serving a cached response when the user's context changed is worse than no cache. A user who asks "is this package compatible with Node 18?" in December and gets a cached response from March may get wrong information.

Temperature > 0 means the model is intentionally non-deterministic. Caching defeats that intentionality. If creative variation is part of the value, do not cache.

Monitor cache hit rate and response quality separately. A 70% hit rate is great; a 70% hit rate where 10% of cached responses are wrong is a bug.

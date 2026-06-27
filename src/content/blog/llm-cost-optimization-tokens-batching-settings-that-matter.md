---
title: "LLM cost optimization: tokens, batching, and the settings that matter."
description: "Practical techniques for reducing LLM API costs without degrading output quality."
pubDate: 2025-09-04
tags: ["DevOps"]
draft: false
---

LLM API costs are token costs. Input tokens and output tokens are priced per million. For applications with significant volume, unoptimized token usage translates directly to unnecessary spend. The optimizations available are practical and concrete.

## Count what you spend first

Before optimizing, measure. Log token usage for every API call:

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
)

logger.info({
    "event": "llm_call",
    "input_tokens": response.usage.input_tokens,
    "output_tokens": response.usage.output_tokens,
    "model": "claude-sonnet-4-5",
    "endpoint": endpoint_name,
})
```

After a week of logging, you can query to find which endpoints account for the most token spend. Optimization effort should target the highest volume calls.

## Model selection

The most impactful cost decision is model choice. There is usually a 10-20x price difference between a large frontier model and a smaller model in the same family.

Not every task requires the most capable model. Classification, extraction, summarization, simple question answering - these often perform equivalently on smaller models.

Test smaller models against your actual task before defaulting to the most capable:

```python
import asyncio

async def compare_models(test_cases):
    for tc in test_cases:
        small_result = await call_model("claude-haiku-4-5", tc['prompt'])
        large_result = await call_model("claude-opus-4-5", tc['prompt'])
        
        # Manual or automated evaluation
        print(f"Small: {small_result}")
        print(f"Large: {large_result}")
        print(f"Match: {evaluate_quality(small_result, large_result, tc['expected'])}")
```

If a smaller model achieves acceptable quality on 95% of cases, use it for those cases and route the harder cases to the larger model.

## Prompt compression

System prompts run on every API call. A verbose system prompt that uses 2,000 tokens costs 2,000 input tokens every single call. Compressing it to 500 tokens saves 1,500 tokens per call - significant at volume.

Remove redundant instructions. Consolidate similar rules. Use structured formats instead of verbose prose:

```
# Verbose (340 tokens):
You are a helpful assistant. Always be polite and professional.
Do not discuss topics unrelated to customer support. If a user
asks about something outside your scope, politely redirect them
to the appropriate team. Never share internal pricing or confidential
information. Keep responses concise and focused...

# Compressed (85 tokens):
Customer support assistant.
Scope: product questions and account issues only.
Rules: no internal pricing, no off-topic, redirect appropriately.
Style: concise, professional.
```

Same semantic content, 75% fewer tokens.

## Prompt caching

Some APIs support prompt caching. When the beginning of a prompt is identical across many calls (a large system prompt, a static document), the provider can cache the processed representation and charge a lower price for cached input tokens.

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": large_system_prompt,
            "cache_control": {"type": "ephemeral"}  # Mark for caching
        }
    ],
    messages=[{"role": "user", "content": user_message}]
)
```

When the same system prompt appears in subsequent calls within the cache window, the cached version is used and you pay approximately 10% of the normal input token price for that portion.

## Output token reduction

Output tokens are typically more expensive than input tokens. Responses that are longer than necessary cost more.

Be explicit about desired response length:

```
Bad:  "Summarize this article."
Good: "Summarize this article in 2-3 sentences."

Bad:  "Explain how this function works."
Good: "Explain this function in under 100 words, focusing on what it returns."
```

For structured extraction tasks, ask for JSON output with specific fields rather than a narrative explanation:

```
Extract: {"name": string, "date": "YYYY-MM-DD", "amount": number}
Do not include explanation.
```

A JSON extraction might use 50 output tokens where a narrative explanation uses 200.

## Batching

Most LLM APIs have rate limits measured in requests per minute and tokens per minute. Batching multiple independent items into a single request reduces the overhead per item and can reduce latency by avoiding sequential calls.

```python
# Instead of calling for each item separately
results = []
for item in items:
    result = await call_llm(f"Classify: {item}")
    results.append(result)

# Batch classify in a single call
items_formatted = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
response = await call_llm(f"""
Classify each item below. Return a JSON array of classifications.
Items:
{items_formatted}
""")
results = json.loads(response)
```

This only works when items are independent and when the batch fits in the context window. For classification tasks with 50-100 items, a single batched call is typically faster and cheaper than 50-100 individual calls.

## Caching at the application layer

Cache deterministic LLM responses. If the same input always produces the same output (and you do not need variation), cache the response:

```python
import hashlib, json
from functools import wraps

def cache_llm_response(ttl=3600):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(prompt, **kwargs):
            key = hashlib.sha256(f"{prompt}{json.dumps(kwargs)}".encode()).hexdigest()
            cached = redis.get(f"llm:{key}")
            if cached:
                return cached.decode()
            result = await fn(prompt, **kwargs)
            redis.setex(f"llm:{key}", ttl, result)
            return result
        return wrapper
    return decorator
```

Document classification, content moderation, tag generation - these tasks on the same content produce the same result. Caching eliminates repeated API calls entirely.

The cost optimization hierarchy: right model first, then prompt compression, then output constraints, then batching, then caching. Applied together, these routinely achieve 50-80% cost reduction on production LLM workloads.

---
title: "LLM context windows: why length limits change how you design prompts."
description: "What context windows are, how they constrain LLM application design, and the practical patterns for working within and around the limits."
pubDate: 2025-08-18
tags: ["DevOps"]
draft: false
---

Every LLM processes text within a context window - a maximum number of tokens it can see at once. This limit is not a detail. It is a fundamental constraint that shapes how you design LLM-based applications, what you can and cannot do with a single prompt, and what architectural decisions you have to make.

## What a context window actually is

When you send a message to an LLM, you are not sending just your current message. You are sending the entire conversation history, any system prompt, any documents you have attached, and the current message. All of it is tokenized and processed together. The total token count of this input must fit within the model's context limit.

Tokens are roughly 3/4 of a word in English. A context window of 128,000 tokens is approximately 100,000 words - about the length of a novel. That sounds large. In practice:

- A detailed system prompt might use 500-2,000 tokens
- A multi-turn conversation history grows by ~200-500 tokens per exchange
- A moderately sized code file might be 3,000-8,000 tokens
- A PDF document might be 20,000-80,000 tokens

The window fills faster than you expect.

## Why the limit matters for application design

A chatbot with memory: every message the user sends and every response the assistant gives adds to the conversation history. Without a pruning strategy, after 50-100 exchanges the context is full. The model starts seeing an error, or you must truncate, potentially removing context that is important.

A code assistant analyzing a large codebase: a single large file might be 10,000 tokens. A project with 100 files totals more than any context window can hold. You cannot pass all the code at once.

A document Q&A application: a legal contract might be 40,000 tokens. The model context must hold the document, the conversation, and the prompt simultaneously. This only works if the document fits.

## Strategies for working within limits

**Sliding window for conversations:** Keep only the most recent N turns of conversation, or summarize older turns.

```python
def trim_conversation(messages, max_tokens=10000):
    total = 0
    trimmed = []
    
    for msg in reversed(messages):
        tokens = count_tokens(msg['content'])
        if total + tokens > max_tokens:
            break
        trimmed.insert(0, msg)
        total += tokens
    
    return trimmed
```

**Summarization:** When conversation history gets long, ask the model to summarize the earlier portion, then replace it with the summary.

```python
async def maybe_summarize(messages, threshold=8000):
    if count_total_tokens(messages) < threshold:
        return messages
    
    early_messages = messages[:-5]  # Keep the last 5 exchanges verbatim
    summary = await llm.complete(
        f"Summarize this conversation concisely: {format_messages(early_messages)}"
    )
    
    return [{'role': 'system', 'content': f'Conversation summary: {summary}'}] + messages[-5:]
```

**Retrieval-Augmented Generation (RAG) for large documents:** Instead of stuffing all documents into the context, retrieve only the relevant chunks. Embed all documents, embed the query, find the most similar chunks, and include only those.

This is the key architectural pattern for document-heavy applications. The model never sees more than a few relevant pages at once, regardless of how large the full document set is.

**Chunked processing:** For tasks that require processing a large document (summarization, extraction), process it in chunks and combine the results.

```python
async def summarize_long_document(document, chunk_size=3000):
    chunks = split_into_chunks(document, chunk_size)
    summaries = []
    
    for chunk in chunks:
        summary = await llm.complete(f"Summarize this section: {chunk}")
        summaries.append(summary)
    
    # Combine chunk summaries into a final summary
    combined = '\n'.join(summaries)
    return await llm.complete(f"Create a coherent summary from these section summaries: {combined}")
```

## Token counting

Count tokens before sending. Most API clients have a tokenizer:

```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(text):
    return len(enc.encode(text))

def will_fit(messages, max_tokens=120000):
    total = sum(count_tokens(m['content']) for m in messages)
    return total < max_tokens
```

Count before constructing the full prompt. Discovering a context overflow when the API returns a 400 error is too late.

## Context utilization and cost

Longer contexts cost more. Most APIs charge per input token. A system prompt that is 2,000 tokens instead of 500 adds cost to every single API call. Keep system prompts concise. Remove redundant instructions. Use structured formats (JSON, YAML) instead of verbose prose where possible.

The ideal prompt uses just enough tokens to provide the necessary context. The margin between what is needed and the context limit gives you room to grow without hitting constraints unexpectedly.

Context windows will continue to grow. But understanding the limits and designing around them produces more reliable, more cost-efficient, and more scalable applications than assuming the window is infinite.

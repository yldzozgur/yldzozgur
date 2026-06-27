---
title: "Embeddings: what they encode and a practical use case."
description: "What embedding vectors represent, how to generate them with the OpenAI API, and how to use them for semantic search."
pubDate: 2025-05-26
tags: ["AI"]
draft: false
---

Embeddings are one of those concepts that sounds abstract until you build something with them. Once you have, they feel indispensable.

## What an embedding is

An embedding is a fixed-length array of numbers that represents the meaning of a piece of text. Two texts with similar meaning will produce vectors that are close together in that high-dimensional space. Two texts that mean completely different things will produce vectors that are far apart.

"The dog ran across the yard" and "A canine sprinted through the garden" will have very similar embeddings, even though they share no words. "The dog ran across the yard" and "The quarterly earnings exceeded forecasts" will have very different embeddings.

The model has learned, from training on a vast corpus, which concepts tend to appear in similar contexts. That co-occurrence information is compressed into the vector.

## Generating embeddings

With the OpenAI API:

```javascript
import OpenAI from "openai";

const client = new OpenAI();

async function embed(text) {
  const response = await client.embeddings.create({
    model: "text-embedding-3-small",
    input: text
  });
  return response.data[0].embedding; // array of 1536 floats
}

const vector = await embed("How do I reset my password?");
console.log(vector.length); // 1536
console.log(vector.slice(0, 5)); // [-0.023, 0.041, -0.012, ...]
```

OpenAI offers three embedding models:
- `text-embedding-3-small`: 1536 dimensions, cheapest, good for most uses
- `text-embedding-3-large`: 3072 dimensions, higher quality, higher cost
- `text-embedding-ada-002`: legacy, 1536 dimensions

You can also reduce the dimension of `text-embedding-3` models by passing `dimensions`:

```javascript
const response = await client.embeddings.create({
  model: "text-embedding-3-small",
  input: text,
  dimensions: 256 // reduces size and cost, small quality tradeoff
});
```

## Measuring similarity

The standard similarity metric for embeddings is cosine similarity: the cosine of the angle between two vectors. Returns 1 for identical direction (very similar), 0 for perpendicular (unrelated), -1 for opposite.

```javascript
function cosineSimilarity(a, b) {
  const dot = a.reduce((sum, val, i) => sum + val * b[i], 0);
  const magA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
  const magB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
  return dot / (magA * magB);
}

const sim = cosineSimilarity(embedding1, embedding2);
// 0.92 = very similar, 0.3 = somewhat related, 0.1 = unrelated
```

## A practical use case: FAQ search

The canonical first project with embeddings is semantic FAQ search. Instead of keyword matching, you embed every FAQ question, store the vectors, and at query time find the question whose embedding is most similar to the user's query.

```javascript
// At startup: embed all FAQ questions
const faqs = [
  { id: 1, question: "How do I reset my password?", answer: "Go to Settings > Security..." },
  { id: 2, question: "Where can I find my invoices?", answer: "Visit the Billing tab..." },
  { id: 3, question: "How do I cancel my subscription?", answer: "Email support@..." }
];

const embeddedFAQs = await Promise.all(
  faqs.map(async (faq) => ({
    ...faq,
    embedding: await embed(faq.question)
  }))
);

// At query time
async function findBestFAQ(userQuery) {
  const queryEmbedding = await embed(userQuery);

  const scored = embeddedFAQs.map(faq => ({
    ...faq,
    score: cosineSimilarity(queryEmbedding, faq.embedding)
  }));

  scored.sort((a, b) => b.score - a.score);

  const best = scored[0];
  if (best.score < 0.75) return null; // not similar enough

  return best;
}

const result = await findBestFAQ("I forgot my login credentials");
// Returns the password reset FAQ even though no words match
```

## Embedding documents, not just queries

For longer documents, you can't embed the whole thing meaningfully. The standard approach is chunking:

```javascript
function chunkText(text, chunkSize = 500, overlap = 50) {
  const words = text.split(" ");
  const chunks = [];

  for (let i = 0; i < words.length; i += chunkSize - overlap) {
    chunks.push(words.slice(i, i + chunkSize).join(" "));
  }

  return chunks;
}

async function indexDocument(doc) {
  const chunks = chunkText(doc.content);
  return Promise.all(
    chunks.map(async (chunk, index) => ({
      docId: doc.id,
      chunkIndex: index,
      text: chunk,
      embedding: await embed(chunk)
    }))
  );
}
```

Chunk size is a tuning parameter. Smaller chunks give more precise retrieval but lose surrounding context. 256-512 tokens is a common starting point.

## What embeddings don't encode

Embeddings capture semantic similarity, not factual correctness. Two confidently wrong statements about the same topic will have similar embeddings. They also don't capture recency -- the embedding model has no knowledge of when something was written.

For tasks that require precise factual lookup, combine embeddings with structured filters: embed to find the relevant document, then filter by metadata like date, category, or source.

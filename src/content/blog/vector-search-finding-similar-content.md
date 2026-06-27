---
title: "Vector search: finding similar content without keyword matching."
description: "How vector databases work, how to query them efficiently, and when to use them instead of traditional search."
pubDate: 2025-05-29
tags: ["AI", "Databases"]
draft: false
---

Keyword search breaks when users describe something without using the exact words it's indexed under. Vector search fixes that by matching on meaning instead of text. Here's how it works and how to use it.

## The problem with keyword search

A user searches for "car won't start." Your database has articles tagged "engine failure," "battery dead," "ignition problems." A keyword search returns nothing or wrong results. A vector search returns all three because it understands that these concepts are semantically related to "car won't start."

Vector search works by converting text into embeddings (dense numerical vectors) and finding vectors that are geometrically close to the query vector. No text matching required.

## How vector databases store and search

Storing millions of vectors and doing brute-force cosine similarity on each query is O(n) and too slow for production. Vector databases solve this with approximate nearest neighbor (ANN) algorithms.

The most common index type is **HNSW** (Hierarchical Navigable Small Worlds). It builds a multi-layer graph where each node is a vector. Search traverses the graph starting from a coarse layer and progressively zooms in, skipping most of the search space. The result is O(log n) approximate nearest neighbor search with controllable accuracy/speed tradeoffs.

Other index types:
- **IVFFlat**: Inverted file index, partitions vectors into clusters and only searches relevant clusters
- **PQ (Product Quantization)**: Compresses vectors for memory efficiency at some accuracy cost

Popular vector databases: Pinecone (managed), Weaviate (open source), Qdrant (open source), pgvector (PostgreSQL extension).

## pgvector: vector search in Postgres

For applications already using PostgreSQL, pgvector adds native vector search without a separate service:

```sql
-- Enable extension
CREATE EXTENSION vector;

-- Create table with vector column
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  content TEXT,
  embedding vector(1536) -- dimension must match your embedding model
);

-- Create HNSW index for fast approximate search
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- Insert a document with its embedding
INSERT INTO documents (content, embedding)
VALUES ('How to reset your password', '[0.023, -0.041, ...]'::vector);
```

Querying for similar documents:

```sql
-- Find 5 most similar documents to a query embedding
SELECT id, content, 1 - (embedding <=> '[0.019, -0.038, ...]'::vector) AS similarity
FROM documents
ORDER BY embedding <=> '[0.019, -0.038, ...]'::vector
LIMIT 5;
```

The `<=>` operator is cosine distance. Subtract from 1 to get cosine similarity. Other operators: `<->` (L2/Euclidean distance), `<#>` (negative inner product for dot product similarity).

## Using pgvector from Node.js

```javascript
import { Pool } from "pg";
import OpenAI from "openai";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const openai = new OpenAI();

async function indexDocument(content) {
  const embeddingRes = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: content
  });
  const embedding = embeddingRes.data[0].embedding;

  await pool.query(
    "INSERT INTO documents (content, embedding) VALUES ($1, $2)",
    [content, JSON.stringify(embedding)]
  );
}

async function searchSimilar(query, limit = 5) {
  const embeddingRes = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: query
  });
  const embedding = embeddingRes.data[0].embedding;

  const result = await pool.query(
    `SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity
     FROM documents
     ORDER BY embedding <=> $1::vector
     LIMIT $2`,
    [JSON.stringify(embedding), limit]
  );

  return result.rows;
}

const results = await searchSimilar("forgot my login", 3);
// Returns documents about password reset, account recovery, etc.
```

## Filtering alongside vector search

Vector search alone returns the semantically closest results regardless of any other criteria. Real applications need to combine similarity with structured filters:

```sql
-- Find similar documents but only in a specific category
SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE category = 'billing'
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

In Pinecone and Qdrant, metadata filters are passed as part of the query:

```javascript
// Qdrant example
const results = await qdrant.search("documents", {
  vector: queryEmbedding,
  filter: {
    must: [{ key: "category", match: { value: "billing" } }]
  },
  limit: 5
});
```

Pre-filtering (filter first, then search) is accurate but may miss relevant results if the filtered set is small. Post-filtering (search first, then filter) is faster but may return fewer than `limit` results if many are filtered out. Most vector databases let you configure which approach to use.

## When to use vector search vs keyword search

Use vector search when:
- Users describe what they want without knowing the exact terminology
- Your content is unstructured text
- Synonyms and paraphrasing are common

Use keyword search when:
- Users search for exact names, IDs, or codes
- Precision matters more than recall
- Explainability of results is required

The best production systems combine both: run keyword search and vector search in parallel, then merge and re-rank results (hybrid search). BM25 for lexical, cosine similarity for semantic, then a reranking model to combine scores. This is the approach most RAG systems use.

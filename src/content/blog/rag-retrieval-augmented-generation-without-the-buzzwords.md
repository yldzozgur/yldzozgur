---
title: "RAG: retrieval-augmented generation without the buzzwords."
description: "What RAG is, how the pipeline works step by step, and when it is the right architecture for an LLM application."
pubDate: 2025-08-21
tags: ["DevOps"]
draft: false
---

RAG is a pattern for giving a language model access to information it was not trained on. The name is dense but the idea is simple: before generating a response, retrieve relevant documents and include them in the prompt. The model answers based on what it retrieved, not just what it learned during training.

## Why retrieval is necessary

LLMs have a training cutoff. They do not know about events after that date. They do not know about your company's internal documentation. They do not know about your codebase, your products, or your customers.

You could fine-tune a model on your data. Fine-tuning is expensive, slow, and produces a model that is hard to update when the data changes.

You could put all your documents in the system prompt. If you have more than a few documents, they will not fit. Context windows have limits.

RAG solves both problems. Documents live in a vector database, separate from the model. At query time, the system finds the relevant documents and passes only those to the model. Updating the knowledge base means updating the vector database, not retraining or redeploying the model.

## The pipeline step by step

**Step 1: Embed the documents**

Each document (or chunk of a document) is converted to a dense vector representation using an embedding model. Semantically similar text produces vectors that are close together in the high-dimensional space.

```python
from openai import OpenAI

client = OpenAI()

def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding
```

**Step 2: Store embeddings in a vector database**

Vectors are stored alongside their source text in a vector database (Pinecone, Weaviate, pgvector, Chroma). The database indexes vectors for efficient similarity search.

```python
import chromadb

db = chromadb.PersistentClient(path="./chroma_db")
collection = db.get_or_create_collection("docs")

# Index all documents
for doc_id, text in documents.items():
    collection.add(
        ids=[doc_id],
        embeddings=[embed(text)],
        documents=[text]
    )
```

**Step 3: At query time, embed the question**

When a user asks a question, embed it using the same model.

```python
query = "How do I reset my password?"
query_embedding = embed(query)
```

**Step 4: Retrieve similar documents**

Find the documents whose embeddings are most similar to the query embedding.

```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3  # Top 3 most relevant chunks
)

relevant_docs = results['documents'][0]
```

**Step 5: Generate a response with context**

Combine the retrieved documents with the user's question in the prompt.

```python
context = "\n\n".join(relevant_docs)

prompt = f"""Answer the question based on the following documentation.
If the answer is not in the documentation, say so.

Documentation:
{context}

Question: {query}"""

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}]
)
print(response.choices[0].message.content)
```

## Chunking strategy

How you split documents matters. A chunk too small loses context. A chunk too large dilutes relevance.

Practical starting points:
- 500-1000 token chunks with 100-200 token overlap
- Split on natural boundaries (paragraphs, headers) rather than fixed character counts
- Overlapping chunks prevent relevant content from being split across a boundary

```python
def chunk_document(text, chunk_size=800, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
```

## When RAG is the right choice

RAG is appropriate when:
- Your knowledge base changes frequently (product documentation, support articles, internal wikis)
- The information is too large for a context window
- You need the model to cite sources or quote specific passages
- You need different users to see different subsets of knowledge (multi-tenant applications)

RAG is not the right choice when:
- You need the model to learn new reasoning skills or behaviors (that requires fine-tuning or training)
- Your knowledge base is tiny and fits in the context window
- Query latency is critical and the retrieval step adds unacceptable delay

## What affects RAG quality

Embedding model quality determines how well similar content is found. Chunk size and overlap affect whether relevant context is retrieved completely. The number of retrieved chunks (top-k) affects both quality and context window usage. The prompt template affects how well the model uses the retrieved context.

Most quality problems in RAG trace back to the retrieval step, not the generation step. If the model gives wrong answers, the first question is: are the right documents being retrieved? Log what gets retrieved and inspect it manually before optimizing prompts.

RAG is the practical choice for any LLM application that needs to work with a body of knowledge that is larger than the context window or more current than the model's training data.

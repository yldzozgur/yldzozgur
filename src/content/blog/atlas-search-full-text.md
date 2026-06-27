---
title: "Atlas Search: full-text search without adding Elasticsearch to your stack."
description: "MongoDB Atlas Search provides Lucene-powered full-text search natively in MongoDB, eliminating the need for a separate Elasticsearch cluster for most search use cases."
pubDate: 2024-08-29
tags: ["Security"]
draft: false
---

Full-text search is the one feature that traditionally forced developers to add Elasticsearch to their stack. MongoDB's `$text` operator supports basic text search but lacks relevance scoring, fuzzy matching, and faceted search. Atlas Search adds Lucene-based full-text search directly into MongoDB's aggregation pipeline, available on any Atlas cluster.

## How it works

Atlas Search maintains a Lucene index alongside your MongoDB collection. When you run a `$search` aggregation stage, Atlas routes the query to the Lucene index, which returns scored results that feed into the rest of your pipeline. From your application's perspective, it's just another aggregation stage.

## Creating a search index

In the Atlas UI or via the Atlas API, define a search index for your collection:

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "title": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "body": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "tags": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "publishedAt": {
        "type": "date"
      },
      "author.name": {
        "type": "string",
        "analyzer": "lucene.standard"
      }
    }
  }
}
```

`lucene.standard` tokenizes and normalizes text (lowercase, remove stop words). `lucene.keyword` treats the entire value as one token — useful for exact matches on tags, IDs, or status fields.

## Basic text search

```js
const results = await Post.aggregate([
  {
    $search: {
      index: "posts_search",
      text: {
        query: "mongodb aggregation performance",
        path: ["title", "body"],
      },
    },
  },
  { $limit: 10 },
  {
    $project: {
      title: 1,
      slug: 1,
      publishedAt: 1,
      score: { $meta: "searchScore" },
    },
  },
  { $sort: { score: -1 } },
]);
```

`{ $meta: "searchScore" }` includes the relevance score computed by Lucene. Results with the query terms in the title score higher than those with them only in the body.

## Fuzzy matching

Handle typos and similar terms:

```js
{
  $search: {
    text: {
      query: "mongdb", // typo
      path: "title",
      fuzzy: {
        maxEdits: 1,      // allow 1 character edit distance
        prefixLength: 3,  // first 3 chars must match exactly
      },
    },
  },
}
// Matches "mongodb", "mongdb", etc.
```

## Compound queries

Combine multiple conditions with boolean logic:

```js
{
  $search: {
    compound: {
      must: [
        {
          text: {
            query: "indexes",
            path: ["title", "body"],
          },
        },
      ],
      should: [
        {
          text: {
            query: "performance",
            path: ["title", "body"],
            score: { boost: { value: 1.5 } }, // boost title matches
          },
        },
      ],
      filter: [
        {
          range: {
            path: "publishedAt",
            gte: new Date("2024-01-01"),
          },
        },
        {
          text: {
            query: "mongodb",
            path: "tags",
          },
        },
      ],
    },
  },
}
```

`must` requires the condition. `should` increases the score if present. `filter` restricts results without affecting score.

## Autocomplete

Atlas Search supports prefix-based autocomplete with a dedicated index mapping:

```json
{
  "mappings": {
    "fields": {
      "title": [
        { "type": "string" },
        { "type": "autocomplete", "tokenization": "edgeGram", "minGrams": 2, "maxGrams": 15 }
      ]
    }
  }
}
```

```js
// As user types "mongo", return suggestions
const suggestions = await Post.aggregate([
  {
    $search: {
      autocomplete: {
        query: "mongo",
        path: "title",
        fuzzy: { maxEdits: 1 },
      },
    },
  },
  { $limit: 5 },
  { $project: { title: 1, slug: 1 } },
]);
```

## Combining search with regular pipeline stages

Because `$search` is a pipeline stage, it composes with everything else:

```js
const results = await Post.aggregate([
  {
    $search: {
      text: { query: searchQuery, path: ["title", "body"] },
    },
  },
  // Join with authors
  {
    $lookup: {
      from: "users",
      localField: "authorId",
      foreignField: "_id",
      as: "author",
    },
  },
  { $unwind: "$author" },
  // Filter by author after the search
  { $match: { "author.verified": true } },
  {
    $project: {
      title: 1,
      "author.name": 1,
      score: { $meta: "searchScore" },
    },
  },
  { $limit: 20 },
]);
```

## Limitations vs Elasticsearch

Atlas Search covers most use cases, but has some gaps compared to a dedicated Elasticsearch cluster:

- No real-time indexing — there's a brief lag between document writes and search index updates (typically a few seconds)
- Atlas-only — works on MongoDB Atlas, not self-hosted MongoDB
- Less tuning control than a dedicated Elasticsearch deployment

For most applications — product search, content search, user search — Atlas Search is sufficient and eliminates an entire service from your infrastructure. The tradeoff: you're locked into Atlas.

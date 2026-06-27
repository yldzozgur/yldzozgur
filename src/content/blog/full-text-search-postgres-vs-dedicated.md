---
title: "Full-text search: when PostgreSQL is enough and when it isn't."
description: "How PostgreSQL full-text search works, its real limitations, and what Elasticsearch and Typesense add that PostgreSQL can't."
pubDate: 2026-02-19
tags: ["Architecture"]
draft: false
---

Adding search to an application usually starts with the simplest thing: a `LIKE` query. Then you discover `LIKE '%term%'` can't use an index and scans the entire table. Then you learn about PostgreSQL's full-text search. Then you realize you need fuzzy matching, facets, and sub-100ms response times. The question is: where does PostgreSQL's full-text capability end?

## PostgreSQL full-text search

PostgreSQL stores documents as `tsvector` -- a list of normalized lexemes (stemmed words) with their positions. Queries are `tsquery` -- a boolean expression of lexemes.

```sql
-- The simple approach: generate tsvector on the fly
SELECT title
FROM articles
WHERE to_tsvector('english', title || ' ' || body) @@ to_tsquery('english', 'database & performance');

-- Better: store the tsvector in a generated column with a GIN index
ALTER TABLE articles
  ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))
  ) STORED;

CREATE INDEX articles_search_idx ON articles USING GIN(search_vector);
```

With the GIN index, full-text queries are fast even on large tables. The `@@` operator checks if a document matches a query; `ts_rank()` provides relevance scoring.

```sql
SELECT title, ts_rank(search_vector, query) AS rank
FROM articles, to_tsquery('english', 'database & performance') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 10;
```

**What works well in PostgreSQL:**

- Boolean queries (`AND`, `OR`, `NOT`)
- Prefix matching (`web:*` matches "web", "webapp", "website")
- Phrase search (`phraseto_tsquery`)
- Relevance ranking with `ts_rank`
- Highlighting matches with `ts_headline`
- Simple faceting with GROUP BY on indexed columns

## Where PostgreSQL falls short

**Fuzzy matching / typo tolerance:** `to_tsquery('english', 'databse')` returns no results. PostgreSQL full-text search operates on exact lexemes after stemming. You can combine it with `pg_trgm` for trigram similarity:

```sql
SELECT title
FROM articles
WHERE similarity(title, 'databse') > 0.3
   OR search_vector @@ to_tsquery('english', 'database');
```

But this gets complicated fast, and the trigram index is larger and slower than a GIN index for full-text.

**Relevance tuning:** PostgreSQL's `ts_rank` is limited. You can't easily boost certain fields, implement BM25 scoring, or tune relevance with custom signals like click-through rate.

**Faceted search:** Getting counts by category, tag, or date range while also filtering by them requires complex queries. PostgreSQL can do it, but performance degrades as the complexity grows.

**Scale:** GIN indexes are update-expensive. High write rates with concurrent search queries can cause contention. A dedicated search engine has write and search paths designed independently.

## When to bring in a dedicated search engine

**Elasticsearch / OpenSearch:** Best-in-class for complex relevance tuning, large-scale aggregations, and autocomplete. Heavy operationally: you're managing a JVM cluster with significant memory requirements. Appropriate for applications where search is a core product feature.

**Typesense:** A modern Elasticsearch alternative with built-in typo tolerance, easier operations (single binary, no JVM), and a simpler API. Good choice if you need fuzzy search and faceting without Elasticsearch's operational overhead.

```typescript
// Typesense: typo-tolerant search with facets
const results = await client.collections('articles').documents().search({
  q: 'databse performanc',   // typos handled automatically
  query_by: 'title,body',
  facet_by: 'category,tags',
  sort_by: '_text_match:desc',
  num_typos: 2,
});
```

**Meilisearch:** Similar to Typesense, optimized for developer experience and instant search UIs.

## The practical decision

Use PostgreSQL full-text search when:
- Your data is already in PostgreSQL and search is a secondary feature
- You need simple keyword search without typo tolerance
- You want to avoid another infrastructure component
- Your dataset is under a few million rows

Move to a dedicated search engine when:
- Typo tolerance is required
- You need complex faceting and filtering
- Search performance is business-critical
- You're doing autocomplete over large datasets

Many applications use both: PostgreSQL for the primary data store and application queries, with a search engine synced via a CDC (Change Data Capture) pipeline or background job for search-specific queries.

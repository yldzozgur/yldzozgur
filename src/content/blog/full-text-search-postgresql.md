---
title: "Full-text search in PostgreSQL: no extra service required."
description: "PostgreSQL's built-in full-text search uses tsvector and tsquery to support ranked, stemmed, stop-word-filtered search without adding Elasticsearch or another service."
pubDate: 2024-09-23
tags: ["Security"]
draft: false
---

Elasticsearch is often added to a stack for full-text search when PostgreSQL can handle the same use cases natively. For most applications — content search, product search, user search — PostgreSQL's tsvector/tsquery engine is sufficient, doesn't require another service to operate, and is transactionally consistent with your data.

## The core types

**tsvector**: a normalized, searchable representation of text. It's the document.

**tsquery**: a query expression. It's what you search for.

```sql
-- Convert text to a tsvector
SELECT to_tsvector('english', 'The quick brown fox jumps over the lazy dog');
-- Result: 'brown':3 'dog':9 'fox':4 'jump':5 'lazi':8 'quick':2
-- Note: "the" and "over" are stop words (removed); "jumps" is stemmed to "jump"

-- Create a tsquery
SELECT to_tsquery('english', 'jumping & fox');
-- Result: 'jump' & 'fox'
-- Note: "jumping" is stemmed to match "jump" in the tsvector

-- Match check
SELECT to_tsvector('english', 'The fox jumps') @@ to_tsquery('english', 'jumping');
-- Result: true
```

The `@@` operator checks whether a tsvector matches a tsquery.

## Setting up full-text search on a table

The naive approach generates tsvectors on the fly:

```sql
-- Works, but no index benefit
SELECT id, title FROM posts
WHERE to_tsvector('english', title || ' ' || body) @@ to_tsquery('english', 'database');
```

The proper approach stores the tsvector in a generated column and indexes it:

```sql
ALTER TABLE posts ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(body, '')), 'B')
  ) STORED;

CREATE INDEX idx_posts_search ON posts USING GIN (search_vector);
```

`setweight` assigns a weight (A, B, C, or D) to each source. Words from the title (weight A) rank higher than words from the body (weight B) in relevance scoring.

## Querying with ranking

```sql
SELECT
  id,
  title,
  ts_rank(search_vector, query) AS rank,
  ts_headline('english', body, query, 'MaxWords=20, MinWords=10') AS excerpt
FROM posts,
  to_tsquery('english', 'database & performance') query
WHERE search_vector @@ query
ORDER BY rank DESC
LIMIT 10;
```

`ts_rank()` computes a relevance score based on match frequency and weight. `ts_headline()` returns a snippet of the source text with the matching terms highlighted.

## tsquery syntax

```sql
-- AND: both terms must match
to_tsquery('english', 'database & index')

-- OR: either term matches
to_tsquery('english', 'database | mongodb')

-- NOT: term must not appear
to_tsquery('english', 'database & !nosql')

-- Phrase: terms must appear adjacent in order
phraseto_tsquery('english', 'query optimization')

-- Prefix matching: matches "index", "indexes", "indexing"
to_tsquery('english', 'index:*')
```

For user input (where query syntax isn't controlled), use `plainto_tsquery` or `websearch_to_tsquery`:

```sql
-- plainto_tsquery: treats input as a list of words, ANDs them
plainto_tsquery('english', 'database performance') -- 'databas' & 'perform'

-- websearch_to_tsquery: supports quoted phrases and - for NOT
websearch_to_tsquery('english', '"query plan" -slow') -- 'queri' <-> 'plan' & !'slow'
```

Always use these for user input — passing raw user input to `to_tsquery` can throw syntax errors on special characters.

## Multi-language support

PostgreSQL ships with text search configurations for many languages:

```sql
SELECT to_tsvector('turkish', 'veritabanı sorgusu');
SELECT to_tsvector('german', 'Datenbankabfrage');
```

The language configuration controls stemming and stop words. If you support multiple languages, store the language alongside the content and use it when generating the tsvector:

```sql
-- Dynamic language selection
SELECT to_tsvector(doc.language::regconfig, doc.content)
FROM documents doc;
```

## Keeping search_vector up to date

With a generated column (`GENERATED ALWAYS AS ... STORED`), PostgreSQL updates the tsvector automatically on every insert and update. No trigger or application code needed.

If you can't use generated columns (PostgreSQL < 12 or if the expression is too complex), use a trigger:

```sql
CREATE FUNCTION update_search_vector() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A')
    || setweight(to_tsvector('english', coalesce(NEW.body, '')), 'B');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER posts_search_vector_update
BEFORE INSERT OR UPDATE OF title, body ON posts
FOR EACH ROW EXECUTE FUNCTION update_search_vector();
```

## When to upgrade to Elasticsearch

PostgreSQL's full-text search handles most use cases. Consider Elasticsearch when you need:
- Real-time search with sub-100ms latency at very high traffic
- Custom analyzers for unusual languages or technical content
- Complex relevance tuning (boosting, custom scoring functions)
- Distributed search across extremely large datasets

For the majority of applications, the operational simplicity of staying on PostgreSQL outweighs the marginal capabilities of Elasticsearch.

---
title: "JSONB columns: flexible schema without breaking your relational model."
description: "PostgreSQL's JSONB type stores structured JSON with binary indexing and full operator support. It adds flexibility for variable attributes without requiring a document database."
pubDate: 2024-09-19
tags: ["Security"]
draft: false
---

PostgreSQL offers two JSON types: `json` (stored as text, validated) and `jsonb` (stored as binary, indexable, and with operator support). In practice, always use `jsonb`. The binary format enables indexing and faster reads at the cost of slightly slower writes — a trade most applications should accept.

## When JSONB makes sense

Consider a products table for an e-commerce platform that sells books, electronics, and clothing. Each category has different attributes:

- Books: author, ISBN, pages, publisher
- Electronics: voltage, warranty_months, connectivity
- Clothing: sizes, material, care_instructions

Storing all possible attributes as nullable columns creates a wide, sparse table. Adding a new category requires a migration. JSONB handles this cleanly:

```sql
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price NUMERIC(10, 2) NOT NULL,
  attributes JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO products (name, category, price, attributes) VALUES
  ('Clean Code', 'book', 29.99, '{"author": "Robert Martin", "isbn": "9780132350884", "pages": 464}'),
  ('USB-C Hub', 'electronics', 49.99, '{"ports": 7, "warranty_months": 12, "connectivity": ["USB-C", "HDMI"]}'),
  ('Linen Shirt', 'clothing', 89.99, '{"sizes": ["S","M","L","XL"], "material": "linen", "color": "white"}');
```

## Querying JSONB

The `->` operator returns JSON, `->>`  returns text:

```sql
-- Get the author as JSON (quoted string)
SELECT attributes -> 'author' FROM products WHERE category = 'book';
-- Result: "Robert Martin"

-- Get the author as text (unquoted)
SELECT attributes ->> 'author' FROM products WHERE category = 'book';
-- Result: Robert Martin

-- Navigate nested JSON
SELECT attributes -> 'dimensions' ->> 'width' FROM products;

-- Query by JSON value
SELECT name, price FROM products
WHERE attributes ->> 'author' = 'Robert Martin';

-- Check array membership
SELECT name FROM products
WHERE attributes -> 'connectivity' ? 'HDMI';

-- Check if a key exists
SELECT name FROM products WHERE attributes ? 'isbn';
```

## Indexing JSONB

A GIN (Generalized Inverted Index) index covers all keys in the JSONB column:

```sql
-- GIN index: covers key existence checks (?), containment (@>), and key-path queries
CREATE INDEX idx_products_attributes ON products USING GIN (attributes);
```

This makes `?`, `?|`, `?&`, and `@>` operators use the index:

```sql
-- Containment: find products with these exact attribute values
SELECT * FROM products WHERE attributes @> '{"author": "Robert Martin"}';

-- Key existence: find products with a warranty
SELECT * FROM products WHERE attributes ? 'warranty_months';
```

For queries on a specific key, a partial index is more efficient:

```sql
-- Index only the 'author' key as text, for fast equality lookups
CREATE INDEX idx_products_author ON products ((attributes ->> 'author'));
```

```sql
-- Uses the expression index
SELECT * FROM products WHERE attributes ->> 'author' = 'Robert Martin';
```

## Updating JSONB

PostgreSQL 9.5+ has `jsonb_set` for partial updates:

```sql
-- Update a single key without rewriting the entire object
UPDATE products
SET attributes = jsonb_set(attributes, '{warranty_months}', '24')
WHERE id = 2;

-- Add a new key
UPDATE products
SET attributes = attributes || '{"refurbished": false}'
WHERE category = 'electronics';

-- Remove a key
UPDATE products
SET attributes = attributes - 'old_field'
WHERE category = 'book';
```

## Mixing fixed and flexible columns

The best JSONB schemas use fixed columns for queryable, relational attributes and JSONB for variable attributes:

```sql
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,          -- fixed: always present, always queried
  category TEXT NOT NULL,      -- fixed: frequently filtered
  price NUMERIC(10, 2) NOT NULL, -- fixed: sorted and filtered
  in_stock BOOLEAN DEFAULT true, -- fixed: critical for inventory queries
  attributes JSONB,            -- flexible: category-specific metadata
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Filtering on `price`, `category`, and `in_stock` uses standard B-tree indexes. The JSONB column holds everything else without schema changes.

## Validating JSONB structure

PostgreSQL doesn't enforce JSONB structure by default. Use check constraints for required attributes per category:

```sql
ALTER TABLE products ADD CONSTRAINT chk_book_attributes
CHECK (
  category != 'book' OR (
    attributes ? 'author' AND attributes ? 'isbn'
  )
);
```

Or handle validation in application code before inserting.

## When not to use JSONB

JSONB is not a replacement for normalized columns when:
- You need foreign key constraints on values inside the JSON
- You need efficient range queries across many rows on a JSONB field (use a proper column)
- The "flexible" field is actually always the same shape (just use a normal column)
- You need full referential integrity across the values

JSONB adds flexibility but loses some of PostgreSQL's relational guarantees. Use it where the flexibility is genuinely needed.

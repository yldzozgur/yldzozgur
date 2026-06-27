---
title: "Relational modeling: when to normalize and when to stop."
description: "Normalization removes redundancy but adds joins. The practical question is which normal form your schema should target and when denormalization is the right engineering tradeoff."
pubDate: 2024-09-05
tags: ["Security"]
draft: false
---

Normalization is taught as a virtue — the more normal forms you satisfy, the better your schema. In practice, fully normalized schemas can be slower to query and harder to work with. Understanding what each normal form actually eliminates helps you decide where to stop.

## What normalization solves

An unnormalized table stores redundant data. Redundancy causes anomalies:

**Update anomaly**: a customer's city is stored in every order row. Update one row and the others are stale.

**Insert anomaly**: you can't add a product category until you have a product to put in it.

**Delete anomaly**: deleting the last product in a category also destroys the category's data.

Normalization eliminates these by ensuring each fact is stored in exactly one place.

## First Normal Form (1NF)

**Rule**: every column contains atomic values; no repeating groups.

Violation — storing multiple phone numbers in a single column:
```sql
-- Bad: violates 1NF
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name TEXT,
  phone_numbers TEXT -- "555-1234, 555-5678"
);
```

Fix — separate table for phone numbers:
```sql
CREATE TABLE customers (id SERIAL PRIMARY KEY, name TEXT);
CREATE TABLE customer_phones (
  id SERIAL PRIMARY KEY,
  customer_id INT REFERENCES customers(id),
  phone TEXT,
  type TEXT -- 'mobile', 'home'
);
```

Most ORMs enforce 1NF naturally because they map to typed columns.

## Second Normal Form (2NF)

**Rule**: every non-key column depends on the entire primary key (only relevant for composite keys).

A composite primary key creates this risk:

```sql
-- Violates 2NF: product_name depends only on product_id, not the full key
CREATE TABLE order_items (
  order_id INT,
  product_id INT,
  product_name TEXT, -- depends only on product_id
  quantity INT,
  PRIMARY KEY (order_id, product_id)
);
```

Fix: `product_name` belongs in a `products` table.

```sql
CREATE TABLE products (id SERIAL PRIMARY KEY, name TEXT, price NUMERIC);
CREATE TABLE order_items (
  order_id INT REFERENCES orders(id),
  product_id INT REFERENCES products(id),
  quantity INT,
  unit_price NUMERIC, -- snapshot at time of purchase
  PRIMARY KEY (order_id, product_id)
);
```

Note `unit_price` in `order_items` — this is intentional denormalization. You want to record what was charged, not what the product costs today.

## Third Normal Form (3NF)

**Rule**: every non-key column depends directly on the primary key, not on another non-key column (no transitive dependencies).

```sql
-- Violates 3NF: zip_code → city (transitively)
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name TEXT,
  zip_code TEXT,
  city TEXT -- depends on zip_code, not id
);
```

Fix: zip codes in their own table.

```sql
CREATE TABLE zip_codes (zip TEXT PRIMARY KEY, city TEXT, state TEXT);
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name TEXT,
  zip_code TEXT REFERENCES zip_codes(zip)
);
```

In practice, most applications don't do this. Storing city alongside zip is accepted denormalization because the join isn't worth it and zip-to-city mapping is mostly stable.

## When to stop normalizing

**3NF is the practical target** for most OLTP schemas. Beyond that, you're often solving theoretical problems that don't manifest in real applications.

**Intentional denormalization** is sometimes the right call:

- Storing a user's full name alongside their ID in a posts table to avoid a join on every page load
- Caching an aggregate (post count, total order value) in a column rather than computing it on every read
- Storing address components in an orders table even though they exist in the users table — order history needs the address as it was, not the current address

```sql
-- Denormalized order record: stores address snapshot
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  -- Snapshot of shipping address at time of order
  ship_street TEXT,
  ship_city TEXT,
  ship_state TEXT,
  ship_zip TEXT,
  total NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

If you normalized this and referenced `users.address`, changing the user's address would retroactively change where past orders appear to have shipped — which is wrong.

## The join cost tradeoff

Joins are fast when the joined columns are indexed. A 3NF schema with proper indexes often performs better than a denormalized schema because smaller, normalized tables fit better in memory. Premature denormalization for performance without measuring is usually a mistake.

Denormalize when:
- You've measured that a specific join is the actual bottleneck
- The data is read far more than written
- The data being duplicated doesn't change independently (snapshot values)
- The join involves a very large table and the joined data is needed on every row

Normalize (and add indexes) as your default. Denormalize deliberately, document why, and enforce consistency with application logic or database triggers.

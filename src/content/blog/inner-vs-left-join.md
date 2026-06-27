---
title: "INNER vs LEFT JOIN: the one you reach for 90% of the time and why."
description: "INNER JOIN returns only matching rows. LEFT JOIN returns all rows from the left table. Choosing wrong silently drops data or inflates result sets — here's how to think about it."
pubDate: 2024-09-12
tags: ["Security"]
draft: false
---

JOIN type is one of those SQL decisions that's easy to get wrong silently. An INNER JOIN that should be a LEFT JOIN drops rows without an error. A LEFT JOIN that should be INNER clutters result sets with nulls. The distinction matters and is worth getting right by reasoning, not by trial and error.

## INNER JOIN: only matching rows

`INNER JOIN` returns rows where the join condition is satisfied in both tables. If a row in the left table has no match in the right table, it's excluded from the result.

```sql
SELECT
  orders.id,
  orders.total,
  users.name AS customer_name
FROM orders
INNER JOIN users ON orders.user_id = users.id
WHERE orders.created_at > '2024-01-01';
```

If an order's `user_id` doesn't exist in the `users` table — because the user was hard-deleted, or it's test data — that order is silently excluded from results. INNER JOIN assumes the relationship always holds.

Use INNER JOIN when: the join represents a required relationship. An order must have a user. A post must have an author. If the related record doesn't exist, the row has incomplete data and shouldn't appear.

## LEFT JOIN: all rows from the left table

`LEFT JOIN` (also `LEFT OUTER JOIN`) returns all rows from the left table, plus matching rows from the right table. When there's no match, right-table columns are NULL.

```sql
SELECT
  users.id,
  users.name,
  orders.id AS order_id,
  orders.total
FROM users
LEFT JOIN orders ON orders.user_id = users.id
WHERE users.created_at > '2024-01-01';
```

Every user appears in results. Users with no orders get `NULL` for `order_id` and `total`. INNER JOIN here would drop users who haven't ordered — often wrong for a "list all users" query.

Use LEFT JOIN when: you want all records from one table, regardless of whether related records exist. Users with no orders, posts with no comments, products with no reviews.

## The 90% rule

LEFT JOIN is the join you'll use more often than you think, because most lists and reports want all records from the primary entity, optionally enriched with data from related tables.

Common LEFT JOIN patterns:

```sql
-- All posts, show comment count (0 for posts with no comments)
SELECT
  posts.id,
  posts.title,
  COUNT(comments.id) AS comment_count
FROM posts
LEFT JOIN comments ON comments.post_id = posts.id
GROUP BY posts.id, posts.title;

-- All users, show whether they've verified their email
SELECT
  users.id,
  users.email,
  CASE WHEN verifications.id IS NOT NULL THEN true ELSE false END AS email_verified
FROM users
LEFT JOIN email_verifications ON email_verifications.user_id = users.id
  AND email_verifications.verified_at IS NOT NULL;
```

## Filtering on LEFT JOIN results

Be careful with WHERE clauses on LEFT JOIN columns. Adding a filter on a nullable column from the right table turns a LEFT JOIN into an INNER JOIN:

```sql
-- This looks like a LEFT JOIN but behaves like INNER JOIN
-- because rows with NULL order_id fail the WHERE condition
SELECT users.name, orders.total
FROM users
LEFT JOIN orders ON orders.user_id = users.id
WHERE orders.total > 100; -- drops users with no orders (NULL > 100 is false)
```

If you want users who either have no orders or have orders over $100:

```sql
WHERE orders.total > 100 OR orders.id IS NULL;
```

Or move the filter into the JOIN condition:

```sql
LEFT JOIN orders ON orders.user_id = users.id AND orders.total > 100
-- Now NULL rows (users with no qualifying orders) are included
```

## RIGHT JOIN: rarely needed

`RIGHT JOIN` returns all rows from the right table. It's the mirror of LEFT JOIN. In practice, you can always rewrite a RIGHT JOIN as a LEFT JOIN by swapping the table order. Most teams use only LEFT JOIN for consistency.

## FULL OUTER JOIN: when you need all rows from both sides

Returns all rows from both tables, with NULLs where there's no match on either side. Useful for comparing two datasets:

```sql
-- Find users present in old_users but not new_users, and vice versa
SELECT
  old_users.email AS old_email,
  new_users.email AS new_email
FROM old_users
FULL OUTER JOIN new_users ON old_users.email = new_users.email
WHERE old_users.id IS NULL OR new_users.id IS NULL;
```

## The decision process

1. Do you want rows from the left table even when there's no match? **LEFT JOIN**
2. Do you only want rows where both sides match? **INNER JOIN**
3. Do you need rows from both tables regardless of match? **FULL OUTER JOIN**
4. Are you joining on a primary/foreign key relationship where the FK is NOT NULL constrained? **INNER JOIN** (the NULL case can't happen anyway)
5. Are you joining to count or aggregate optional relationships? **LEFT JOIN** (to count zeros, not just nonzero values)

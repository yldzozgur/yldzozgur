---
title: "Window functions in PostgreSQL: running totals without a subquery."
description: "Window functions compute values across rows related to the current row without collapsing them into groups. They're the clean solution to running totals, rankings, and row comparisons."
pubDate: 2024-09-16
tags: ["Security"]
draft: false
---

Before window functions, computing a running total or ranking in SQL required self-joins or correlated subqueries that were both slow and hard to read. Window functions express these computations directly, run efficiently, and don't collapse rows like GROUP BY does.

## The problem they solve

You have a sales table and need to compute a running total — the cumulative revenue up to each date:

```sql
-- Without window functions: correlated subquery (slow, verbose)
SELECT
  sale_date,
  amount,
  (
    SELECT SUM(amount)
    FROM sales s2
    WHERE s2.sale_date <= s1.sale_date
  ) AS running_total
FROM sales s1
ORDER BY sale_date;
```

This runs a subquery for every row — O(n²). With a window function:

```sql
-- With window functions: clean and fast
SELECT
  sale_date,
  amount,
  SUM(amount) OVER (ORDER BY sale_date) AS running_total
FROM sales
ORDER BY sale_date;
```

Same result, single pass over the data.

## The OVER clause

Every window function uses `OVER(...)` to define the window — the set of rows and ordering:

```sql
function_name() OVER (
  PARTITION BY column    -- optional: separate windows per group
  ORDER BY column        -- optional: order within the window
  ROWS/RANGE ...         -- optional: frame definition
)
```

## Running total with PARTITION BY

Compute a running total per user:

```sql
SELECT
  user_id,
  order_date,
  amount,
  SUM(amount) OVER (
    PARTITION BY user_id
    ORDER BY order_date
  ) AS cumulative_spend
FROM orders
ORDER BY user_id, order_date;
```

`PARTITION BY user_id` creates a separate window for each user. The running total resets for each user.

## Ranking functions

`ROW_NUMBER()`, `RANK()`, and `DENSE_RANK()` assign rankings within a window:

```sql
-- Top spender per region
SELECT
  region,
  user_id,
  total_spent,
  RANK() OVER (
    PARTITION BY region
    ORDER BY total_spent DESC
  ) AS rank_in_region
FROM user_totals;
```

- `ROW_NUMBER()`: unique number for every row (ties get different numbers)
- `RANK()`: same rank for ties, skips numbers (1, 1, 3...)
- `DENSE_RANK()`: same rank for ties, no gaps (1, 1, 2...)

Filtering to the top N per partition:

```sql
-- Top 3 products per category by revenue
SELECT * FROM (
  SELECT
    category,
    product_name,
    revenue,
    RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank
  FROM product_revenue
) ranked
WHERE rank <= 3;
```

## LAG and LEAD: comparing adjacent rows

`LAG()` accesses the previous row's value; `LEAD()` accesses the next row's:

```sql
-- Month-over-month revenue change
SELECT
  month,
  revenue,
  LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
  revenue - LAG(revenue) OVER (ORDER BY month) AS change,
  ROUND(
    (revenue - LAG(revenue) OVER (ORDER BY month))
    / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100,
    1
  ) AS pct_change
FROM monthly_revenue
ORDER BY month;
```

`NULLIF(expr, 0)` prevents division by zero when the previous month's revenue was zero.

## Frame definitions

By default, `ORDER BY` in a window function uses `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` — all rows from the start up to the current row. You can change this:

```sql
-- 7-day moving average
SELECT
  sale_date,
  amount,
  AVG(amount) OVER (
    ORDER BY sale_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS seven_day_avg
FROM daily_sales;
```

`ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` includes the current row and the 6 rows before it — a 7-row window. `ROWS` counts physical rows; `RANGE` counts rows with the same ORDER BY value (handles ties differently).

## FIRST_VALUE and LAST_VALUE

```sql
-- Show each order alongside the user's first and most recent order dates
SELECT
  user_id,
  order_date,
  FIRST_VALUE(order_date) OVER (
    PARTITION BY user_id
    ORDER BY order_date
  ) AS first_order_date,
  LAST_VALUE(order_date) OVER (
    PARTITION BY user_id
    ORDER BY order_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) AS most_recent_order_date
FROM orders;
```

`LAST_VALUE` requires `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` to include the entire partition — by default it only sees up to the current row.

## Performance

Window functions are generally efficient. PostgreSQL processes them in a single pass with a sort when needed. Use `EXPLAIN ANALYZE` to check for sort operations — if the ORDER BY in the window function matches an existing index, PostgreSQL may avoid the sort entirely.

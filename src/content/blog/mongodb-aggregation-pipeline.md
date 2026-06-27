---
title: "The aggregation pipeline: $match, $group, $project with a real example."
description: "MongoDB's aggregation pipeline processes documents through stages. Walk through a real analytics query using $match, $group, and $project to understand how data flows between stages."
pubDate: 2024-08-15
tags: ["Security"]
draft: false
---

The aggregation pipeline is MongoDB's answer to SQL's GROUP BY, JOINs, and computed columns. Documents flow through a sequence of stages, each stage transforming the data, and the final stage produces the result. Understanding a few key stages unlocks most real-world aggregation needs.

## The mental model

Think of each stage as a transformation step:

```
collection → [$match] → [$group] → [$project] → [$sort] → result
```

Each stage receives the documents from the previous stage and passes its output to the next. Stages that reduce document count (like `$match` and `$limit`) are more efficient earlier in the pipeline.

## The scenario

We have an `orders` collection:

```js
// Sample documents
{
  _id: ObjectId("..."),
  userId: ObjectId("..."),
  status: "completed",
  total: 99.99,
  items: [
    { productId: ObjectId("..."), category: "electronics", price: 79.99, quantity: 1 },
    { productId: ObjectId("..."), category: "accessories", price: 19.99, quantity: 1 }
  ],
  createdAt: ISODate("2024-08-15T10:30:00Z")
}
```

Goal: find total revenue and order count per category for the month of August 2024, for completed orders only.

## $match: filter first

`$match` is MongoDB's `find()` equivalent inside a pipeline. Always put it first to reduce the document set before expensive operations:

```js
const pipeline = [
  {
    $match: {
      status: "completed",
      createdAt: {
        $gte: new Date("2024-08-01"),
        $lt: new Date("2024-09-01"),
      },
    },
  },
  // ...
];
```

This uses your indexes on `status` and `createdAt` if they exist. Subsequent stages only see completed August orders.

## $unwind: flatten arrays

Before grouping by category, we need to flatten the `items` array so each item becomes its own document:

```js
{
  $unwind: "$items"
}
```

One order with 3 items becomes 3 documents, each with a single `items` object. After unwind, each document represents one line item.

## $group: aggregate values

`$group` is the core of aggregation. `_id` defines what you're grouping by; the other fields define what to compute:

```js
{
  $group: {
    _id: "$items.category",          // group by category
    totalRevenue: {
      $sum: { $multiply: ["$items.price", "$items.quantity"] }
    },
    orderCount: { $sum: 1 },         // count documents in each group
    avgOrderValue: { $avg: "$items.price" },
    uniqueProducts: { $addToSet: "$items.productId" }
  }
}
```

Accumulator operators:
- `$sum`: total or count (use `1` to count)
- `$avg`: arithmetic mean
- `$min` / `$max`: extreme values
- `$addToSet`: array of unique values
- `$push`: array of all values (including duplicates)

After this stage, one document per category:

```js
{
  _id: "electronics",
  totalRevenue: 4200.50,
  orderCount: 53,
  avgOrderValue: 79.25,
  uniqueProducts: [ObjectId("..."), ObjectId("..."), ...]
}
```

## $project: reshape the output

`$project` controls which fields appear in the output and can compute new ones:

```js
{
  $project: {
    _id: 0,                    // exclude _id
    category: "$_id",          // rename _id to category
    totalRevenue: {
      $round: ["$totalRevenue", 2]   // round to 2 decimal places
    },
    orderCount: 1,
    avgOrderValue: { $round: ["$avgOrderValue", 2] },
    productCount: { $size: "$uniqueProducts" },  // count unique products
  }
}
```

## Putting it together

```js
const revenueByCategory = await Order.aggregate([
  // Stage 1: filter to completed August orders
  {
    $match: {
      status: "completed",
      createdAt: {
        $gte: new Date("2024-08-01"),
        $lt: new Date("2024-09-01"),
      },
    },
  },
  // Stage 2: flatten items array
  { $unwind: "$items" },
  // Stage 3: group by category
  {
    $group: {
      _id: "$items.category",
      totalRevenue: {
        $sum: { $multiply: ["$items.price", "$items.quantity"] },
      },
      orderCount: { $sum: 1 },
      productCount: { $addToSet: "$items.productId" },
    },
  },
  // Stage 4: reshape output
  {
    $project: {
      _id: 0,
      category: "$_id",
      totalRevenue: { $round: ["$totalRevenue", 2] },
      orderCount: 1,
      uniqueProductCount: { $size: "$productCount" },
    },
  },
  // Stage 5: sort by revenue descending
  { $sort: { totalRevenue: -1 } },
]);

// Result:
// [
//   { category: "electronics", totalRevenue: 4200.50, orderCount: 53, uniqueProductCount: 12 },
//   { category: "clothing", totalRevenue: 2100.75, orderCount: 89, uniqueProductCount: 24 },
//   ...
// ]
```

## Other useful stages

- `$limit` / `$skip`: pagination
- `$lookup`: join from another collection
- `$addFields`: add computed fields without removing others
- `$facet`: run multiple sub-pipelines in parallel and combine results
- `$bucket`: group numeric values into ranges

The aggregation pipeline handles queries that would require multiple application-level operations if done with `find()`. Push aggregation work to MongoDB rather than fetching large result sets and processing them in Node.js — the database is faster and the network transfer is smaller.

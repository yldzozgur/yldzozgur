---
title: "Embed vs reference in MongoDB: the decision that's hard to undo."
description: "MongoDB gives you the choice to embed related data or reference it. The wrong choice causes either performance problems or query complexity that's expensive to reverse later."
pubDate: 2024-08-05
tags: ["Security"]
draft: false
---

MongoDB doesn't enforce a schema, which means data modeling decisions are entirely on you. The most consequential decision is whether to embed related data inside a document or store it separately and reference it. This choice affects query performance, write complexity, and document size — and changing it later requires a migration.

## What embedding looks like

An order document that embeds line items:

```js
{
  _id: ObjectId("..."),
  userId: ObjectId("..."),
  status: "shipped",
  createdAt: ISODate("2024-08-05"),
  items: [
    { productId: ObjectId("..."), name: "Laptop", quantity: 1, price: 999 },
    { productId: ObjectId("..."), name: "Mouse", quantity: 2, price: 29 }
  ],
  shippingAddress: {
    street: "123 Main St",
    city: "Austin",
    zip: "78701"
  }
}
```

Everything needed to display or process this order is in one document. One read operation retrieves it all.

## What referencing looks like

The same order using references:

```js
// orders collection
{
  _id: ObjectId("..."),
  userId: ObjectId("..."),
  status: "shipped",
  createdAt: ISODate("2024-08-05"),
  itemIds: [ObjectId("..."), ObjectId("...")],
  shippingAddressId: ObjectId("...")
}

// orderItems collection
{ _id: ObjectId("..."), orderId: ObjectId("..."), productId: ObjectId("..."), quantity: 1, price: 999 }
{ _id: ObjectId("..."), orderId: ObjectId("..."), productId: ObjectId("..."), quantity: 2, price: 29 }
```

Displaying an order now requires multiple queries or a `$lookup` aggregation.

## The embedding signals

**Embed when:**

The data is "owned" by the parent and doesn't exist independently. A blog post's tags, an order's line items, a user's address — these don't have a useful identity outside the parent document.

You always read the parent and child together. If every query for a post also needs its comments, embedding makes one query do both.

The child list is bounded and small. MongoDB documents have a 16MB limit. An array that grows indefinitely will eventually hit this. A comments array is dangerous; a "recent 10 comments" array is fine.

The child data doesn't need to be queried independently. You never need to find all comments across all posts; you find comments for a specific post.

```js
// Good embedding candidate: post with tags and metadata
{
  _id: ObjectId("..."),
  title: "How MongoDB works",
  body: "...",
  tags: ["mongodb", "databases", "nosql"],
  author: { name: "Alice", id: ObjectId("...") }, // denormalized for display
  stats: { views: 1420, likes: 83 }
}
```

## The referencing signals

**Reference when:**

The related entity is large and not always needed. A user document shouldn't embed their full order history — that array could contain thousands of items and would be loaded on every `findOne({ email })` call.

The child exists and is queried independently. If you need to query the `orders` collection directly (find all orders over $500, show orders by status), they need to be their own collection.

Many-to-many relationships. A product belongs to many orders; embedding products in orders means updating product info requires touching every order document.

The child data changes frequently. Embedded data is a snapshot at write time. If you embed a product's current price in order items (which you should — you want to record what was charged), that's fine. But if you embed a product's current name and description, every product name change requires updating all orders.

```js
// Good referencing candidate: user → orders
// users collection
{ _id: ObjectId("..."), email: "alice@example.com", name: "Alice" }

// orders collection
{ _id: ObjectId("..."), userId: ObjectId("..."), total: 1057, status: "shipped" }
```

## The hybrid: selective denormalization

Often the best model is neither pure embedding nor pure referencing. Embed the fields you need for display; reference the full entity for detail pages:

```js
// Order embeds just the product name and price at time of purchase
// but references the product ID for linking to the product page
{
  _id: ObjectId("..."),
  userId: ObjectId("..."),
  items: [
    {
      productId: ObjectId("..."),   // reference for linking
      name: "Laptop",               // embedded snapshot for display
      price: 999                    // embedded snapshot — what was charged
    }
  ]
}
```

## The rule of thumb

MongoDB's own documentation offers this guideline:

- **Embed** if the relationship is "has-a" and the child data is always accessed with the parent
- **Reference** if the child data is large, grows unboundedly, or needs to be queried/updated independently

The hardest part is knowing which queries your application will actually run. Model around your read patterns, not your data structure. If you're storing posts and always display the author's name next to the post, embed the author's name. If you need to display the author's full profile, reference the author and do a second query or `$lookup`.

Get this decision right early. Converting from embedded to referenced (or vice versa) in a collection with millions of documents requires a migration that can take hours and must be designed to run without taking the collection offline.

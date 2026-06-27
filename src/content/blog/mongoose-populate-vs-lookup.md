---
title: "Mongoose populate vs $lookup: same result, very different performance."
description: "Mongoose's populate() runs multiple queries in application code. $lookup joins in the database. Understanding the difference prevents N+1 query problems at scale."
pubDate: 2024-08-22
tags: ["Security"]
draft: false
---

Both `populate()` and `$lookup` let you resolve references between collections, but they work completely differently at the database level. Choosing the wrong one is one of the most common MongoDB performance mistakes.

## What populate() does under the hood

`populate()` is an application-level join. When you call it, Mongoose:
1. Runs the original query and gets the documents
2. Collects all the referenced IDs from those documents
3. Runs a second query (`$in`) to fetch the referenced documents
4. Merges them in JavaScript

```js
// These two queries happen:
// 1. db.posts.find({ status: "published" }).limit(10)
// 2. db.users.find({ _id: { $in: [id1, id2, id3, ...] } })

const posts = await Post
  .find({ status: "published" })
  .limit(10)
  .populate("author", "name avatar");
```

This is 2 queries for 1 level of depth. Add another `populate()`:

```js
await Post
  .find({ status: "published" })
  .populate("author", "name avatar")
  .populate("category", "name slug");
```

Now it's 3 queries. Populate deeply nested references:

```js
await Post.find().populate({
  path: "author",
  populate: { path: "organization" }
});
```

This is 3 queries. Fetch 100 posts with nested populates and you could be running hundreds of database round trips.

## The N+1 problem

The N+1 query problem is when you fetch N records and then make one additional query per record. Populate can create this if used naively:

```js
// Classic N+1: fetching author separately for each post
const posts = await Post.find({ status: "published" });
for (const post of posts) {
  post.author = await User.findById(post.authorId); // N extra queries
}
```

Populate avoids the loop by batching into a single `$in` query — which is why it's better than the naive loop. But it still runs multiple round trips, and each has network latency and query overhead.

## What $lookup does

`$lookup` is a server-side join that runs entirely within MongoDB's aggregation pipeline. One network round trip:

```js
const posts = await Post.aggregate([
  { $match: { status: "published" } },
  { $limit: 10 },
  {
    $lookup: {
      from: "users",          // collection name (not model name)
      localField: "authorId", // field in posts
      foreignField: "_id",    // field in users
      as: "author",           // output field name
    },
  },
  {
    $unwind: {
      path: "$author",
      preserveNullAndEmpty: true, // don't drop posts with no author
    },
  },
  {
    $project: {
      title: 1,
      slug: 1,
      "author.name": 1,
      "author.avatar": 1,
      createdAt: 1,
    },
  },
]);
```

The database handles the join. One query, one network round trip. For large result sets, this is significantly faster.

## Multiple $lookup stages

```js
const posts = await Post.aggregate([
  { $match: { status: "published" } },
  {
    $lookup: {
      from: "users",
      localField: "authorId",
      foreignField: "_id",
      as: "author",
    },
  },
  {
    $lookup: {
      from: "categories",
      localField: "categoryId",
      foreignField: "_id",
      as: "category",
    },
  },
  { $unwind: { path: "$author", preserveNullAndEmpty: true } },
  { $unwind: { path: "$category", preserveNullAndEmpty: true } },
]);
```

Still one network round trip, regardless of how many `$lookup` stages you add.

## When populate is fine

Populate is not always wrong. It's appropriate when:

- You're querying a small, bounded number of documents (a single post, a user profile)
- Development speed matters more than raw performance for that endpoint
- The data you're joining is already cached in Mongoose's model layer

```js
// Fine: fetching a single post — 2 queries is negligible
const post = await Post.findById(id).populate("author", "name avatar");
```

## When to use $lookup

- List endpoints that return many documents
- Any time you're joining more than one level deep
- When you need to filter or sort by joined fields

Filtering by a joined field is where `$lookup` really shines:

```js
// Find posts where the author has more than 1000 followers
// This is impossible to express efficiently with populate
const posts = await Post.aggregate([
  {
    $lookup: {
      from: "users",
      localField: "authorId",
      foreignField: "_id",
      as: "author",
    },
  },
  { $unwind: "$author" },
  { $match: { "author.followerCount": { $gt: 1000 } } },
]);
```

With `populate`, you'd have to fetch all posts, then filter in JavaScript — loading far more data than needed.

## Index your $lookup fields

For `$lookup` to be fast, the `foreignField` needs an index. `_id` is always indexed. Any other field used in `foreignField` needs an explicit index:

```js
userSchema.index({ externalId: 1 }); // if used as foreignField in $lookup
```

Without the index, the `$lookup` stage scans the entire foreign collection for every document in the pipeline.

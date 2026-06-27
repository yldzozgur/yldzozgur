---
title: "Prisma vs raw SQL: what you give up and what you gain."
description: "Prisma trades SQL control for developer ergonomics. Understanding exactly what that trade looks like helps you decide when each approach is appropriate."
pubDate: 2026-04-23
tags: ["Databases", "TypeScript"]
draft: false
---

Every ORM makes the same pitch: write less SQL, get more type safety, move faster. Prisma makes that pitch more convincingly than most. But "write less SQL" always means "give up some SQL control." The question is whether the tradeoff is worth it for your use case.

## What Prisma gives you

Prisma's schema file becomes the source of truth for your database structure and your TypeScript types simultaneously.

```prisma
// schema.prisma
model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  author    User     @relation(fields: [authorId], references: [id])
  authorId  String
  tags      Tag[]
  createdAt DateTime @default(now())
}

model User {
  id    String @id @default(cuid())
  email String @unique
  posts Post[]
}
```

From this schema, Prisma generates a client where every query is typed:

```typescript
const prisma = new PrismaClient();

// Return type is inferred: Post & { author: User }
const post = await prisma.post.findUnique({
  where: { id: postId },
  include: { author: true },
});

// TypeScript knows post.author.email exists
console.log(post?.author.email);

// Creating a record — TypeScript validates the shape
const newPost = await prisma.post.create({
  data: {
    title: 'Hello world',
    authorId: user.id,
  },
});
```

No casting, no manually maintained interfaces. When you change the schema and run `prisma generate`, every query that touches a changed field becomes a type error if it's now wrong.

## What Prisma costs you

The moment you need SQL that doesn't fit Prisma's model, you feel the friction.

**Aggregations and window functions.** Prisma supports basic `groupBy` and `count`, but anything involving window functions, CTEs, or complex aggregations requires falling back to `$queryRaw`:

```typescript
// Prisma's groupBy — fine for simple cases
const stats = await prisma.post.groupBy({
  by: ['authorId'],
  _count: { id: true },
  _avg: { viewCount: true },
});

// Anything more complex needs raw SQL
const trending = await prisma.$queryRaw<TrendingPost[]>`
  SELECT
    p.id,
    p.title,
    COUNT(v.id) AS view_count,
    RANK() OVER (PARTITION BY p.author_id ORDER BY COUNT(v.id) DESC) AS rank
  FROM posts p
  LEFT JOIN views v ON v.post_id = p.id
  WHERE v.created_at > NOW() - INTERVAL '7 days'
  GROUP BY p.id, p.title, p.author_id
  HAVING COUNT(v.id) > 100
`;
```

`$queryRaw` returns typed results but the typing is manual — you pass a generic parameter and Prisma trusts you.

**Query optimization.** Prisma generates reasonable SQL, but you can't always control the exact query plan. If a particular query is slow, you might find the generated SQL is doing an unnecessary join or missing a filter hint. With raw SQL you write exactly the query you want.

**Bulk operations.** Prisma's `createMany` doesn't support returning created records on all databases. Large bulk inserts often benefit from `COPY` or multi-value inserts that Prisma doesn't generate.

## Raw SQL with a type layer

One middle ground is using a thin query library like `postgres` or `pg` with manual typing:

```typescript
import postgres from 'postgres';

const sql = postgres(process.env.DATABASE_URL!);

interface PostSummary {
  id: string;
  title: string;
  authorName: string;
  commentCount: number;
}

// You write the SQL; you own the return type
const summaries = await sql<PostSummary[]>`
  SELECT
    p.id,
    p.title,
    u.name AS author_name,
    COUNT(c.id)::int AS comment_count
  FROM posts p
  JOIN users u ON u.id = p.author_id
  LEFT JOIN comments c ON c.post_id = p.id
  GROUP BY p.id, p.title, u.name
  ORDER BY p.created_at DESC
  LIMIT ${limit}
`;
```

You get parameterized queries and template literal safety, but the type accuracy depends on you keeping the interface in sync with the actual query output.

## A practical split

Many production codebases use both. Prisma handles the 80% of queries that are straightforward CRUD operations on single tables or simple relations. Raw SQL handles the 20% that need specific optimization, complex aggregations, or database-specific features.

```typescript
// Prisma for standard operations
const user = await prisma.user.findUnique({ where: { email } });
const posts = await prisma.post.findMany({ where: { authorId: user.id } });

// Raw SQL when the query warrants it
const analytics = await prisma.$queryRaw`
  SELECT date_trunc('day', created_at) AS day, COUNT(*) AS posts
  FROM posts
  WHERE author_id = ${user.id}
  GROUP BY 1
  ORDER BY 1
`;
```

Prisma and raw SQL aren't competing choices — they're tools for different jobs within the same project. The skill is knowing which one a given query deserves.

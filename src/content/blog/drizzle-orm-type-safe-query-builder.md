---
title: "Drizzle ORM: the type-safe query builder that stays close to SQL."
description: "Drizzle gives you TypeScript types over your database queries without hiding the SQL. The mental model stays SQL — the ergonomics become TypeScript."
pubDate: 2026-04-27
tags: ["Databases", "TypeScript"]
draft: false
---

Most ORMs try to abstract SQL away. Drizzle takes the opposite stance: stay close to SQL, but make it fully typed. The result is a query builder that feels familiar to anyone who knows SQL, while catching schema mismatches at compile time.

## Schema as TypeScript

Drizzle schemas are TypeScript files, not a separate DSL or config format.

```typescript
// db/schema.ts
import { pgTable, serial, text, boolean, timestamp, integer } from 'drizzle-orm/pg-core';

export const users = pgTable('users', {
  id: serial('id').primaryKey(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export const posts = pgTable('posts', {
  id: serial('id').primaryKey(),
  title: text('title').notNull(),
  content: text('content'),
  published: boolean('published').default(false).notNull(),
  authorId: integer('author_id').references(() => users.id).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
});
```

From these table definitions, Drizzle infers TypeScript types for select results, insert shapes, and update payloads — all without a separate codegen step.

## Query syntax

Drizzle's query syntax mirrors SQL structure:

```typescript
import { db } from './db';
import { users, posts } from './schema';
import { eq, and, gte, desc, count } from 'drizzle-orm';

// Simple select
const allUsers = await db.select().from(users);
// Type: { id: number; email: string; name: string; createdAt: Date }[]

// With conditions
const recentPosts = await db
  .select({
    id: posts.id,
    title: posts.title,
    authorName: users.name,
  })
  .from(posts)
  .innerJoin(users, eq(posts.authorId, users.id))
  .where(and(
    eq(posts.published, true),
    gte(posts.createdAt, new Date('2026-01-01'))
  ))
  .orderBy(desc(posts.createdAt))
  .limit(20);

// Return type is exactly the shape you selected:
// { id: number; title: string; authorName: string }[]
```

The column references (`posts.id`, `users.name`) are typed. If you rename a column in the schema, every query that references it becomes a compile error.

## Insert, update, delete

```typescript
// Insert — data shape is inferred from the schema
const [newUser] = await db.insert(users).values({
  email: 'alex@example.com',
  name: 'Alex',
}).returning();
// newUser is fully typed

// Update
await db
  .update(posts)
  .set({ published: true })
  .where(eq(posts.id, postId));

// Delete
await db.delete(posts).where(eq(posts.authorId, userId));

// Batch insert
await db.insert(posts).values([
  { title: 'First post', authorId: 1 },
  { title: 'Second post', authorId: 1 },
]);
```

## Relational queries

Drizzle has a separate relational API for defining and querying relations:

```typescript
// db/relations.ts
import { relations } from 'drizzle-orm';
import { users, posts } from './schema';

export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
}));

export const postsRelations = relations(posts, ({ one }) => ({
  author: one(users, {
    fields: [posts.authorId],
    references: [users.id],
  }),
}));

// Query with relations
const usersWithPosts = await db.query.users.findMany({
  with: {
    posts: {
      where: eq(posts.published, true),
      orderBy: desc(posts.createdAt),
    },
  },
});
// Type: (User & { posts: Post[] })[]
```

## Migrations

Drizzle Kit generates migration SQL by diffing your schema against the current database state:

```bash
# Generate a migration
npx drizzle-kit generate

# Apply migrations
npx drizzle-kit migrate
```

The generated migrations are plain SQL files you can review and commit. No migration framework magic, no ORM-specific migration format.

## Drizzle vs Prisma

The practical difference comes down to what you want the abstraction to feel like.

Prisma's API hides SQL — you think in terms of models and relations, and Prisma generates queries. This is productive for CRUD operations but creates friction when you need precise SQL control.

Drizzle's API is SQL with TypeScript types layered over it. If you know what SQL you want to write, Drizzle lets you write essentially that, but with compile-time column name checking and typed results. Aggregations, window functions, and complex joins all work because you're just writing SQL expressions through a typed interface.

```typescript
// Drizzle with a window function — you write what you mean
const ranked = await db.execute(sql`
  SELECT
    id,
    title,
    RANK() OVER (ORDER BY view_count DESC) AS rank
  FROM posts
  WHERE published = true
`);
```

For teams that think in SQL and want types without losing control, Drizzle fits more naturally than Prisma.

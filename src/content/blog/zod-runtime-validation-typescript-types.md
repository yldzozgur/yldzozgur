---
title: "Zod: runtime validation that generates TypeScript types."
description: "TypeScript types vanish at runtime. Zod keeps them alive — and turns your schemas into a single source of truth for both validation and types."
pubDate: 2026-04-16
tags: ["TypeScript", "Validation"]
draft: false
---

TypeScript's type system is a compile-time tool. Once your code runs, the types are gone. If an API response comes back with the wrong shape, or a form input contains unexpected data, TypeScript won't catch it — there's nothing left to catch with.

Zod fills that gap. You define a schema once, use it to validate data at runtime, and get TypeScript types inferred from that same schema automatically.

## Defining schemas and inferring types

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
  role: z.enum(['admin', 'user', 'guest']),
  createdAt: z.string().datetime(),
});

// TypeScript type inferred from the schema — no duplication
type User = z.infer<typeof UserSchema>;

// At runtime, parse() throws if data doesn't match
const user: User = UserSchema.parse(rawApiResponse);

// safeParse() returns a result object instead of throwing
const result = UserSchema.safeParse(rawInput);
if (result.success) {
  console.log(result.data.email); // fully typed
} else {
  console.error(result.error.issues); // structured error list
}
```

The key benefit: `User` is derived from `UserSchema`. You can't accidentally have a type that says one thing and a validator that checks something different. They're the same thing.

## Transforming data during parsing

Zod schemas aren't limited to pure validation. You can transform data as part of the parse step.

```typescript
const ApiResponseSchema = z.object({
  user_id: z.string(),
  full_name: z.string(),
  created_at: z.string().datetime(),
}).transform((data) => ({
  userId: data.user_id,
  fullName: data.full_name,
  createdAt: new Date(data.created_at), // string -> Date
}));

type ParsedResponse = z.infer<typeof ApiResponseSchema>;
// { userId: string; fullName: string; createdAt: Date }
```

The snake_case-to-camelCase conversion and string-to-Date coercion happen automatically during parsing. Your application never touches the raw API shape.

## Composing schemas

Zod schemas compose. You can build complex schemas from simpler pieces.

```typescript
const AddressSchema = z.object({
  street: z.string(),
  city: z.string(),
  country: z.string().length(2), // ISO country code
});

const ContactSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
  address: AddressSchema, // nested schema
  tags: z.array(z.string()).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

// Extend an existing schema
const FullContactSchema = ContactSchema.extend({
  phone: z.string().regex(/^\+[1-9]\d{1,14}$/),
});

// Pick or omit fields
const ContactPreviewSchema = ContactSchema.pick({ name: true, email: true });

type ContactPreview = z.infer<typeof ContactPreviewSchema>;
// { name: string; email: string }
```

## Validating form inputs and API boundaries

The most common use cases are validating form submissions and API request/response bodies.

```typescript
// Next.js API route with Zod validation
const CreatePostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
  tags: z.array(z.string()).max(10),
  publishAt: z.string().datetime().optional(),
});

export async function POST(request: Request) {
  const body = await request.json();
  const result = CreatePostSchema.safeParse(body);

  if (!result.success) {
    return Response.json(
      { errors: result.error.flatten().fieldErrors },
      { status: 400 }
    );
  }

  // result.data is fully typed as CreatePost
  const post = await db.posts.create({ data: result.data });
  return Response.json(post, { status: 201 });
}
```

`flatten()` restructures the error list into field-level errors, which maps cleanly to form validation UI.

## Reusing schemas across the stack

When you share Zod schemas between your frontend and backend (in a monorepo or shared package), you get a single validation definition that both sides use. A schema change automatically propagates to both TypeScript types and runtime checks everywhere it's imported.

```typescript
// packages/schemas/src/post.ts
export const CreatePostSchema = z.object({ ... });
export type CreatePost = z.infer<typeof CreatePostSchema>;

// apps/web/src/components/PostForm.tsx — uses CreatePost type
// apps/api/src/routes/posts.ts — uses CreatePostSchema to validate
```

This is one of Zod's most practical advantages over maintaining separate type declarations and validation logic: there's one file to update, and the change is correct everywhere.

## What Zod doesn't replace

Zod validates structure and types. It doesn't validate business rules — things like "this email address must not already exist in the database" or "this discount code must be currently active." Those checks still belong in your application logic. Zod handles the shape; your domain handles the rules.

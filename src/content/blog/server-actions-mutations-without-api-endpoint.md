---
title: "Server actions: mutations without an API endpoint."
description: "How Next.js Server Actions work, what they replace, the security model, and when they're the right choice over a dedicated API route."
pubDate: 2026-03-26
tags: ["Architecture"]
draft: false
---

Server Actions are async functions that run on the server and can be called directly from client components. They look like regular function calls in your component, but the function body executes on the server -- with direct database access, no API endpoint required.

## The traditional pattern

Before Server Actions, a form submission or mutation in a Next.js app required:

1. An API route (`pages/api/` or `app/api/`)
2. A `fetch` call from the client to that route
3. Server-side logic in the route handler
4. Response parsing and error handling on the client

For simple mutations, this is a lot of boilerplate for what is conceptually "call this function."

## What Server Actions look like

Define a Server Action with `'use server'`:

```typescript
// app/actions.ts
'use server';

import { db } from '@/lib/db';
import { revalidatePath } from 'next/cache';

export async function createPost(formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;

  await db.insert(posts).values({ title, content });

  revalidatePath('/posts');
}
```

Use it in a component:

```tsx
// app/posts/new/page.tsx
import { createPost } from '@/app/actions';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" placeholder="Title" required />
      <textarea name="content" placeholder="Content" />
      <button type="submit">Create Post</button>
    </form>
  );
}
```

No `fetch`, no API route, no event handlers, no state for loading/error. The form's `action` is the Server Action. This works with JavaScript disabled (progressive enhancement) because it's a native form submission under the hood.

## Calling from event handlers

Server Actions aren't limited to form `action` attributes. Call them from event handlers with `useTransition` for pending state:

```tsx
'use client';

import { useTransition } from 'react';
import { deletePost } from '@/app/actions';

function DeleteButton({ postId }: { postId: string }) {
  const [isPending, startTransition] = useTransition();

  return (
    <button
      disabled={isPending}
      onClick={() => startTransition(() => deletePost(postId))}
    >
      {isPending ? 'Deleting...' : 'Delete'}
    </button>
  );
}
```

## The security model

Server Actions are exposed as POST endpoints. The URL is obfuscated (Next.js uses a hash), but they're network-accessible. This has implications:

**Treat inputs as untrusted.** The same as any API route -- validate and sanitize everything. Use Zod:

```typescript
'use server';

import { z } from 'zod';

const CreatePostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
});

export async function createPost(formData: FormData) {
  const result = CreatePostSchema.safeParse({
    title: formData.get('title'),
    content: formData.get('content'),
  });

  if (!result.success) {
    return { error: result.error.flatten() };
  }

  // Proceed with validated data
  await db.insert(posts).values(result.data);
}
```

**Authenticate inside the action.** Never assume the caller is authenticated just because they're calling a Server Action:

```typescript
'use server';

import { getSession } from '@/lib/auth';

export async function deletePost(postId: string) {
  const session = await getSession();
  if (!session) throw new Error('Unauthorized');

  // Verify the user owns this post
  const post = await db.query.posts.findFirst({
    where: eq(posts.id, postId),
  });
  if (post?.userId !== session.user.id) throw new Error('Forbidden');

  await db.delete(posts).where(eq(posts.id, postId));
}
```

## When to use Server Actions vs API routes

**Use Server Actions for:**
- Form submissions and mutations tightly coupled to a single page
- Mutations that only need to be called from your own app
- Simple CRUD operations where the API route would add no value

**Use API routes for:**
- Endpoints consumed by external clients (mobile apps, third parties)
- Webhooks
- Operations that need standard HTTP status codes and responses
- When you want to document and test an explicit API contract

Server Actions collapse the client/server boundary for the common case of "my Next.js app needs to mutate data." For anything that needs to be a real API, keep using route handlers.

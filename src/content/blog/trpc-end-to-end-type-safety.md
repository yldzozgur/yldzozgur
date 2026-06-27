---
title: "tRPC: end-to-end type safety without writing an API spec."
description: "tRPC lets your frontend call backend procedures with full TypeScript types — no REST spec, no codegen, no type drift between client and server."
pubDate: 2026-04-20
tags: ["TypeScript", "REST API"]
draft: false
---

The typical TypeScript API setup has a gap: your backend has types, your frontend has types, but nothing enforces they match. You write a fetch call, cast the response to some interface, and hope the backend hasn't changed. tRPC closes that gap by making the server's type definitions directly available to the client.

## How it works

tRPC is built around a router that defines procedures — either queries (reads) or mutations (writes). The router's type is exported and imported by the client, which uses it to know exactly what procedures exist and what types they accept and return.

```typescript
// server/router.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();

export const appRouter = t.router({
  users: t.router({
    getById: t.procedure
      .input(z.object({ id: z.string() }))
      .query(async ({ input }) => {
        const user = await db.users.findUnique({ where: { id: input.id } });
        if (!user) throw new TRPCError({ code: 'NOT_FOUND' });
        return user;
      }),

    create: t.procedure
      .input(z.object({
        email: z.string().email(),
        name: z.string().min(1),
      }))
      .mutation(async ({ input }) => {
        return db.users.create({ data: input });
      }),
  }),
});

// Export only the type — no runtime code crosses the boundary
export type AppRouter = typeof appRouter;
```

The client imports `AppRouter` as a type-only import. No actual server code runs on the client.

```typescript
// client/trpc.ts
import { createTRPCReact } from '@trpc/react-query';
import type { AppRouter } from '../server/router';

export const trpc = createTRPCReact<AppRouter>();
```

Now calling a procedure from a React component looks like this:

```typescript
function UserProfile({ userId }: { userId: string }) {
  // Fully typed: input validated, return type inferred from the query
  const { data: user, isLoading } = trpc.users.getById.useQuery({ id: userId });

  if (isLoading) return <Spinner />;
  // user is typed as the exact return type of the getById query
  return <div>{user?.name}</div>;
}

function CreateUserForm() {
  const createUser = trpc.users.create.useMutation();

  const handleSubmit = async (formData: FormData) => {
    await createUser.mutateAsync({
      email: formData.get('email') as string,
      name: formData.get('name') as string,
    });
  };

  return <form onSubmit={...}>...</form>;
}
```

If you rename a field on the server, TypeScript immediately shows errors everywhere the client uses that field. There's no schema file to regenerate and no client SDK to update.

## Context and middleware

Procedures can use context — data that's passed to every procedure, typically containing the authenticated user.

```typescript
// Context is built per-request
export const createContext = async ({ req }: { req: Request }) => {
  const session = await getSession(req);
  return { session, db };
};

type Context = Awaited<ReturnType<typeof createContext>>;
const t = initTRPC.context<Context>().create();

// Reusable middleware for protected routes
const isAuthenticated = t.middleware(({ ctx, next }) => {
  if (!ctx.session?.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({ ctx: { ...ctx, user: ctx.session.user } });
});

const protectedProcedure = t.procedure.use(isAuthenticated);

// Protected procedures know ctx.user is defined
const userRouter = t.router({
  updateProfile: protectedProcedure
    .input(z.object({ name: z.string() }))
    .mutation(async ({ input, ctx }) => {
      // ctx.user is guaranteed non-null here
      return db.users.update({
        where: { id: ctx.user.id },
        data: { name: input.name },
      });
    }),
});
```

## Adapters for different runtimes

tRPC procedures aren't tied to HTTP — they're just functions. Adapters connect them to a request handler.

```typescript
// Next.js App Router
import { fetchRequestHandler } from '@trpc/server/adapters/fetch';

export const GET = (req: Request) =>
  fetchRequestHandler({ endpoint: '/api/trpc', req, router: appRouter, createContext });

export const POST = GET;
```

The same router works with Express, Fastify, AWS Lambda, or called directly without HTTP in tests.

## When tRPC fits and when it doesn't

tRPC works best in TypeScript monorepos where the frontend and backend are maintained together. It eliminates the overhead of maintaining a REST spec or running codegen for GraphQL.

It's less appropriate when:

- Your API is consumed by clients you don't control (mobile apps built by another team, third-party integrations). Those consumers need a documented, language-agnostic interface.
- Your team includes developers who aren't working in TypeScript.
- You need fine-grained HTTP control — specific status codes, headers, caching semantics.

For internal TypeScript full-stack apps, tRPC removes an entire category of bugs — the ones where the frontend and backend have quietly drifted apart.

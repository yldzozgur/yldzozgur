---
title: "React Query vs RTK Query: the actual differences."
description: "A concrete comparison of TanStack Query and RTK Query -- what each does well, where they diverge, and how to choose."
pubDate: 2026-04-09
tags: ["Architecture"]
draft: false
---

React Query (TanStack Query) and RTK Query solve the same problem: managing server state in React -- fetching, caching, and synchronizing remote data. They're both good. The differences matter when you're choosing one for a project.

## Mental models

**React Query** is framework-agnostic server state management. It doesn't care where your data comes from or how you fetch it. You give it a query key and an async function; it handles caching, background refetching, and stale-while-revalidate.

**RTK Query** is Redux Toolkit's integrated data-fetching layer. It generates typed hooks from API endpoint definitions and integrates tightly with the Redux store, enabling the tag-based cache invalidation system.

## Basic usage comparison

Both libraries look similar for simple cases:

```tsx
// React Query
import { useQuery } from '@tanstack/react-query';

function PostsList() {
  const { data, isPending, error } = useQuery({
    queryKey: ['posts'],
    queryFn: () => fetch('/api/posts').then(r => r.json()),
  });

  if (isPending) return <Loading />;
  if (error) return <Error />;
  return <List items={data} />;
}
```

```tsx
// RTK Query
import { postsApi } from '@/store/postsApi';

function PostsList() {
  const { data, isLoading, error } = postsApi.useGetPostsQuery();

  if (isLoading) return <Loading />;
  if (error) return <Error />;
  return <List items={data} />;
}
```

The main surface difference: React Query's `queryFn` is inline and arbitrary. RTK Query's endpoint is defined in the API slice, and the hook is generated from that definition.

## Cache invalidation

This is where they diverge most.

**React Query** invalidates by query key:

```typescript
const mutation = useMutation({
  mutationFn: createPost,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['posts'] });
  },
});
```

Straightforward, but you're manually specifying which keys to invalidate in the mutation's success handler. For complex relationships between resources, this can get unwieldy.

**RTK Query** uses the tag system -- queries declare what data they provide, mutations declare what they invalidate, and the library handles the rest automatically. (Covered in depth in the RTK Query cache invalidation post.)

For simple cases, React Query's approach is more direct. For complex APIs with many interconnected resources, RTK Query's tag system tends to scale better because invalidation logic lives with the endpoint definition, not scattered across mutation callbacks.

## Setup and integration

**React Query** setup is minimal:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
    </QueryClientProvider>
  );
}
```

**RTK Query** requires Redux store setup:

```typescript
import { configureStore } from '@reduxjs/toolkit';
import { postsApi } from './postsApi';

const store = configureStore({
  reducer: {
    [postsApi.reducerPath]: postsApi.reducer,
  },
  middleware: getDefaultMiddleware =>
    getDefaultMiddleware().concat(postsApi.middleware),
});
```

If you're not using Redux for anything else, RTK Query's setup overhead is a real consideration. React Query doesn't require Redux.

## Flexibility

React Query is more flexible by design:

- Works with any async function (REST, GraphQL, IndexedDB, anything)
- Works outside React (TanStack Query has Vue, Solid, and Svelte adapters)
- Mutation callbacks are freeform
- Custom fetching logic is easy to add inline

RTK Query is more opinionated:

- Mutations are defined upfront in the slice
- Cache invalidation is declarative and structured
- Strongly typed from endpoint definition to generated hook
- Server state lives in Redux, inspectable in Redux DevTools

## TypeScript

Both have strong TypeScript support. RTK Query's generated hooks carry the exact types from your endpoint definition automatically. React Query requires you to type the `queryFn`'s return value:

```typescript
// React Query
const { data } = useQuery<Post[], Error>({
  queryKey: ['posts'],
  queryFn: fetchPosts, // return type inferred from fetchPosts
});

// RTK Query -- types flow from endpoint definition
const { data } = useGetPostsQuery(); // data: Post[] | undefined, automatically
```

## The choice

**Choose React Query if:**
- You're not using Redux
- You need flexibility in how you fetch (multiple backends, custom logic)
- You want minimal setup
- You're building a non-Next.js app and want framework portability

**Choose RTK Query if:**
- You're already using Redux Toolkit
- You want structured, declarative cache invalidation
- You benefit from server state being in the Redux DevTools
- You're building a large app where consistent endpoint definitions matter

Both are well-maintained and production-proven. Either is a good choice over manual `useEffect` + `useState` data fetching.

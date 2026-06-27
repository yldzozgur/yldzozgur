---
title: "RTK Query cache invalidation: the tags system that keeps UI in sync."
description: "How RTK Query's tag-based cache invalidation works, how to configure it, and the patterns for keeping your UI consistent after mutations."
pubDate: 2026-04-02
tags: ["Architecture"]
draft: false
---

RTK Query is Redux Toolkit's built-in data fetching and caching library. Its cache invalidation model -- based on tags -- is one of its most distinctive features, and getting it right is what separates a UI that stays in sync from one that shows stale data after mutations.

## The problem: keeping data fresh

You fetch a list of posts. A user creates a new post. The list is stale. You need to refetch it.

The naive solution: refetch everything on every mutation. This is slow and wastes bandwidth.

The optimal solution: only refetch data that was actually affected by the mutation.

RTK Query's tags system is how you express which data is affected.

## Defining tags

Tags are strings or `{type, id}` objects. Queries provide tags (they "produce" this data). Mutations invalidate tags (they "affect" this data).

```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const postsApi = createApi({
  reducerPath: 'postsApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),

  // Declare the tag types used in this API
  tagTypes: ['Post'],

  endpoints: builder => ({
    getPosts: builder.query({
      query: () => '/posts',
      // This query's result is tagged with 'Post'
      providesTags: ['Post'],
    }),

    getPost: builder.query({
      query: (id: string) => `/posts/${id}`,
      // This query provides a specific Post tag
      providesTags: (result, error, id) => [{ type: 'Post', id }],
    }),

    createPost: builder.mutation({
      query: body => ({ url: '/posts', method: 'POST', body }),
      // Invalidate all Post tags -- list needs to refresh
      invalidatesTags: ['Post'],
    }),

    updatePost: builder.mutation({
      query: ({ id, ...body }) => ({
        url: `/posts/${id}`,
        method: 'PATCH',
        body,
      }),
      // Only invalidate the specific post that changed
      invalidatesTags: (result, error, { id }) => [{ type: 'Post', id }],
    }),

    deletePost: builder.mutation({
      query: (id: string) => ({ url: `/posts/${id}`, method: 'DELETE' }),
      invalidatesTags: (result, error, id) => [
        { type: 'Post', id },  // invalidate the specific post
        'Post',                 // also invalidate the list
      ],
    }),
  }),
});
```

When `updatePost` runs, it invalidates `{ type: 'Post', id }`. Only queries that provided that specific tag refetch. The posts list (which provides `'Post'` -- the list tag) is unaffected. When `deletePost` runs, it invalidates both the specific post and the list tag, causing both to refetch.

## The LIST pattern

A common pattern: tag the list result with a sentinel `LIST` id to distinguish "the list of posts" from "a specific post":

```typescript
getPosts: builder.query({
  query: () => '/posts',
  providesTags: result =>
    result
      ? [
          ...result.map(({ id }) => ({ type: 'Post' as const, id })),
          { type: 'Post', id: 'LIST' },
        ]
      : [{ type: 'Post', id: 'LIST' }],
}),

createPost: builder.mutation({
  // Invalidating 'LIST' only refetches the list, not every individual post
  invalidatesTags: [{ type: 'Post', id: 'LIST' }],
}),
```

Now `createPost` only invalidates the list. `updatePost` only invalidates the specific post. Efficient and precise.

## Optimistic updates

For mutations that are likely to succeed, you can update the cache immediately and roll back if the server fails:

```typescript
updatePost: builder.mutation({
  query: ({ id, ...patch }) => ({
    url: `/posts/${id}`,
    method: 'PATCH',
    body: patch,
  }),
  async onQueryStarted({ id, ...patch }, { dispatch, queryFulfilled }) {
    const patchResult = dispatch(
      postsApi.util.updateQueryData('getPost', id, draft => {
        Object.assign(draft, patch);
      })
    );
    try {
      await queryFulfilled;
    } catch {
      patchResult.undo(); // roll back on failure
    }
  },
}),
```

The user sees the update immediately. If the server rejects it, the UI reverts. No separate loading state needed for the optimistic update itself.

## Polling and manual invalidation

RTK Query also supports polling and manual cache invalidation:

```tsx
// Poll every 30 seconds
const { data } = useGetPostsQuery(undefined, { pollingInterval: 30000 });

// Force a refetch from anywhere
dispatch(postsApi.util.invalidateTags(['Post']));
```

The tags system is what makes RTK Query's cache coherent rather than eventually consistent. Define your tags precisely and the UI stays in sync with the server automatically.

---
title: "RTK Query vs useEffect: the comparison that changed how I fetch data."
description: "A side-by-side look at fetching data with useEffect versus RTK Query, and why the latter eliminates entire categories of bugs."
pubDate: 2024-12-30
tags: ["Redux", "RTK Query", "React"]
draft: false
---

## The useEffect approach and its hidden costs

For most React developers, data fetching starts with `useEffect`. You write a function, call `fetch`, update state, and move on. It works. But as applications grow, the cracks appear.

```javascript
function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/users/${userId}`)
      .then(res => res.json())
      .then(data => {
        setUser(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [userId]);

  if (loading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  return <div>{user.name}</div>;
}
```

This looks fine. But consider what happens when:

- Two components mount at the same time and both need the same user
- The user navigates away before the fetch completes (stale closure, potential state update on unmounted component)
- You need to refetch after a mutation
- You want to cache the result so a back-navigation doesn't trigger another network request

Each of these is a problem you solve manually, in every component, every time.

## What RTK Query brings to the table

RTK Query is built into Redux Toolkit. You define an API slice once, and every component that needs data shares the same cache automatically.

```javascript
// store/api.js
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  endpoints: builder => ({
    getUser: builder.query({
      query: userId => `/users/${userId}`,
    }),
    updateUser: builder.mutation({
      query: ({ id, ...patch }) => ({
        url: `/users/${id}`,
        method: 'PATCH',
        body: patch,
      }),
      invalidatesTags: ['User'],
    }),
  }),
});

export const { useGetUserQuery, useUpdateUserMutation } = api;
```

The component becomes almost trivial:

```javascript
function UserProfile({ userId }) {
  const { data: user, isLoading, error } = useGetUserQuery(userId);

  if (isLoading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  return <div>{user.name}</div>;
}
```

## The cache is the difference

When `UserProfile` mounts, RTK Query checks its cache for a response keyed to that `userId`. If one exists and is fresh, it returns immediately without a network request. If two components call `useGetUserQuery(42)` at the same time, only one HTTP request goes out. Both components subscribe to the same cache entry.

This deduplication happens automatically. With `useEffect`, you either lift state up, use a context, or fire two requests and hope they return the same data.

## Invalidation after mutations

The cache is only useful if it stays correct. RTK Query handles this with tags. You annotate your queries with `providesTags` and your mutations with `invalidatesTags`. When a mutation completes, every matching cache entry is marked stale and refetched.

```javascript
endpoints: builder => ({
  getUser: builder.query({
    query: id => `/users/${id}`,
    providesTags: (result, error, id) => [{ type: 'User', id }],
  }),
  updateUser: builder.mutation({
    query: ({ id, ...patch }) => ({
      url: `/users/${id}`,
      method: 'PATCH',
      body: patch,
    }),
    invalidatesTags: (result, error, { id }) => [{ type: 'User', id }],
  }),
}),
```

After `updateUser` succeeds, any component displaying that user's data automatically refetches. You do not wire this up manually. There is no "refetch after save" logic scattered across components.

## When useEffect still makes sense

RTK Query is not a universal replacement. If your side effect is not a network request -- subscribing to a WebSocket, reading from localStorage, setting up an event listener -- `useEffect` is the right tool. RTK Query is specifically for data fetching and synchronization with a server.

For anything involving remote state, RTK Query reduces boilerplate, eliminates race conditions by construction, and gives you caching, deduplication, and cache invalidation for free.

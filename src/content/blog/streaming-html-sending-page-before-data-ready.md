---
title: "Streaming HTML: sending the page before all the data is ready."
description: "How HTTP streaming works with React and Next.js, the role of Suspense boundaries, and why it improves Time to First Byte."
pubDate: 2026-03-30
tags: ["Architecture"]
draft: false
---

Traditional server-rendered pages have a waterfall: the server waits for all data to load, renders the complete HTML, and sends it in one response. If one query takes 500ms, the browser waits 500ms before it sees anything. Streaming HTML sends the page in chunks as data becomes available.

## How chunked transfer works

HTTP/1.1 has chunked transfer encoding. Instead of sending a `Content-Length` header and the complete body, the server sends chunks with their size, and the browser renders each chunk as it arrives. The connection stays open until the server sends a final zero-length chunk.

This isn't new. What's new is React's ability to generate that stream -- rendering the shell of a page immediately and flushing data-dependent sections as their promises resolve.

## Suspense as a streaming boundary

React 18's streaming renderer uses `<Suspense>` boundaries to determine what to send immediately and what to hold:

```tsx
// app/dashboard/page.tsx
import { Suspense } from 'react';

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>

      {/* Rendered immediately -- no async data */}
      <Navigation />

      {/* Held until SlowMetrics resolves, fallback sent immediately */}
      <Suspense fallback={<MetricsSkeleton />}>
        <SlowMetrics />
      </Suspense>

      {/* Independent -- resolves on its own timeline */}
      <Suspense fallback={<FeedSkeleton />}>
        <ActivityFeed />
      </Suspense>
    </div>
  );
}
```

What the browser receives:

1. Immediately: the `<h1>`, `<Navigation />`, and both skeleton fallbacks as complete HTML
2. When `SlowMetrics` resolves: a `<script>` tag with the rendered component HTML and instructions to replace the skeleton
3. When `ActivityFeed` resolves: same for the feed section

The browser starts parsing and rendering the shell at step 1. If `SlowMetrics` takes 800ms, the user sees the shell and the skeletons immediately -- not a blank page.

## Server Components and streaming

In Next.js App Router, `async` Server Components are the primary way to introduce data fetching:

```tsx
// This is a Server Component -- it can be async
async function SlowMetrics() {
  const metrics = await db.query.metrics.findMany({
    orderBy: desc(metrics.timestamp),
    limit: 5,
  });

  return (
    <div className="metrics-grid">
      {metrics.map(m => <MetricCard key={m.id} metric={m} />)}
    </div>
  );
}
```

Wrap it in `<Suspense>` and Next.js streams its output when the query completes.

Multiple independent `<Suspense>` boundaries stream in parallel. `SlowMetrics` (800ms query) and `ActivityFeed` (300ms query) both start fetching at the same time. The feed arrives first and streams in at 300ms; the metrics arrive at 800ms. Total time to complete page: 800ms, not 1100ms.

Without streaming, you'd wait for the slowest query before sending anything.

## The TTFB impact

Time to First Byte (TTFB) measures when the browser receives the first byte of the response. With streaming, TTFB is very low -- the shell HTML starts flowing as soon as the server starts rendering. With traditional SSR, TTFB is the time for your slowest query.

For Lighthouse and Core Web Vitals, a low TTFB directly improves LCP (Largest Contentful Paint) because the browser can start parsing HTML and loading resources earlier.

## Loading.tsx and error.tsx

Next.js wraps `loading.tsx` files in a `<Suspense>` boundary automatically:

```tsx
// app/dashboard/loading.tsx -- shown while dashboard/page.tsx fetches data
export default function Loading() {
  return <DashboardSkeleton />;
}
```

Similarly, `error.tsx` files become error boundaries:

```tsx
// app/dashboard/error.tsx
'use client';

export default function Error({ error, reset }: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div>
      <h2>Something went wrong</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

## The practical advice

Put `<Suspense>` boundaries around data-dependent sections, especially slow ones. Keep the shell of the page (navigation, layout, headings) outside `<Suspense>` so it renders immediately. Place independent data fetches in separate `<Suspense>` boundaries so they stream in parallel rather than sequentially.

The user experience goal: never show a blank page. Show a meaningful shell immediately, fill in data as it arrives.

---
title: "Next.js app router: what changed and why it matters."
description: "The key differences between Next.js pages router and app router -- React Server Components, layouts, streaming, and the new data fetching model."
pubDate: 2026-03-12
tags: ["Architecture"]
draft: false
---

Next.js 13 introduced the app router as an alternative to the pages router, and Next.js 14 made it the recommended default. The shift is bigger than a new directory structure. It's a fundamentally different model for how components render, how data is fetched, and how layouts work.

## React Server Components

The biggest change: components in the app router are **Server Components** by default. They render on the server and send HTML to the client. They can be `async`, they can directly `await` database queries or API calls, and they send zero JavaScript to the browser.

```tsx
// app/products/page.tsx -- a Server Component
// No 'use client'. This runs on the server.
async function ProductsPage() {
  const products = await db.query('SELECT * FROM products LIMIT 20');

  return (
    <ul>
      {products.rows.map(p => (
        <li key={p.id}>{p.name} -- ${p.price}</li>
      ))}
    </ul>
  );
}
```

No `useEffect` to fetch data, no loading state management, no client bundle cost for this component. The database query happens on the server; the user gets HTML.

To opt into client-side rendering (for interactivity, hooks, browser APIs), add `'use client'`:

```tsx
'use client';

import { useState } from 'react';

function AddToCart({ productId }: { productId: string }) {
  const [added, setAdded] = useState(false);

  return (
    <button onClick={() => setAdded(true)}>
      {added ? 'Added!' : 'Add to cart'}
    </button>
  );
}
```

The architecture becomes a tree: Server Components compose with Client Components. Server Components can render Client Components; Client Components cannot render Server Components directly.

## Nested layouts

The pages router had `_app.tsx` for global layout -- a single shared wrapper. The app router has nested layouts through `layout.tsx` files:

```
app/
  layout.tsx          <-- root layout (html, body tags)
  dashboard/
    layout.tsx        <-- sidebar, nav for all dashboard pages
    settings/
      layout.tsx      <-- settings-specific tabs
      page.tsx
    analytics/
      page.tsx
```

Each layout wraps its children. The `dashboard/layout.tsx` renders once and persists as you navigate between dashboard pages -- the sidebar doesn't remount. This is what the pages router couldn't do: shared persistent UI that isn't at the root level.

```tsx
// app/dashboard/layout.tsx
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dashboard">
      <Sidebar />          {/* persists across navigation */}
      <main>{children}</main>
    </div>
  );
}
```

## The new data fetching model

The pages router had `getServerSideProps` and `getStaticProps` -- special functions bolted onto pages. The app router replaces both with `async` Server Components and the `fetch` API extended with caching options:

```tsx
async function BlogPost({ params }: { params: { slug: string } }) {
  // Cached indefinitely (like getStaticProps)
  const post = await fetch(`/api/posts/${params.slug}`, {
    cache: 'force-cache'
  }).then(r => r.json());

  // Never cached, fresh on every request (like getServerSideProps)
  const comments = await fetch(`/api/posts/${params.slug}/comments`, {
    cache: 'no-store'
  }).then(r => r.json());

  // Revalidate every 60 seconds
  const relatedPosts = await fetch('/api/posts/related', {
    next: { revalidate: 60 }
  }).then(r => r.json());

  return <PostView post={post} comments={comments} related={relatedPosts} />;
}
```

Multiple `fetch` calls within a layout/page tree that share the same URL are automatically deduplicated by React.

## Streaming with Suspense

Because the app router is built on React 18, it can stream HTML. You wrap slow parts with `<Suspense>` and they're filled in as data arrives -- the page shell renders immediately:

```tsx
import { Suspense } from 'react';

export default function Page() {
  return (
    <>
      <h1>Dashboard</h1>
      <Suspense fallback={<MetricsSkeleton />}>
        <SlowMetrics />   {/* streams in when ready */}
      </Suspense>
      <Suspense fallback={<FeedSkeleton />}>
        <ActivityFeed />  {/* streams in independently */}
      </Suspense>
    </>
  );
}
```

The shell HTML with skeletons arrives immediately. `SlowMetrics` and `ActivityFeed` stream in as their data fetches resolve, without blocking each other.

## The migration question

The pages router still works and isn't being removed. Migrating an existing app to the app router requires rethinking data fetching patterns and moving interactivity to Client Components. For new projects, start with the app router. For existing projects, evaluate based on how much you'd benefit from nested layouts and RSC.

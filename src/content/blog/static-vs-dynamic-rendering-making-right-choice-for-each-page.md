---
title: "Static vs dynamic rendering: making the right choice for each page."
description: "The tradeoffs between static and dynamic rendering, what determines the right choice for a given page, and how modern frameworks handle the decision."
pubDate: 2025-10-06
tags: ["DevOps"]
draft: false
---

Every page in a web application has a rendering strategy. The choice between static and dynamic rendering affects performance, infrastructure cost, data freshness, and deployment complexity. Modern frameworks make both options available per page, but the decision still requires understanding the tradeoffs.

## Static rendering

A statically rendered page is generated at build time. The HTML is produced once, stored as a file, and served identically to every user who requests it. No server computation happens at request time.

The benefits are significant. Response time is a CDN cache lookup away - often single-digit milliseconds. Scaling is trivially simple: CDNs serve files, they do not need database connections or application servers. Cost is low because there is no compute per request.

The constraint: the page content cannot vary by user or time without additional mechanisms. A page generated at build time at 2pm shows 2pm data when served at 11pm.

Static rendering is appropriate for:
- Marketing pages, landing pages, blog posts
- Documentation
- Product pages where data changes infrequently
- Any page where all users should see the same content

In Next.js, a page is statically rendered by default if it does not use any dynamic data:

```jsx
// This page is static: no request-time data dependencies
export default function AboutPage() {
  return <main><h1>About Us</h1><p>Founded in 2020...</p></main>;
}
```

For pages that use data but can be generated statically:

```jsx
// Next.js App Router: static by default, runs at build time
async function BlogPost({ params }) {
  const post = await fetch(`https://cms.example.com/posts/${params.slug}`, {
    next: { revalidate: 3600 } // Regenerate every hour
  }).then(r => r.json());

  return <article>{post.content}</article>;
}

// Generate static paths at build time
export async function generateStaticParams() {
  const posts = await fetchAllPosts();
  return posts.map(post => ({ slug: post.slug }));
}
```

`generateStaticParams` pre-generates pages for all known slugs at build time. New slugs are generated on first request and cached.

## Dynamic rendering

A dynamically rendered page is generated per request. The server runs code, fetches data, and produces HTML specific to that request. Response time includes server computation and data fetching.

Dynamic rendering is necessary when:
- The page content depends on the user's identity (dashboard, account page)
- The page depends on real-time data (live prices, current inventory)
- The page reads request-specific information (cookies, geolocation, query parameters)

```jsx
// This page must be dynamic: reads user-specific data
import { cookies } from 'next/headers';

async function DashboardPage() {
  const cookieStore = cookies();
  const sessionId = cookieStore.get('session');
  
  const user = await fetchUserFromSession(sessionId);
  const stats = await fetchUserStats(user.id);
  
  return (
    <main>
      <h1>Welcome back, {user.name}</h1>
      <StatsGrid stats={stats} />
    </main>
  );
}
```

In Next.js App Router, accessing `cookies()`, `headers()`, or `searchParams` automatically opts the page into dynamic rendering.

## Incremental Static Regeneration

ISR is the middle ground: pages are statically generated and cached, but they regenerate automatically after a time-to-live expires or on demand via an API call.

```jsx
async function ProductPage({ params }) {
  const product = await fetch(`/api/products/${params.id}`, {
    next: { revalidate: 60 } // Stale after 60 seconds
  }).then(r => r.json());

  return <ProductDetail product={product} />;
}
```

The first request after TTL expiry triggers a background regeneration. Users see the previous version until the new one is ready. This gives you near-static performance with data freshness measured in seconds or minutes.

On-demand revalidation updates a page immediately when data changes:

```javascript
// Called when a product is updated in the CMS
import { revalidatePath } from 'next/cache';

export async function updateProduct(id, data) {
  await db.product.update({ where: { id }, data });
  revalidatePath(`/products/${id}`); // Invalidate the cached page
}
```

## The decision framework

Ask: does every user see the same thing?

If yes, static is the right choice. Use ISR if the content changes over time.

If no (content is user-specific or real-time), dynamic rendering is required.

For pages that are mostly static with small dynamic sections, consider static rendering with client-side data fetching for the dynamic parts:

```jsx
// The page shell is static
async function ProductPage({ params }) {
  const product = await getProduct(params.id); // Static data, build-time or cached
  
  return (
    <main>
      <ProductDetails product={product} />
      <PriceDisplay productId={params.id} /> {/* Client component: fetches live price */}
    </main>
  );
}
```

The static product information is delivered instantly. The live price fetches on the client after the page loads. Users see content immediately; the dynamic part loads without blocking.

Performance and user experience follow directly from the rendering decision. Static pages are fast by default. Dynamic pages require deliberate optimization to be fast.

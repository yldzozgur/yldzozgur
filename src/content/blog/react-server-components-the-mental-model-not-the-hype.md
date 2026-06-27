---
title: "React Server Components: the mental model, not the hype."
description: "What React Server Components actually are, how they differ from client components, and when to use each one."
pubDate: 2025-10-02
tags: ["DevOps"]
draft: false
---

React Server Components (RSC) arrived with significant hype and an equal amount of confusion. The confusion mostly comes from conflating them with server-side rendering, which they are not, and from unclear mental models about what "server" and "client" mean in this context.

## The key distinction

In a standard React application, all components run in the browser. They fetch data, maintain state, respond to events, all in JavaScript executing on the user's machine.

React Server Components run on the server - the component's code executes in the server process, has access to the server's resources (database, filesystem, environment variables), and never ships its code to the browser.

Server Components are not server-side rendering. SSR takes React components and renders them to HTML on the server. The components still run in the browser for hydration. Server Components are a different model: they render on the server and their output (a serialized component tree) is sent to the client. They never execute on the client at all.

## What Server Components can and cannot do

Server Components can:
- Directly access databases, filesystem, and APIs without exposing credentials
- Import large libraries without adding to the client bundle
- Render synchronously with `async/await` data fetching

Server Components cannot:
- Use state (`useState`, `useReducer`)
- Use effects (`useEffect`)
- Use browser APIs
- Add event listeners
- Use React context (as consumers)

```jsx
// A Server Component
// No 'use client' directive = Server Component by default (in Next.js App Router)

import { db } from '@/lib/database';

async function ProductList() {
  // Direct database access - credentials never exposed to client
  const products = await db.query('SELECT * FROM products WHERE active = true');
  
  return (
    <ul>
      {products.map(product => (
        <li key={product.id}>{product.name} - ${product.price}</li>
      ))}
    </ul>
  );
}
```

This component fetches data directly from the database. The `db` module, with its connection credentials, is never sent to the browser. The SQL query executes on the server. The client receives HTML.

## Client Components

Client Components are traditional React components. They use state, effects, and event handlers. In the Next.js App Router, a file must explicitly opt into client behavior:

```jsx
'use client'; // This directive marks the component and its dependencies as client code

import { useState } from 'react';

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('');
  
  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => e.key === 'Enter' && onSearch(query)}
    />
  );
}
```

## Composing them together

Server and Client Components compose. A Server Component can include a Client Component. A Client Component cannot include a Server Component (because the client has no server context), but it can receive Server Component output as `children`.

```jsx
// page.tsx - Server Component
import { db } from '@/lib/database';
import { SearchBar } from './SearchBar'; // Client Component
import { ProductGrid } from './ProductGrid'; // Server Component

async function ProductsPage({ searchParams }) {
  const query = searchParams.q ?? '';
  const products = await db.product.findMany({
    where: { name: { contains: query } }
  });

  return (
    <main>
      <SearchBar />  {/* Client: needs interactivity */}
      <ProductGrid products={products} />  {/* Server: just renders data */}
    </main>
  );
}
```

The `SearchBar` is a Client Component with state and event handlers. The `ProductGrid` is a Server Component that receives data as props and renders HTML. The SearchBar's JavaScript runs in the browser. The ProductGrid's code does not.

## The bundle size benefit

Server Components do not add to the JavaScript bundle. A Server Component that imports a 200KB markdown parsing library sends zero bytes of that library to the client. The markdown is parsed on the server and HTML is sent.

This is the concrete bundle benefit: any library used only in Server Components is excluded from the client bundle entirely.

## When to use each

Use Server Components (the default) when:
- The component fetches data from a database or API
- The component uses sensitive environment variables or credentials
- The component has no interactivity
- The component uses a large library for data processing

Use Client Components when:
- The component uses `useState` or `useReducer`
- The component uses browser events (`onClick`, `onChange`)
- The component uses browser APIs (`localStorage`, `window`)
- The component uses `useEffect`

The mental model: Server Components are for data and rendering. Client Components are for interactivity. Push Client Components to the leaves of the component tree where possible.

---
title: "React.lazy and Suspense: loading code only when you need it."
description: "How code splitting with React.lazy and Suspense works, how to apply it to routes and heavy components, and what to watch out for."
pubDate: 2024-12-16
tags: ["React"]
draft: false
---

By default, a React application bundles all of its JavaScript into a single file (or a few files). Users download the entire bundle upfront, including code for pages they may never visit. Code splitting lets you break the bundle into smaller pieces that load on demand. `React.lazy` and `Suspense` are React's built-in tools for this.

## The problem with a single bundle

A typical React application with a dashboard, settings page, admin panel, and various heavy libraries can produce a 1-2 MB JavaScript bundle. Users visiting the login page download the entire bundle before seeing anything. The admin panel code downloads for every user, including those who never have admin access.

Code splitting solves this by deferring the load of code until it is actually needed.

## React.lazy basics

`React.lazy` takes a function that calls a dynamic `import()` and returns a component that React will load on demand:

```jsx
import { lazy, Suspense } from 'react';

// The import() call happens when the component is first rendered
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
```

`React.lazy` requires its argument to return a promise that resolves to a module with a default export that is a React component.

## Suspense: showing a fallback while loading

When a lazy component is loading, React needs something to show. `Suspense` provides the fallback:

```jsx
function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Dashboard />
    </Suspense>
  );
}
```

React renders the fallback while the `Dashboard` chunk is downloading. Once the download completes, React swaps the fallback for the component.

## Route-based code splitting

The most impactful place to apply code splitting is at the route level. Each route becomes its own chunk, downloaded when the user navigates to it:

```jsx
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

const HomePage = lazy(() => import('./pages/HomePage'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));

function App() {
  return (
    <Suspense fallback={<PageLoadingSpinner />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Suspense>
  );
}
```

One `Suspense` boundary wrapping the entire route tree is sufficient. React will show the fallback whenever any lazy route is loading.

## Splitting heavy components

Route-level splitting handles most cases, but individual heavy components can also be lazy-loaded. A rich text editor, a chart library, or a PDF viewer might add hundreds of kilobytes. Load them only when they're displayed:

```jsx
const RichTextEditor = lazy(() => import('./RichTextEditor'));
const RevenueChart = lazy(() => import('./RevenueChart'));

function PostEditor({ showChart }) {
  return (
    <div>
      <Suspense fallback={<div>Loading editor...</div>}>
        <RichTextEditor />
      </Suspense>

      {showChart && (
        <Suspense fallback={<div>Loading chart...</div>}>
          <RevenueChart />
        </Suspense>
      )}
    </div>
  );
}
```

## Named exports with lazy

`React.lazy` only works with default exports. If your component uses a named export, wrap it:

```jsx
// MyComponent.jsx has: export function MyComponent() {}

const MyComponent = lazy(() =>
  import('./MyComponent').then(module => ({ default: module.MyComponent }))
);
```

## Preloading chunks

By default, a chunk downloads when the component is first rendered. You can preload it earlier by calling the dynamic import manually, before the component renders:

```jsx
// Start downloading the Dashboard chunk when the user hovers over the link
function NavLink() {
  const handleMouseEnter = () => {
    import('./pages/Dashboard'); // Kicks off the download
  };

  return (
    <Link to="/dashboard" onMouseEnter={handleMouseEnter}>
      Dashboard
    </Link>
  );
}
```

The download begins on hover. By the time the user clicks, the chunk may already be cached, making the navigation feel instant.

## Suspense boundaries and error handling

If a lazy component fails to load (network error, chunk not found), the error propagates up to the nearest error boundary. Combine Suspense with an error boundary for robust handling:

```jsx
import { ErrorBoundary } from 'react-error-boundary';

function AppRoutes() {
  return (
    <ErrorBoundary fallback={<p>Failed to load page. Refresh to try again.</p>}>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          {/* lazy routes */}
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
```

## Checking the impact

To verify that code splitting is working, inspect the network tab in Chrome DevTools and filter by JS. Navigate between routes and watch for new chunk files downloading. Bundlers typically name chunks with a hash: `Dashboard.abc123.js`.

You can also use tools like `webpack-bundle-analyzer` or Vite's `rollup-plugin-visualizer` to see which modules are in which chunks before and after splitting.

Route-based splitting on a moderately sized application often reduces the initial bundle by 40-60%, which directly translates to faster first-page loads, particularly on mobile networks.

---
title: "Code splitting at the route level: loading less on every page."
description: "What code splitting is, how route-level splitting works in React, and how to measure whether it's reducing your initial load."
pubDate: 2025-09-29
tags: ["DevOps"]
draft: false
---

A single-page application bundled without code splitting ships all of your code to every user on the first page load. A user visiting the homepage downloads the code for the admin dashboard, the settings panel, and every other route - code they may never use in that session.

Code splitting solves this by splitting the bundle into separate chunks loaded on demand.

## How it works

Without code splitting, the bundler produces one large JavaScript file. With code splitting, it produces a small initial chunk and many smaller chunks, one per split point. The initial chunk contains the code needed to render the first page. The route chunks are loaded when the user navigates to that route.

The browser fetches code only when it is needed. A user on the homepage does not download the admin dashboard code.

## Route-level splitting in React

React's `lazy` and `Suspense` are the mechanism for dynamic imports in React:

```jsx
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

// These components are loaded on-demand, not in the initial bundle
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
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

`lazy(() => import('./pages/Dashboard'))` creates a component that, when first rendered, triggers a dynamic import. The browser fetches the chunk for `Dashboard.js`. Until it arrives, the `Suspense` fallback is shown.

After the first visit to `/dashboard`, the browser caches the chunk. Subsequent navigations are instant.

## What gets split where

The natural split points are routes, but code splitting can go further:

**Heavy third-party libraries.** A rich text editor, a chart library, or a PDF renderer that is only used on one page should be split:

```jsx
const RichEditor = lazy(() => import('./RichEditor')); // which imports Tiptap
const AnalyticsChart = lazy(() => import('./AnalyticsChart')); // which imports Recharts
```

These libraries can be hundreds of kilobytes. Deferring their load to pages that need them reduces the initial bundle significantly.

**Modal and dialog content.** Large modals with significant logic do not need to be in the initial bundle:

```jsx
const [showBillingModal, setShowBillingModal] = useState(false);
const BillingModal = lazy(() => import('./BillingModal'));

return (
  <>
    <button onClick={() => setShowBillingModal(true)}>Manage Billing</button>
    {showBillingModal && (
      <Suspense fallback={<ModalSkeleton />}>
        <BillingModal onClose={() => setShowBillingModal(false)} />
      </Suspense>
    )}
  </>
);
```

## Preloading for faster navigation

Dynamic imports introduce a loading delay on the first navigation to a route. Prefetching the chunk before navigation eliminates the delay:

```jsx
// Prefetch when the user hovers over a link
function NavLink({ to, children }) {
  const prefetch = () => {
    if (to === '/dashboard') import('./pages/Dashboard');
    if (to === '/settings') import('./pages/Settings');
  };

  return (
    <Link to={to} onMouseEnter={prefetch}>
      {children}
    </Link>
  );
}
```

When the user hovers over "Dashboard" in the navigation, the browser starts downloading the dashboard chunk. By the time they click, the chunk is ready.

React Router's `<Link>` component in newer versions handles prefetching automatically. Next.js prefetches all linked routes that are in the viewport by default.

## Measuring the impact

Open Chrome DevTools, go to the Network tab, filter by JavaScript, and reload the page. Note the total JS downloaded. Then navigate to a few routes and watch the additional chunks load.

Use the Coverage tab (Shift+Ctrl+P -> "Show Coverage") to see how much of the loaded JavaScript is actually executed on each page. High unused code percentage on the initial load indicates code splitting opportunities.

Bundle analyzer tools (`webpack-bundle-analyzer`, `vite-bundle-visualizer`) show which modules are in which chunks:

```bash
# Vite
npm install --save-dev rollup-plugin-visualizer

# vite.config.js
import { visualizer } from 'rollup-plugin-visualizer';
export default { plugins: [visualizer({ open: true })] };
```

Before and after bundle size for the initial chunk is the metric. A 40% reduction in initial JS is common after applying route-level code splitting to an application that previously had none.

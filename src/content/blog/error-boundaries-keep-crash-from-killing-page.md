---
title: "Error boundaries: the component that keeps one crash from killing the page."
description: "How error boundaries work, how to implement one, and where to place them so a single component crash doesn't take down the entire React application."
pubDate: 2024-12-02
tags: ["React"]
draft: false
---

When a React component throws an error during rendering, the entire component tree unmounts by default. The user sees a blank page. Error boundaries are class components that catch errors from their children and render a fallback UI instead of propagating the crash.

## Why only class components

Error boundaries must be class components. This is the one React feature that doesn't have a hook equivalent. The reason is historical: the two lifecycle methods that enable error boundaries (`componentDidCatch` and `getDerivedStateFromError`) were added before hooks existed and haven't been reimplemented as hooks.

In practice, you write one error boundary class, put it in a file, and use it as a component everywhere. You don't need to understand class components deeply to use it.

## A minimal error boundary

```jsx
import { Component } from 'react';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    // Called during rendering when a child throws
    // Update state to show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Called after the error is caught
    // Good place to log to an error tracking service
    console.error('Error boundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <p>Something went wrong.</p>;
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
```

Usage:

```jsx
<ErrorBoundary fallback={<p>The chart failed to load.</p>}>
  <RevenueChart data={data} />
</ErrorBoundary>
```

If `RevenueChart` throws for any reason during render, the error boundary catches it and shows the fallback. The rest of the page is unaffected.

## Where to place error boundaries

The key decision is granularity. One error boundary around the entire app catches everything but shows a blank page fallback for any error. Many targeted error boundaries isolate crashes to specific sections.

**Coarse-grained (top-level only):**
```jsx
<ErrorBoundary fallback={<AppErrorPage />}>
  <App />
</ErrorBoundary>
```

This prevents blank pages but is a blunt instrument. A broken sidebar crashes the entire UI.

**Fine-grained (per section):**
```jsx
function Dashboard() {
  return (
    <div className="dashboard">
      <ErrorBoundary fallback={<p>Stats unavailable.</p>}>
        <StatsPanel />
      </ErrorBoundary>
      <ErrorBoundary fallback={<p>Chart failed to load.</p>}>
        <RevenueChart />
      </ErrorBoundary>
      <ErrorBoundary fallback={<p>Activity feed unavailable.</p>}>
        <ActivityFeed />
      </ErrorBoundary>
    </div>
  );
}
```

Each section fails independently. A broken chart doesn't affect the stats panel or the activity feed.

A reasonable strategy: error boundaries at the route level (so a broken page doesn't crash the entire app) and additional boundaries around sections that fetch data or render dynamic content.

## Resetting after an error

The fallback UI sometimes needs a way to let the user retry. The error boundary needs a reset mechanism:

```jsx
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
    this.reset = this.reset.bind(this);
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  reset() {
    this.setState({ hasError: false });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div>
          <p>Something went wrong.</p>
          <button onClick={this.reset}>Try again</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

Calling `reset` sets `hasError` back to false, which causes the boundary to re-render its children. If the error was transient (a network issue, a race condition), this gives the user a chance to recover without a full page reload.

## Using react-error-boundary

The `react-error-boundary` package provides a well-tested error boundary component with a clean API so you don't need to write the class yourself:

```bash
npm install react-error-boundary
```

```jsx
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div role="alert">
      <p>Something went wrong:</p>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

<ErrorBoundary
  FallbackComponent={ErrorFallback}
  onError={(error, info) => logErrorToService(error, info)}
  onReset={() => {
    // Optional: reset any application state that caused the error
  }}
>
  <RevenueChart data={data} />
</ErrorBoundary>
```

It also provides a `useErrorBoundary` hook that lets you trigger the boundary from inside a child component, useful for catching errors in async code that wouldn't be caught by the render boundary.

## What error boundaries don't catch

Error boundaries only catch errors that occur during React's rendering and lifecycle methods. They do not catch:

- Errors in event handlers (use try/catch in the handler)
- Errors in async code (`setTimeout`, `fetch` callbacks)
- Errors in server-side rendering
- Errors thrown by the error boundary itself

For async errors, catch them where they happen and store the error in state. If the error state triggers a rendering error, the boundary will catch the resulting throw.

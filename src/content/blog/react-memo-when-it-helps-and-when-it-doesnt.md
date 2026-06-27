---
title: "React.memo: when it helps and when it makes things worse."
description: "How React.memo works, the cases where it actually improves performance, and the common misuse that wastes memory without helping."
pubDate: 2026-03-19
tags: ["Architecture"]
draft: false
---

`React.memo` is a higher-order component that skips re-rendering if props haven't changed. It sounds like a straightforward optimization. In practice, it's overused, often does nothing useful, and can occasionally make things slower.

## How React renders without memo

React re-renders a component when its parent re-renders. That's the default. It doesn't matter whether the props changed -- a parent re-render triggers a child re-render.

```tsx
function Parent() {
  const [count, setCount] = useState(0);
  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>Count: {count}</button>
      <ExpensiveChild value="static" />  {/* re-renders on every click */}
    </>
  );
}
```

`ExpensiveChild` receives the same `value` prop every time, but it still re-renders because `Parent` re-renders.

## What React.memo does

`React.memo` wraps a component and adds a shallow comparison of props before rendering:

```tsx
const ExpensiveChild = React.memo(function ExpensiveChild({ value }: { value: string }) {
  // Expensive computation
  return <div>{processExpensiveData(value)}</div>;
});
```

Now `ExpensiveChild` only re-renders when `value` changes. The comparison is shallow: primitive values are compared by value, objects and functions by reference.

## The three conditions for memo to help

**1. The component is actually expensive to render.**

React's rendering is fast. A component that renders a few elements and does no heavy computation takes microseconds. Wrapping it in `memo` adds a shallow comparison on every parent render. If the render itself takes 0.1ms and the comparison takes 0.05ms, you've saved 0.05ms -- probably not measurable.

`React.memo` pays off when the component is genuinely slow: complex SVG rendering, a large list, a data visualization, or heavy computation in the render body.

**2. The props are stable.**

If props change on every render (because the parent creates new objects or functions), memo does nothing -- every comparison says "props changed" and the child renders anyway.

```tsx
function Parent() {
  const [count, setCount] = useState(0);

  // New object reference on every render -- memo does nothing
  const config = { threshold: 10 };

  return <MemoizedChild config={config} />;
}
```

Fix this with `useMemo` (for objects) or `useCallback` (for functions):

```tsx
const config = useMemo(() => ({ threshold: 10 }), []); // stable reference
const handleClick = useCallback(() => doSomething(), []); // stable reference
```

**3. The parent re-renders frequently.**

If the parent only re-renders rarely, the overhead of memo is negligible but so is the benefit. Memo helps most when a parent state updates frequently (like a counter or a search input) and a child's props are unrelated to that state.

## When memo makes things worse

**Unnecessary memoization of cheap components.** Adding `React.memo` to every component is cargo-culting. The comparison has a cost. For cheap components, the comparison can cost more than the avoided render.

**Props that always change.** If a component's props include unstable object or function references, memo runs the comparison (cost) and finds they changed (no benefit) on every render. Worse than no memo.

**Breaking intentional renders.** Sometimes you want a child to re-render when a parent re-renders even if props haven't changed. Memo prevents this and can cause stale data bugs if you're not careful.

## The right approach

Profile first. Chrome DevTools' React profiler shows which components are rendering and how long each render takes. Optimize based on actual data.

When you do reach for memo, also check whether `useMemo` and `useCallback` are needed to stabilize the props you're passing down. Memo without stable props is useless.

```tsx
// Useful memo: expensive component with stable props
const DataGrid = React.memo(function DataGrid({ rows, columns }) {
  // Heavy rendering logic
});

function Dashboard() {
  const [filter, setFilter] = useState('');

  // rows and columns are stable (from a stable source)
  const rows = useData(filter);    // assume this returns a stable reference
  const columns = useMemo(() => buildColumns(), []); // stable

  return <DataGrid rows={rows} columns={columns} />;
}
```

The component is expensive (a data grid), the parent updates frequently (filter changes), and the props are stable. That's the scenario where memo earns its keep.

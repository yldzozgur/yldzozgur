---
title: "useMemo and useCallback: the optimization you're probably adding too early."
description: "What useMemo and useCallback actually do, when they help, and why adding them everywhere makes your code slower and harder to read."
pubDate: 2024-11-14
tags: ["React"]
draft: false
---

`useMemo` and `useCallback` are optimization hooks. They are not utilities you reach for by default. Adding them throughout a codebase without measuring first is a common pattern that adds overhead, complicates code, and in many cases makes performance worse.

## What they do

Both hooks cache a value across renders and only recompute it when specified dependencies change.

`useMemo` caches the result of a function call:

```jsx
const sortedList = useMemo(() => {
  return [...items].sort((a, b) => a.name.localeCompare(b.name));
}, [items]);
```

`useCallback` caches the function reference itself:

```jsx
const handleSubmit = useCallback((event) => {
  event.preventDefault();
  submitForm(formData);
}, [formData]);
```

`useCallback(fn, deps)` is equivalent to `useMemo(() => fn, deps)`. They exist separately only because caching a function reference is a common enough use case to warrant a dedicated hook.

## The cost of memoization

Every `useMemo` and `useCallback` call has a cost:

1. React has to store the cached value.
2. React has to compare dependencies on every render to decide whether to return the cache or recompute.
3. The code becomes more verbose and harder to follow.

For cheap computations, the comparison overhead often exceeds the computation cost. You are optimizing away a few microseconds and adding tens of microseconds of bookkeeping.

## When they actually help

There are two legitimate use cases.

**Expensive computations.** If a calculation is genuinely slow (filtering and sorting thousands of items, running a regex against a large string, processing a complex data structure), `useMemo` avoids rerunning it on every render:

```jsx
// Worth memoizing: O(n log n) sort over thousands of records
const processedData = useMemo(() => {
  return largeDataset
    .filter(row => row.active)
    .sort((a, b) => b.score - a.score)
    .map(row => ({ ...row, rank: computeRank(row) }));
}, [largeDataset]);
```

**Stable references for React.memo children.** If a child component is wrapped in `React.memo`, it only re-renders when its props change by reference. If the parent passes a new function or object reference on every render (even with the same values), `React.memo` provides no benefit. `useCallback` and `useMemo` create stable references:

```jsx
const Parent = () => {
  const [count, setCount] = useState(0);

  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []); // Stable reference - doesn't change between renders

  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>Increment</button>
      <MemoizedChild onClick={handleClick} /> {/* Won't re-render on count change */}
    </>
  );
};

const MemoizedChild = React.memo(({ onClick }) => {
  console.log('MemoizedChild rendered');
  return <button onClick={onClick}>Click me</button>;
});
```

Note the requirement: this only matters if `MemoizedChild` is actually expensive to render. If it renders in under a millisecond, wrapping it in `React.memo` and stabilizing props with `useCallback` saves less than a millisecond at the cost of additional code complexity.

## The three questions to ask before memoizing

1. **Is this computation actually slow?** Measure it with React DevTools Profiler or `console.time`. If it doesn't show up as a bottleneck, memoization is not helping.

2. **Is this component actually re-rendering too often?** React DevTools has a "Highlight updates" option that shows when components re-render. If a component renders rarely, there is nothing to optimize.

3. **Does the child depend on a stable reference?** If you're not using `React.memo` on the receiving component, `useCallback` for its callback props does nothing.

## Common misuses

```jsx
// Useless - primitive value, no benefit
const doubled = useMemo(() => count * 2, [count]);
// Just write: const doubled = count * 2;

// Useless - the function isn't passed to a memoized child
const handleChange = useCallback((e) => {
  setValue(e.target.value);
}, []);
// Just write: const handleChange = (e) => setValue(e.target.value);

// Useless - the child isn't wrapped in React.memo anyway
const options = useMemo(() => ({ color: 'blue' }), []);
<NonMemoizedChild options={options} /> // Re-renders regardless
```

## The correct approach

Write components without memoization first. Use React DevTools Profiler to find actual bottlenecks. Apply `useMemo`, `useCallback`, and `React.memo` surgically to the components that the profiler identifies as slow.

This order matters. Code written for correctness first and then optimized based on measurement is easier to understand and more reliably fast than code written with speculative optimizations throughout.

For most components in most applications, the unmemoized version is fast enough that the question never comes up. React's reconciler is highly optimized. Component functions that do simple prop reads and return JSX run in microseconds. Memoizing them does not make your application noticeably faster, but it does make the code harder to read and maintain.

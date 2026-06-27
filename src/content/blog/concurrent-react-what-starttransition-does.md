---
title: "Concurrent React: what startTransition actually does."
description: "How React's concurrent features work, what startTransition is for, and the difference between urgent and non-urgent state updates."
pubDate: 2026-03-23
tags: ["Architecture"]
draft: false
---

React 18 introduced concurrent rendering: the ability to interrupt, pause, and resume rendering work. The most developer-facing part of this is `startTransition`. Understanding what it does requires understanding why it exists.

## The problem: everything is urgent

Before concurrent React, every `setState` call triggered a render that ran to completion before the browser could do anything else -- paint a frame, respond to input, or run other JavaScript.

This is fine for small updates. For expensive renders, it causes jank: type in a search box, triggering a re-render of 1000 filtered results, and the browser can't update the input's value until the expensive render finishes. The input feels laggy even though nothing is actually slow -- the render is blocking.

## Urgent vs non-urgent updates

React 18 introduces a distinction:

- **Urgent updates:** Things that should happen immediately because users expect instant feedback. Typing in an input, clicking a button. These should never be delayed.
- **Transition updates:** Things that can be deferred. Updating search results, navigating to a new view, filtering a list. A small delay is acceptable.

`startTransition` marks a state update as non-urgent:

```tsx
import { useState, startTransition } from 'react';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;

    // Urgent: update the input immediately
    setQuery(value);

    // Non-urgent: updating results can wait
    startTransition(() => {
      setResults(filterResults(value));
    });
  }

  return (
    <>
      <input value={query} onChange={handleChange} />
      <ResultsList results={results} />
    </>
  );
}
```

The input value updates immediately (urgent). The results update is marked as a transition. If a new keystroke arrives before the results render is complete, React can interrupt the results render, process the urgent input update, and restart the results render with the new query.

## The useTransition hook

`startTransition` is a plain function. `useTransition` gives you a `isPending` boolean to show a loading indicator while the transition is in progress:

```tsx
import { useState, useTransition } from 'react';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isPending, startTransition] = useTransition();

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    startTransition(() => {
      setResults(filterResults(e.target.value));
    });
  }

  return (
    <>
      <input value={query} onChange={handleChange} />
      {isPending && <Spinner />}
      <ResultsList results={results} />
    </>
  );
}
```

The spinner shows while the results render is pending and disappears when it commits. The user sees a responsive input and a loading indicator rather than a frozen UI.

## useDeferredValue

`useDeferredValue` is the complementary hook for when you can't control where a state update originates -- for example, if the value comes from a prop:

```tsx
import { useDeferredValue } from 'react';

function SearchResults({ query }: { query: string }) {
  const deferredQuery = useDeferredValue(query);
  // deferredQuery lags behind query -- updates are deferred

  const results = useMemo(
    () => filterResults(deferredQuery),
    [deferredQuery]
  );

  return <ResultsList results={results} />;
}
```

When `query` changes rapidly (every keystroke), `deferredQuery` trails behind. The expensive `filterResults` computation only runs with the deferred value, keeping the parent rendering fast.

## What concurrent React actually means for rendering

In concurrent mode, React can:

1. **Interrupt** a render in progress when a higher-priority update arrives
2. **Restart** the interrupted render after processing the urgent update
3. **Reuse** previously computed work where possible

The render phase is now "interruptible." The commit phase (when React actually updates the DOM) is still synchronous -- you'll never see a half-committed update.

This requires components to be pure and safe to render multiple times with the same props -- React may render a component multiple times before committing. Side effects belong in `useEffect`, not in the render body.

## When to use it

Use `startTransition` when:
- A state update triggers an expensive re-render
- The update doesn't need to happen synchronously from the user's perspective
- You want to keep the UI responsive during the expensive update

Don't use it for:
- Urgent user input updates (never wrap the input value itself in a transition)
- Network requests (transitions are about rendering cost, not async data)
- Any update that must commit before the user takes the next action

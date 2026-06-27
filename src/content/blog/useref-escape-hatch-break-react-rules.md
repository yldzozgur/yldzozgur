---
title: "useRef: the escape hatch that lets you break React's rules safely."
description: "What useRef is for beyond DOM access, when to use it instead of useState, and the situations where mutating a ref is the correct solution."
pubDate: 2024-11-18
tags: ["React"]
draft: false
---

`useRef` is introduced in most React tutorials as "how you access DOM nodes." That use case is real, but it is the less interesting half of what `useRef` does. The more important use case is storing mutable values that persist across renders without triggering re-renders.

## The two problems useRef solves

### 1. Access to DOM nodes

```jsx
function AutoFocusInput() {
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current.focus();
  }, []);

  return <input ref={inputRef} />;
}
```

React attaches the DOM node to `inputRef.current` after the component mounts. This is the straightforward case. The ref gives you a direct reference to the underlying DOM element for cases where you need imperative DOM access: focus management, measuring element dimensions, integrating with third-party libraries that manipulate the DOM directly.

### 2. Mutable values that persist without triggering re-renders

`useRef` returns a plain object `{ current: value }` that React keeps stable across renders. Mutating `ref.current` does not cause a re-render. This is fundamentally different from `useState`.

When would you want a value that persists but doesn't cause a re-render?

**Storing a timer ID:**
```jsx
const timerRef = useRef(null);

function start() {
  timerRef.current = setInterval(() => {
    // do work
  }, 1000);
}

function stop() {
  clearInterval(timerRef.current);
}
```

The timer ID is not part of the UI. Storing it in state would cause a re-render when you start and stop the timer, which is unnecessary.

**Tracking whether the component has mounted:**
```jsx
function Component() {
  const isMounted = useRef(false);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  function handleAsyncAction() {
    fetchData().then(data => {
      if (isMounted.current) {
        setState(data); // Avoid setting state on unmounted component
      }
    });
  }
}
```

**Storing the previous value of a prop or state:**
```jsx
function Component({ value }) {
  const prevValueRef = useRef(value);
  const prevValue = prevValueRef.current;

  useEffect(() => {
    prevValueRef.current = value;
  });

  return (
    <div>
      Current: {value}, Previous: {prevValue}
    </div>
  );
}
```

After each render, the effect updates the ref to the current value. On the next render, `prevValueRef.current` holds the value from the previous render.

## The stale closure escape hatch

One pattern where `useRef` is particularly useful is reading the latest value of something inside a callback that is not re-created on every render.

```jsx
function SearchComponent({ onSearch }) {
  const [query, setQuery] = useState('');
  const queryRef = useRef(query);

  // Keep ref in sync with state
  useEffect(() => {
    queryRef.current = query;
  });

  // This callback is created once, but always reads the latest query
  const handleKeyPress = useCallback((event) => {
    if (event.key === 'Enter') {
      onSearch(queryRef.current); // Always the latest value
    }
  }, [onSearch]); // Doesn't need query in deps

  return <input onChange={e => setQuery(e.target.value)} onKeyPress={handleKeyPress} />;
}
```

Without the ref, `handleKeyPress` would close over a stale `query` value. By storing `query` in a ref and updating the ref synchronously after each render, the callback always reads the current value.

## Forwarding refs to child components

By default, refs can only be attached to DOM elements. To attach a ref to a custom component and access a DOM node inside it, use `forwardRef`:

```jsx
const FancyInput = forwardRef(function FancyInput(props, ref) {
  return (
    <div className="fancy-wrapper">
      <input ref={ref} {...props} />
    </div>
  );
});

// Parent can now do:
const inputRef = useRef(null);
<FancyInput ref={inputRef} />
inputRef.current.focus(); // Accesses the input inside FancyInput
```

## What not to do with refs

**Don't use a ref when state is the right tool.** If a value changing should cause the UI to update, use `useState`. Refs intentionally bypass the render cycle. If you store something in a ref and read it in JSX, the UI won't update when the ref changes.

```jsx
// Bug: updating a ref does not cause the displayed count to update
const count = useRef(0);
return (
  <button onClick={() => { count.current++; }}>
    Clicked {count.current} times {/* Always shows initial value */}
  </button>
);
```

**Don't read or write refs during rendering.** Refs are mutable, and React's render function should be pure. Reading a ref during render is fine if it's genuinely needed, but writing to a ref during render can cause inconsistencies between renders. Writes to refs belong in event handlers and effects.

The rule of thumb: reach for `useRef` when you need to persist a value across renders but the value changing does not need to update the screen. When in doubt, start with `useState`.

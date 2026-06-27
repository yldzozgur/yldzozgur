---
title: "useState anti-patterns that cause re-renders you can't explain."
description: "The most common useState mistakes that create unnecessary re-renders, stale state, and bugs that are hard to trace back to their source."
pubDate: 2024-11-07
tags: ["React"]
draft: false
---

`useState` looks simple. Most problems with it come not from misunderstanding the API but from patterns that seem fine in isolation and create subtle bugs at scale.

## Storing derived state

If a value can be computed from existing state, putting it in state creates a second source of truth that can get out of sync.

```jsx
// Anti-pattern
const [items, setItems] = useState([]);
const [itemCount, setItemCount] = useState(0);

function addItem(item) {
  setItems([...items, item]);
  setItemCount(itemCount + 1); // Easy to forget, easy to get wrong
}
```

Every time you update `items`, you have to remember to update `itemCount`. When you forget, they diverge. The fix is to derive `itemCount` from `items` during render:

```jsx
// Correct
const [items, setItems] = useState([]);
const itemCount = items.length; // Derived, always in sync
```

This is not just cleaner syntax. It is structurally impossible for `itemCount` and `items` to disagree because `itemCount` is recalculated every render from the authoritative source.

## Using state for values that don't affect rendering

State triggers re-renders. If a value changes but should not cause the component to re-render, state is the wrong place to put it.

```jsx
// Anti-pattern: timer ID stored in state
const [timerId, setTimerId] = useState(null);

function start() {
  const id = setInterval(tick, 1000);
  setTimerId(id); // Causes a re-render just to store the ID
}
```

A timer ID is something you need to call `clearInterval` on later. The UI doesn't depend on it. Storing it in state causes an extra re-render every time you save or clear it. Use `useRef` for values you need to persist across renders without triggering re-renders:

```jsx
const timerIdRef = useRef(null);

function start() {
  timerIdRef.current = setInterval(tick, 1000);
  // No re-render
}
```

## Initializing state from props and not updating it

Passing a prop to `useState` as the initial value is valid. The mistake is expecting it to update when the prop changes.

```jsx
// Anti-pattern
function EditableTitle({ title }) {
  const [value, setValue] = useState(title); // Only reads title once
  // If title prop changes later, value does not update
}
```

`useState(title)` uses `title` as the initial value for the first render. Subsequent renders with a different `title` prop do not update `value`. The component is now "stuck" with the original value.

Solutions:

1. If you need a locally editable copy that resets when the prop changes, use a `key` prop at the call site. Changing `key` unmounts and remounts the component, resetting all state:

```jsx
// At the parent
<EditableTitle key={title} title={title} />
```

2. If you need to sync with prop changes, use `useEffect` to detect them and update state explicitly (though this pattern often indicates the state should be lifted up instead).

## Updating state with stale closures

Each render captures the state values from that render. Inside callbacks that are not re-created on every render, you may be reading a stale value.

```jsx
// Anti-pattern
const [count, setCount] = useState(0);

useEffect(() => {
  const interval = setInterval(() => {
    setCount(count + 1); // count is always 0 (from the first render)
  }, 1000);
  return () => clearInterval(interval);
}, []); // Empty dependency array means the closure captures count=0 forever
```

The fix is to use the functional update form, which receives the current state as an argument rather than closing over a captured value:

```jsx
useEffect(() => {
  const interval = setInterval(() => {
    setCount(prev => prev + 1); // Always reads the current value
  }, 1000);
  return () => clearInterval(interval);
}, []);
```

The functional form `setCount(prev => prev + 1)` is always safe when the new state depends on the previous state. Use it by default whenever you're incrementing, toggling, or appending.

## Creating new object references on every render

React uses `Object.is` comparison to decide if state has changed. For primitive values this is straightforward. For objects and arrays, it compares references.

```jsx
// This triggers a re-render every time even if nothing changed
const [config, setConfig] = useState({ theme: 'dark', lang: 'en' });

// Anti-pattern: passing a new object to setConfig even when values are the same
setConfig({ ...config, lang: 'en' }); // Creates a new object, different reference
```

More commonly, this appears with state in parent components that passes objects down as props. If the parent re-renders and creates a new object reference even with the same values, child components that use `React.memo` will still re-render because the reference changed.

Keep state as flat as possible. Update only the fields that actually changed. Consider splitting unrelated state into separate `useState` calls instead of one large state object.

## Batching and the multiple setState calls pattern

React batches state updates that happen in event handlers. Multiple `setState` calls in the same event handler cause only one re-render.

```jsx
function handleReset() {
  setName('');
  setAge(0);
  setEmail('');
  // One re-render, not three
}
```

This works automatically in event handlers. In async code (inside `setTimeout`, `fetch` callbacks), React 18 batches these automatically as well via automatic batching. Before React 18, they were not batched in async contexts.

The anti-pattern here is splitting state updates across multiple places when they should always change together. If `name`, `age`, and `email` always reset together, consider whether they should be a single state object:

```jsx
const [form, setForm] = useState({ name: '', age: 0, email: '' });

function handleReset() {
  setForm({ name: '', age: 0, email: '' }); // One call, clear intent
}
```

The rule of thumb: group state that always changes together. Separate state that changes independently. This minimizes both cognitive overhead and unnecessary re-renders.

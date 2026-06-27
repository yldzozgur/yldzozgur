---
title: "useEffect's dependency array is a contract. Breaking it causes silent bugs."
description: "Why the useEffect dependency array is not a performance optimization but a correctness requirement, and what happens when you leave things out of it."
pubDate: 2024-11-11
tags: ["React"]
draft: false
---

The dependency array in `useEffect` is widely misunderstood. Developers treat it as a way to control how often the effect runs. That framing leads to incorrect code. The dependency array is a declaration of what values the effect reads. React uses that declaration to know when to re-run the effect. If your declaration is wrong, your effect is wrong.

## What the dependency array actually means

An effect reads values from the component's scope: props, state, variables derived from them. The dependency array should list every one of those values.

```jsx
useEffect(() => {
  document.title = `${user.name} - Dashboard`;
}, [user.name]); // Correct: the effect reads user.name, so it's listed
```

When `user.name` changes, React re-runs the effect. When nothing in the dependency array changes, React skips the effect. This is a correctness guarantee, not an optimization. React assumes the effect does not need to re-run if its inputs haven't changed.

## The empty array case

```jsx
useEffect(() => {
  fetchUser(userId);
}, []); // This says: "this effect has no dependencies"
```

An empty array means the effect runs once after the first render and never again. If the effect truly has no dependencies (it doesn't read any reactive values), this is correct. An initialization step that runs once, for example.

The bug happens when an effect does read reactive values but you list `[]` anyway to get the "run once" behavior:

```jsx
// Bug: effect reads userId but doesn't list it
useEffect(() => {
  fetchUser(userId); // userId is a reactive value
}, []); // Pretending it has no dependencies

// If userId changes (e.g., user navigates to a different profile),
// the effect does not re-run. You're showing stale data.
```

This is a stale closure bug. The effect captured `userId` from the first render. When `userId` changes in subsequent renders, the effect still holds the old value. The `[]` array tells React "don't re-run this," so the stale value is never updated.

## The correct fix

```jsx
useEffect(() => {
  fetchUser(userId);
}, [userId]); // The effect re-runs when userId changes
```

Now if the component renders with a new `userId`, the effect re-runs and fetches the correct user. You may need to handle cleanup to cancel the previous request:

```jsx
useEffect(() => {
  let cancelled = false;

  fetchUser(userId).then(data => {
    if (!cancelled) {
      setUser(data);
    }
  });

  return () => {
    cancelled = true;
  };
}, [userId]);
```

## Functions as dependencies

Functions defined inside the component are recreated on every render. Listing a function in the dependency array means the effect re-runs on every render, which is usually not what you want.

```jsx
// This effect re-runs on every render
function Component({ id }) {
  function loadData() {
    fetch(`/api/${id}`);
  }

  useEffect(() => {
    loadData();
  }, [loadData]); // New function reference every render
}
```

The options:

1. Move the function inside the effect:

```jsx
useEffect(() => {
  function loadData() {
    fetch(`/api/${id}`);
  }
  loadData();
}, [id]); // Only depends on id now
```

2. Wrap the function in `useCallback` so it only changes when its own dependencies change:

```jsx
const loadData = useCallback(() => {
  fetch(`/api/${id}`);
}, [id]);

useEffect(() => {
  loadData();
}, [loadData]); // Stable reference, only changes when id changes
```

The first approach (moving the function inside the effect) is usually cleaner when the function is only used by that effect.

## Object and array dependencies

Similar to functions, objects and arrays created during render are new references on every render:

```jsx
// This effect re-runs on every render
useEffect(() => {
  fetchWithOptions(options);
}, [options]); // options is { timeout: 5000 } - new object every render
```

Solutions:

1. Reference only the primitive values you actually need:

```jsx
useEffect(() => {
  fetchWithOptions({ timeout: options.timeout });
}, [options.timeout]); // Primitive value, stable comparison
```

2. Move the object outside the component if it's constant:

```jsx
const DEFAULT_OPTIONS = { timeout: 5000 };

function Component() {
  useEffect(() => {
    fetchWithOptions(DEFAULT_OPTIONS);
  }, []); // Correct: no reactive dependencies
}
```

## The eslint-plugin-react-hooks exhaustive-deps rule

The `exhaustive-deps` rule from `eslint-plugin-react-hooks` statically analyzes your effects and warns when you're missing dependencies. Configure it:

```json
{
  "rules": {
    "react-hooks/exhaustive-deps": "error"
  }
}
```

Treat every warning as a potential bug, not a style issue. The correct response to a dependency warning is not to add the value to the `// eslint-disable` comment. It is to either add the value to the dependency array or restructure the code so the effect doesn't need it.

## When effects don't belong

Sometimes you have an effect with a dependency that causes it to run more than you want. The instinct is to remove the dependency. The better question is: should this be an effect at all?

Event handlers are the alternative. Effects react to renders. Event handlers react to user actions.

```jsx
// Anti-pattern: using an effect to respond to a button click
useEffect(() => {
  if (shouldSave) {
    saveData(data);
    setShouldSave(false);
  }
}, [shouldSave, data]);

// Correct: handle it in the event handler directly
function handleSave() {
  saveData(data);
}
```

The dependency array is an honest specification of what your effect depends on. Keeping it honest is what keeps your components correct.

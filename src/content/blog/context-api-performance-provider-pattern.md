---
title: "Context API performance: the provider pattern that doesn't re-render everything."
description: "Why Context causes unexpected re-renders, and how to structure your providers to limit re-renders to only the components that actually consume the changed value."
pubDate: 2024-11-25
tags: ["React"]
draft: false
---

Context is React's built-in way to share data across a component tree without prop drilling. It works well for data that changes infrequently. For data that changes often, naive Context usage causes every consumer to re-render whenever any part of the context value changes, even if that component only cares about a part that didn't change.

## Why Context re-renders are broad

When a Context value changes, React re-renders every component that calls `useContext` for that context, regardless of which part of the value changed.

```jsx
const AppContext = createContext();

function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState('light');

  return (
    <AppContext.Provider value={{ user, setUser, theme, setTheme }}>
      {children}
    </AppContext.Provider>
  );
}
```

If `theme` changes, every component using `useContext(AppContext)` re-renders, including components that only care about `user`. The context object is a new reference on every render because it's created inline in the Provider's render function. React compares context values by reference, detects a new object, and re-renders all consumers.

## Solution 1: Split contexts by concern

The simplest fix is to not put unrelated data in the same context.

```jsx
const UserContext = createContext();
const ThemeContext = createContext();

function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState('light');

  return (
    <UserContext.Provider value={{ user, setUser }}>
      <ThemeContext.Provider value={{ theme, setTheme }}>
        {children}
      </ThemeContext.Provider>
    </UserContext.Provider>
  );
}
```

Now components that consume `ThemeContext` don't re-render when `user` changes, and vice versa. This is the primary strategy and often the only one you need.

## Solution 2: Split state and dispatch

A common pattern for complex state is to put the state object and the dispatch function in separate contexts. The dispatch function never changes (it's a stable reference from `useReducer`), so components that only dispatch actions won't re-render when state changes.

```jsx
const StateContext = createContext();
const DispatchContext = createContext();

function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>
        {children}
      </DispatchContext.Provider>
    </StateContext.Provider>
  );
}

// A button that only dispatches doesn't re-render on state changes
function AddButton() {
  const dispatch = useContext(DispatchContext); // Stable reference
  return <button onClick={() => dispatch({ type: 'ADD_ITEM' })}>Add</button>;
}
```

## Solution 3: Memoize the context value

If you need a single context but want to prevent re-renders when the value hasn't meaningfully changed, memoize the value object:

```jsx
function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState('light');

  const value = useMemo(
    () => ({ user, setUser, theme, setTheme }),
    [user, theme] // setUser and setTheme are stable references from useState
  );

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}
```

The `useMemo` ensures the value object has the same reference between renders unless `user` or `theme` actually changed. This prevents re-renders in consumers when an unrelated ancestor re-renders.

Note: `setUser` and `setTheme` are stable references from `useState` and don't need to be in the `useMemo` dependencies.

## Solution 4: Context selector pattern

For fine-grained subscriptions to context slices, you need a library. React doesn't have built-in context selectors. The `use-context-selector` library provides this:

```jsx
import { createContext, useContextSelector } from 'use-context-selector';

const AppContext = createContext();

// Only re-renders when user.name changes, even if other parts of context change
function UserName() {
  const name = useContextSelector(AppContext, ctx => ctx.user?.name);
  return <span>{name}</span>;
}
```

For most applications, splitting contexts is sufficient and requires no additional dependencies.

## The provider composition pattern

When you have many providers, nesting them creates deep indentation. A common pattern is to compose them:

```jsx
function AppProviders({ children }) {
  return (
    <AuthProvider>
      <ThemeProvider>
        <CartProvider>
          {children}
        </CartProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

// Or with a reduce pattern for dynamic composition
function combineProviders(providers) {
  return providers.reduce(
    (AccumulatedProviders, [Provider, props = {}]) =>
      ({ children }) => (
        <AccumulatedProviders>
          <Provider {...props}>{children}</Provider>
        </AccumulatedProviders>
      ),
    ({ children }) => children
  );
}

const AppProviders = combineProviders([
  [AuthProvider],
  [ThemeProvider, { defaultTheme: 'light' }],
  [CartProvider],
]);
```

## When to use Context vs external state

Context is well-suited for:
- Authentication state (user object, login/logout functions)
- Theme and locale (changes infrequently)
- Feature flags
- Modal or toast management

Context struggles with:
- State that changes frequently (form values, search queries, counters)
- State that needs to be updated from many components simultaneously
- State that requires time-travel debugging or middleware

For frequent updates or complex state needs, a dedicated state manager like Zustand or Redux Toolkit performs better because they use subscription-based updates rather than React's context diffing.

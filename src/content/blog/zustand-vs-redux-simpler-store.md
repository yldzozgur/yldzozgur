---
title: "Zustand vs Redux: when the simpler store is the right choice."
description: "What Zustand does differently from Redux, the concrete cases where each is the better fit, and what you actually give up going simpler."
pubDate: 2026-04-06
tags: ["Architecture"]
draft: false
---

Redux has been the default state management library for React for a decade. Zustand has grown to be a genuine alternative. The question isn't which is better -- it's which fits your situation.

## What Redux gives you

Redux is an architecture as much as a library. State lives in a single store, changes go through dispatched actions, and reducers are pure functions that produce new state. Redux Toolkit (RTK) makes this practical:

```typescript
import { createSlice, configureStore } from '@reduxjs/toolkit';

const cartSlice = createSlice({
  name: 'cart',
  initialState: { items: [], total: 0 },
  reducers: {
    addItem: (state, action) => {
      state.items.push(action.payload);
      state.total += action.payload.price;
    },
    removeItem: (state, action) => {
      state.items = state.items.filter(i => i.id !== action.payload);
      state.total = state.items.reduce((sum, i) => sum + i.price, 0);
    },
  },
});

const store = configureStore({ reducer: { cart: cartSlice.reducer } });
```

The benefits:
- **Predictability:** every state change is an explicit action, traceable through the action log
- **DevTools:** time-travel debugging, action replay, state inspection
- **Middleware:** easy to add logging, analytics, or saga-based side effects
- **Team patterns:** a large team has a consistent structure for state changes

## What Zustand gives you

Zustand is a smaller, simpler API. A store is just a function that returns state and actions:

```typescript
import { create } from 'zustand';

interface CartStore {
  items: Item[];
  total: number;
  addItem: (item: Item) => void;
  removeItem: (id: string) => void;
}

const useCart = create<CartStore>(set => ({
  items: [],
  total: 0,

  addItem: (item) => set(state => ({
    items: [...state.items, item],
    total: state.total + item.price,
  })),

  removeItem: (id) => set(state => {
    const items = state.items.filter(i => i.id !== id);
    return { items, total: items.reduce((sum, i) => sum + i.price, 0) };
  }),
}));

// Use it
function CartSummary() {
  const { items, total } = useCart();
  return <div>{items.length} items, ${total}</div>;
}
```

No Provider, no selectors, no dispatch. The store is used directly as a hook. Components subscribe to slices of state and only re-render when their slice changes.

## What you give up with Zustand

**DevTools are less powerful.** Zustand has a DevTools middleware, but Redux DevTools' time-travel debugging (jump to any previous state) and action log are more capable. When debugging complex state bugs, Redux's action history is valuable.

**No enforced structure.** Redux's reducer pattern enforces that state changes happen through named actions. Zustand lets you call `set` directly from anywhere. On a large team, this flexibility can lead to state updates scattered throughout the codebase in ways that are hard to follow.

**Less ecosystem.** Redux has years of middleware, patterns, and documentation. RTK Query is the best data-fetching story in the Redux ecosystem. Zustand is simpler but you're making more decisions yourself.

## What you give up with Redux

**Boilerplate at small scale.** RTK has reduced this significantly, but it's still more setup than Zustand for simple state.

**Bundle size.** Redux + RTK is larger than Zustand (though for most apps this isn't meaningful).

**Learning curve.** The Redux mental model (actions, reducers, selectors, dispatch) is a real concept to internalize.

## The practical heuristic

Use Zustand when:
- The app is small to medium, with a single team
- You want minimal boilerplate
- Global state is relatively simple (UI state, user preferences, non-async data)

Use Redux when:
- The team is large and benefits from enforced patterns
- You need RTK Query for server state management
- You need robust DevTools for complex debugging
- You're already in a Redux codebase

Many applications don't need either. React context + `useReducer` is sufficient for simple global state. RTK Query handles server state. Add a global state store only when you have state that genuinely needs to be shared across many unrelated components and updated from many places.

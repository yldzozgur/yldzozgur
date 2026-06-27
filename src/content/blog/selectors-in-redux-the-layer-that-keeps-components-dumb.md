---
title: "Selectors in Redux: the layer that keeps components dumb about state shape."
description: "How selector functions decouple your components from your Redux state structure, and why memoized selectors with Reselect belong in every Redux codebase."
pubDate: 2025-01-02
tags: ["Redux", "React"]
draft: false
---

## The problem with reading state directly in components

When a component reaches into Redux state directly, it takes on knowledge of how the state is shaped. That coupling is subtle but expensive over time.

```javascript
// Component that knows too much
function CartSummary() {
  const items = useSelector(state => state.cart.items);
  const discount = useSelector(state => state.user.profile.memberDiscount);
  const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const discounted = total * (1 - discount);
  return <div>Total: ${discounted.toFixed(2)}</div>;
}
```

Now imagine renaming `memberDiscount` to `discountRate`, or moving items to a normalized structure. Every component that contains this logic needs updating. The derivation logic (the multiplication, the reduce) also lives in the component where it cannot be tested without rendering.

## Selectors as the solution

A selector is just a function that takes state and returns a derived value.

```javascript
// selectors/cart.js
export const selectCartItems = state => state.cart.items;
export const selectMemberDiscount = state => state.user.profile.memberDiscount;

export const selectCartTotal = state => {
  const items = selectCartItems(state);
  return items.reduce((sum, item) => sum + item.price * item.qty, 0);
};

export const selectDiscountedTotal = state => {
  const total = selectCartTotal(state);
  const discount = selectMemberDiscount(state);
  return total * (1 - discount);
};
```

The component becomes:

```javascript
function CartSummary() {
  const total = useSelector(selectDiscountedTotal);
  return <div>Total: ${total.toFixed(2)}</div>;
}
```

Now the component knows nothing about state shape. If the state structure changes, you update one selector file. The derivation logic is testable in isolation, without React, without Redux, just pure functions.

## Memoization with Reselect

Simple selectors recompute on every render. If `selectCartTotal` runs on every state change regardless of whether the cart changed, that is wasted work. For derived values built from multiple inputs, `createSelector` from Reselect memoizes the result.

```javascript
import { createSelector } from '@reduxjs/toolkit'; // re-exported from RTK

export const selectCartItems = state => state.cart.items;
export const selectMemberDiscount = state => state.user.profile.memberDiscount;

export const selectDiscountedTotal = createSelector(
  [selectCartItems, selectMemberDiscount],
  (items, discount) => {
    const total = items.reduce((sum, item) => sum + item.price * item.qty, 0);
    return total * (1 - discount);
  }
);
```

`createSelector` takes an array of input selectors and a result function. It only calls the result function when one of the inputs has changed by reference. If neither `cart.items` nor `user.profile.memberDiscount` changed, the selector returns the cached value immediately.

This matters when the selector feeds a component: if `useSelector` returns the same reference as last render, React skips the re-render entirely.

## Parameterized selectors with factory functions

Sometimes you need a selector that takes an argument, like fetching a single item by ID. The pattern is a selector factory: a function that returns a selector.

```javascript
export const makeSelectItemById = id =>
  createSelector(
    [selectCartItems],
    items => items.find(item => item.id === id)
  );
```

In the component:

```javascript
function CartItem({ id }) {
  const selectItem = useMemo(() => makeSelectItemById(id), [id]);
  const item = useSelector(selectItem);
  return <div>{item.name}</div>;
}
```

The `useMemo` ensures each component instance gets its own memoized selector instance, so the cache is per-component rather than shared (which would break if multiple instances needed different IDs).

## Testing selectors

Because selectors are plain functions, testing them is straightforward:

```javascript
import { selectDiscountedTotal } from './selectors/cart';

test('applies discount to cart total', () => {
  const state = {
    cart: { items: [{ price: 100, qty: 2 }] },
    user: { profile: { memberDiscount: 0.1 } },
  };
  expect(selectDiscountedTotal(state)).toBe(180);
});
```

No rendering, no mocking, no setup. The selector is just a function.

## Where to put selectors

A common convention is to co-locate selectors with the slice file they read from, exporting them alongside the slice actions. RTK encourages this pattern: the slice owns its piece of state and the functions that read from it.

When selectors combine data from multiple slices, a dedicated `selectors/` directory keeps them organized without forcing circular imports.

The key rule: if a component is computing something from state, that computation belongs in a selector, not in the component.

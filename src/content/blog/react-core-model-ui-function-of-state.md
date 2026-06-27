---
title: "React's core model: UI as a function of state. Everything follows from this."
description: "The single idea behind React's design: UI = f(state). Once you internalize this, useState, re-renders, and component composition all make sense as consequences of one principle."
pubDate: 2024-11-04
tags: ["React"]
draft: false
---

React's documentation has grown large, but the entire framework is built on one idea: **UI is a function of state**. Write it as `UI = f(state)`. If you understand this fully, the rest of React's behavior becomes predictable instead of surprising.

## What the formula means

A function takes inputs and produces an output. Given the same inputs, it always produces the same output. No side effects, no hidden dependencies.

React components work the same way. A component takes props and state as inputs and returns JSX as output. Given the same props and state, it always renders the same UI.

```jsx
function Greeting({ name }) {
  return <h1>Hello, {name}</h1>;
}
```

This component is a pure function. Pass `name="Alice"`, you get `<h1>Hello, Alice</h1>`. Every time. The output is determined entirely by the input.

## State is the input React controls

Props come from outside the component. State is internal. When either changes, React calls the function again and computes a new output.

```jsx
function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}
```

The UI at any moment is a direct function of `count`. When `count` is 0, the paragraph says "Count: 0". When `count` is 3, it says "Count: 3". You do not write code to update the DOM. You describe what the UI looks like for each possible state value, and React handles the translation.

## Why this matters: you describe, React decides

The pre-React way to build UIs is imperative: find the element, update its text, toggle this class, hide that div. You write instructions for how to change the DOM step by step.

React's model is declarative: describe what the UI should look like right now, given the current state. React figures out the minimal DOM changes needed to get there. This is what the virtual DOM reconciliation process does: compare the previous output of `f(state)` with the new output of `f(state)` and patch only the differences.

```jsx
// Imperative (not React)
document.getElementById('status').textContent = isOnline ? 'Online' : 'Offline';
document.getElementById('status').className = isOnline ? 'green' : 'red';

// Declarative (React)
function Status({ isOnline }) {
  return (
    <span className={isOnline ? 'green' : 'red'}>
      {isOnline ? 'Online' : 'Offline'}
    </span>
  );
}
```

The declarative version describes the relationship between `isOnline` and the UI. The imperative version describes the procedure for updating the UI. The declarative version is easier to reason about because there is no sequence, no timing, no "what if this runs before that."

## Re-renders are recalculations

When state changes, React calls the component function again. This is a re-render. It is not expensive in the way DOM manipulation is expensive because React's function produces a lightweight JavaScript object tree (the virtual DOM), not actual DOM nodes. The comparison and patch step is fast.

Understanding re-renders as recalculations rather than redraws clarifies why certain patterns exist. You should not put things in state that can be derived from other state, because derived values are just `f(state)` computed inline:

```jsx
// Redundant - total is derived from items
const [items, setItems] = useState([]);
const [total, setTotal] = useState(0); // Don't do this

// Correct - compute total during render
const [items, setItems] = useState([]);
const total = items.reduce((sum, item) => sum + item.price, 0);
```

`total` does not need to be state. It is a function of `items`. Every time `items` changes, the component re-renders, and `total` is recomputed automatically. If you put it in state, you have to remember to update both, and they can drift out of sync.

## Components compose because functions compose

Because components are functions, you can compose them the same way you compose functions. The output of one component can be the input (children) of another. This scales from a single button to an entire application.

```jsx
function App() {
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState([]);

  return (
    <Layout>
      <Header user={user} />
      <ProductList onAddToCart={(item) => setCart([...cart, item])} />
      <CartSidebar items={cart} />
    </Layout>
  );
}
```

The entire tree is a function of `user` and `cart`. Change either, React re-runs the relevant parts of the tree and updates the DOM.

## The practical consequences

Once you have this model, several React patterns stop being arbitrary rules and become logical necessities:

- **Don't mutate state directly.** You call `setCount(newValue)` instead of `count = count + 1` because React needs to know state changed in order to schedule a re-render. Mutating in place does not trigger the function to be called again.
- **Keep components pure.** Side effects (API calls, timers, DOM manipulation) don't belong in the render path because render should be a predictable function call. Side effects go in `useEffect`.
- **Lift state up.** When two components need the same state, move it to their common ancestor so both can receive it as props. Both are then functions of the same source of truth.

The formula `UI = f(state)` is not marketing. It is the actual design principle that React's authors encoded into the framework. Everything else is a consequence of taking that principle seriously.

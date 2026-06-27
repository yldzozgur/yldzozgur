---
title: "Closures are not magic. One example that makes them click forever."
description: "Closures are the mechanism behind half of JavaScript's patterns. One concrete example explains them permanently."
pubDate: 2024-01-15
tags: ["JavaScript"]
draft: false
---

Every JavaScript developer has read a definition of closures. Something like: "a closure is a function that has access to its outer function's scope even after the outer function has returned." That definition is accurate and completely useless for building intuition.

Here is the one example that makes closures click.

## The example

```js
function makeCounter() {
  let count = 0;

  return function increment() {
    count++;
    return count;
  };
}

const counter = makeCounter();
counter(); // 1
counter(); // 2
counter(); // 3
```

`makeCounter` runs and finishes. After it returns, `count` still exists, and `increment` can still read and write it. That is a closure.

## Why this should not work (but does)

Normal mental model of function execution: when a function returns, its local variables are destroyed. That is how the call stack works. `makeCounter` runs, creates `count = 0`, returns `increment`, and exits. By that model, `count` should be gone.

But JavaScript's memory model is different. Variables are not stored solely on the call stack. When a function creates another function that references the outer function's variables, those variables are kept alive in a structure called the closure environment. The inner function holds a reference to that environment.

So `count` is not on the stack. It is in a heap-allocated environment object. The `increment` function holds a reference to that object. As long as `increment` is reachable, `count` is reachable.

## Two counters do not share state

```js
const counterA = makeCounter();
const counterB = makeCounter();

counterA(); // 1
counterA(); // 2
counterB(); // 1 — completely separate count
counterA(); // 3
```

Each call to `makeCounter` creates a new environment with its own `count`. `counterA` and `counterB` each close over their own environment. They are independent.

This is one of the most useful properties of closures: you can create multiple instances of the same behavior, each with private state.

## Closures in the wild

Once you understand the mechanic, you see closures everywhere.

**Partial application:**

```js
function multiply(a) {
  return function(b) {
    return a * b;
  };
}

const double = multiply(2);
const triple = multiply(3);

double(5); // 10
triple(5); // 15
```

`double` closes over `a = 2`. `triple` closes over `a = 3`. The outer parameter is captured.

**Event handlers with state:**

```js
function attachClickCounter(element) {
  let clicks = 0;

  element.addEventListener("click", function() {
    clicks++;
    console.log(`Clicked ${clicks} times`);
  });
}
```

The click handler closes over `clicks`. Each click can read and update it without exposing it globally.

**Module pattern:**

```js
const bank = (function() {
  let balance = 0;

  return {
    deposit(amount) { balance += amount; },
    withdraw(amount) { balance -= amount; },
    getBalance() { return balance; },
  };
})();

bank.deposit(100);
bank.withdraw(30);
bank.getBalance(); // 70
// balance is not accessible from outside
```

`balance` is private. It only exists in the closure environment of the IIFE. The returned object's methods close over it. This is the module pattern before ES modules existed, and it still works well for standalone utilities.

## The classic loop trap

Before `let` existed, closures caused a famous bug:

```js
// ES5 with var
for (var i = 0; i < 3; i++) {
  setTimeout(function() {
    console.log(i);
  }, 0);
}
// Prints: 3, 3, 3
```

All three functions close over the same `i`. By the time they run, the loop has finished and `i` is 3. All three log 3.

The fix with `let`:

```js
for (let i = 0; i < 3; i++) {
  setTimeout(function() {
    console.log(i);
  }, 0);
}
// Prints: 0, 1, 2
```

`let` creates a new binding per iteration. Each closure captures a different `i`. Understanding this bug requires understanding closures, and understanding closures resolves the bug permanently.

## The actual mental model

Stop thinking about closures as a feature. They are a consequence of how scope works in JavaScript.

A function can reference any variable in any enclosing scope at the time it was defined. If that function outlives its enclosing scope (which happens when you return it, store it, or pass it as a callback), the referenced variables are kept alive.

That is it. No magic. Closures are just functions that remember the variables around them when they were created. The counter example makes this concrete because you can see the state persisting across calls in a way that would be impossible if the variables were destroyed.

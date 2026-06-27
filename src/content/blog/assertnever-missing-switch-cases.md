---
title: "The assertNever trick: catching missing switch cases at compile time."
description: "assertNever is a one-function pattern that turns incomplete switch statements from runtime bugs into compile errors."
pubDate: 2024-03-11
tags: ["TypeScript"]
draft: false
---

When you switch over a union type, TypeScript does not automatically warn you if you miss a case. You can have a union with five variants and a switch with four cases, and TypeScript will not complain. The `assertNever` pattern fixes this.

## The problem

```ts
type Shape = "circle" | "rectangle" | "triangle";

function describe(shape: Shape): string {
  switch (shape) {
    case "circle":
      return "A round shape";
    case "rectangle":
      return "A four-sided shape";
    // Missing: "triangle"
    // TypeScript: no error
  }
  // Returns undefined implicitly — but TypeScript thinks the return type is string
}
```

Later, someone adds `"pentagon"` to `Shape`. The switch still has no default. `describe("pentagon")` returns `undefined` at runtime. The compiler never told you.

## The assertNever function

```ts
function assertNever(x: never): never {
  throw new Error("Unexpected value: " + JSON.stringify(x));
}
```

The `never` type is the bottom type in TypeScript — the type that has no values. A variable of type `never` can never have a value. If TypeScript infers that something is `never`, it means that code is unreachable.

Use it in the default case of a switch:

```ts
function describe(shape: Shape): string {
  switch (shape) {
    case "circle":
      return "A round shape";
    case "rectangle":
      return "A four-sided shape";
    case "triangle":
      return "A three-sided shape";
    default:
      return assertNever(shape); // shape is 'never' here if all cases are handled
  }
}
```

If all cases are handled, `shape` in the default case has type `never` because there are no remaining values it could be. Passing `never` to `assertNever(x: never)` compiles fine.

Now add a new variant:

```ts
type Shape = "circle" | "rectangle" | "triangle" | "pentagon";
```

The `describe` function now has an unhandled case. In the default branch, `shape` is `"pentagon"` — not `never`. Passing `"pentagon"` to `assertNever(x: never)` is a compile error:

```
Argument of type '"pentagon"' is not assignable to parameter of type 'never'.
```

The compiler tells you exactly which function needs updating.

## With discriminated unions

The pattern is most valuable with discriminated unions:

```ts
type Action =
  | { type: "INCREMENT" }
  | { type: "DECREMENT" }
  | { type: "RESET"; value: number };

function reducer(state: number, action: Action): number {
  switch (action.type) {
    case "INCREMENT":
      return state + 1;
    case "DECREMENT":
      return state - 1;
    case "RESET":
      return action.value;
    default:
      return assertNever(action);
  }
}
```

When a new action type is added to the union, every reducer that does not handle it gets a compile error. No more runtime bugs from unhandled actions.

## Exhaustive if-else chains

`assertNever` also works with if-else chains, though switch is more common for this pattern:

```ts
function processStatus(status: "pending" | "active" | "cancelled") {
  if (status === "pending") {
    return "waiting";
  } else if (status === "active") {
    return "running";
  } else if (status === "cancelled") {
    return "done";
  } else {
    return assertNever(status); // compile error if a case is missing
  }
}
```

## Exhaustive checks in object maps

An alternative to switch statements is an object map:

```ts
const labels: Record<Shape, string> = {
  circle: "A round shape",
  rectangle: "A four-sided shape",
  triangle: "A three-sided shape",
  // pentagon: ... // TypeScript error if missing and pentagon is in Shape
};

function describe(shape: Shape): string {
  return labels[shape];
}
```

`Record<Shape, string>` requires a key for every member of `Shape`. This is exhaustive by definition. When you add `"pentagon"` to `Shape`, the `Record` type immediately requires a `pentagon` entry.

This approach works when the values are data. Use `assertNever` in functions where the logic per case is more complex.

## The runtime safety

`assertNever` also provides runtime safety. If somehow a value outside the union reaches the switch (from `any` cast, JSON parse, etc.), the function throws with a descriptive error instead of silently returning `undefined`.

```ts
function assertNever(x: never): never {
  throw new Error("Unexpected value: " + JSON.stringify(x));
}
```

The throw is the runtime guarantee. The compile error is the development-time guarantee. Together they cover both the expected case (wrong type at compile time) and the unexpected case (invalid value at runtime).

One function, four lines, eliminates an entire category of missing-case bugs.

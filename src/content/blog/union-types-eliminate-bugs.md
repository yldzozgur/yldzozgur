---
title: "Union types sound simple. They eliminate entire bug categories."
description: "Union types in TypeScript are more than a list of allowed values. They enforce handling every case at compile time."
pubDate: 2024-02-05
tags: ["TypeScript"]
draft: false
---

A union type says "this value can be one of these types." That sounds like a minor convenience, but the real power is what the compiler can do with that information: force you to handle every case.

## Basic union types

```ts
type Status = "pending" | "active" | "inactive";

function setUserStatus(status: Status) {
  // TypeScript only accepts the three literal values
}

setUserStatus("active"); // OK
setUserStatus("deleted"); // Error: Argument of type '"deleted"' is not assignable to parameter of type 'Status'
```

This already eliminates a class of typo bugs. But the more important use is in control flow.

## Exhaustive checking in switch statements

```ts
type Status = "pending" | "active" | "inactive";

function getStatusLabel(status: Status): string {
  switch (status) {
    case "pending":
      return "Waiting for approval";
    case "active":
      return "Currently active";
    case "inactive":
      return "Deactivated";
  }
}
```

If you add a new status to the union:

```ts
type Status = "pending" | "active" | "inactive" | "suspended";
```

TypeScript will report an error on `getStatusLabel` because the function might not return a string when `status` is `"suspended"`. The compiler tells you exactly where you need to handle the new case. You cannot forget.

## Union types with objects

Unions work with full object types, not just string literals:

```ts
type Circle = { kind: "circle"; radius: number };
type Rectangle = { kind: "rectangle"; width: number; height: number };
type Triangle = { kind: "triangle"; base: number; height: number };

type Shape = Circle | Rectangle | Triangle;
```

Each variant has a `kind` discriminant that makes it uniquely identifiable. This is a discriminated union, which has special power in TypeScript's narrowing.

```ts
function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2; // TypeScript knows shape is Circle here
    case "rectangle":
      return shape.width * shape.height;  // TypeScript knows shape is Rectangle here
    case "triangle":
      return 0.5 * shape.base * shape.height;
  }
}
```

Inside each case, TypeScript has narrowed the type. You cannot access `shape.radius` in the rectangle case because TypeScript knows it does not exist there.

## The eliminated bug category

Without union types, the status-handling bug looks like this:

```js
// JavaScript — no enforcement
function getStatusLabel(status) {
  if (status === "pending") return "Waiting";
  if (status === "active") return "Active";
  // Forgot "inactive" — returns undefined
  // No error until runtime
}
```

You add a new status, update the `Status` constant somewhere, but forget this function. The bug ships. With a union type, the compiler catches the omission before the code runs.

## Nullable values as union types

TypeScript's strict null checks use union types. `string | null` is a union of `string` and `null`:

```ts
function getUser(id: number): User | null {
  return db.find(id) ?? null;
}

const user = getUser(1);
user.name; // Error: Object is possibly 'null'

if (user) {
  user.name; // OK — TypeScript narrowed to User
}
```

This forces you to handle the null case. Without strict null checks, `null` values silently pass through type checking and cause runtime errors.

## Union types for function return values

A common pattern is returning either a result or an error:

```ts
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string };

function parseJSON(input: string): Result<unknown> {
  try {
    return { success: true, data: JSON.parse(input) };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

const result = parseJSON('{"name": "Alice"}');

if (result.success) {
  console.log(result.data); // TypeScript knows this is the success branch
} else {
  console.error(result.error); // TypeScript knows this is the error branch
}
```

You cannot access `result.data` without checking `result.success` first. The compiler makes the error case impossible to ignore.

## Combining with type narrowing

TypeScript narrows union types in if statements, switch statements, and type guards:

```ts
type Input = string | number | string[];

function process(input: Input) {
  if (typeof input === "string") {
    return input.toUpperCase(); // TypeScript: string
  }
  if (Array.isArray(input)) {
    return input.join(", "); // TypeScript: string[]
  }
  return input.toFixed(2); // TypeScript: number
}
```

Each branch handles one variant of the union. TypeScript tracks which variants remain possible as it narrows.

Union types are not just about documenting allowed values. They turn "did you handle all the cases?" from a code review question into a compiler check.

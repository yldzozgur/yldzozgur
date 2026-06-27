---
title: "TypeScript's discriminated union is the closest thing it has to a superpower."
description: "Discriminated unions model state that cannot be invalid. They eliminate impossible states by making them unrepresentable."
pubDate: 2024-02-12
tags: ["TypeScript"]
draft: false
---

The phrase "make illegal states unrepresentable" comes from functional programming. It means designing types so that invalid states cannot be constructed in the first place. TypeScript's discriminated unions are the primary way to do this.

## The problem with flags and nullable fields

Imagine a component that loads user data:

```ts
// Common but problematic pattern
interface UserState {
  loading: boolean;
  error: string | null;
  data: User | null;
}
```

This type allows states that should be impossible:
- `loading: true, data: { ... }` — loading and already done?
- `loading: false, error: null, data: null` — not loading, no error, no data?
- `loading: true, error: "timeout"` — loading but also errored?

You end up writing defensive checks everywhere because TypeScript cannot tell you which combinations are valid.

## Discriminated union version

```ts
type UserState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: User };
```

Now each valid state is a separate type. Impossible combinations cannot be constructed. The `status` field is the discriminant — TypeScript uses it to narrow the type.

```ts
function render(state: UserState) {
  switch (state.status) {
    case "idle":
      return <div>Click to load</div>;
    case "loading":
      return <Spinner />;
    case "error":
      return <ErrorMessage message={state.message} />;
      // TypeScript knows message exists here
    case "success":
      return <UserProfile user={state.data} />;
      // TypeScript knows data exists here
  }
}
```

In the `"error"` case, `state.message` is available — TypeScript narrowed the type to the error variant. In the `"success"` case, `state.data` is available. In any other case, those properties do not exist.

## How narrowing works

The discriminant must be a literal type on a common property. TypeScript uses structural narrowing: once it sees `state.status === "error"`, it knows `state` must be the `{ status: "error"; message: string }` variant, because that is the only member of the union with `status === "error"`.

```ts
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rectangle"; width: number; height: number };

function describe(shape: Shape) {
  if (shape.kind === "circle") {
    // shape is narrowed to { kind: "circle"; radius: number }
    return `Circle with radius ${shape.radius}`;
  }
  // shape is narrowed to { kind: "rectangle"; width: number; height: number }
  return `Rectangle ${shape.width}x${shape.height}`;
}
```

## Network request states

A discriminated union for async operations:

```ts
type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };
```

This generic type works for any async operation. Use it for any piece of data that needs to track its loading lifecycle.

```ts
function useUser(id: number): AsyncState<User> {
  // implementation
}

const state = useUser(1);

// Without narrowing, you can't access data or error:
state.data; // Error: Property 'data' does not exist on type 'AsyncState<User>'

// After narrowing:
if (state.status === "success") {
  state.data; // User — TypeScript knows
}
```

## Exhaustive checking with assertNever

Adding a new variant to a discriminated union should force you to handle it everywhere. You can enforce this with an exhaustive check:

```ts
function assertNever(x: never): never {
  throw new Error("Unexpected value: " + JSON.stringify(x));
}

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    case "rectangle":
      return shape.width * shape.height;
    default:
      return assertNever(shape); // compile error if a case is missing
  }
}
```

When you add `{ kind: "triangle"; base: number; height: number }` to the `Shape` union, `assertNever(shape)` will fail to compile because `shape` is no longer of type `never` in the default case — it is the unhandled triangle variant. The compiler tells you exactly where to add the missing case.

## Modeling command/event types

Discriminated unions are ideal for command objects and event systems:

```ts
type UserAction =
  | { type: "CREATE_USER"; payload: { name: string; email: string } }
  | { type: "DELETE_USER"; payload: { id: number } }
  | { type: "UPDATE_EMAIL"; payload: { id: number; email: string } };

function handleAction(action: UserAction) {
  switch (action.type) {
    case "CREATE_USER":
      return createUser(action.payload.name, action.payload.email);
    case "DELETE_USER":
      return deleteUser(action.payload.id);
    case "UPDATE_EMAIL":
      return updateEmail(action.payload.id, action.payload.email);
  }
}
```

This is essentially how Redux reducers work. The discriminant is `type`, and each case has its own payload shape.

The key insight: discriminated unions do not just improve readability. They change what is possible to represent. Invalid states cannot be constructed, which means you cannot write code that handles them — they never occur.

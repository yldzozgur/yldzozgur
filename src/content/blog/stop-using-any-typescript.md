---
title: "The TypeScript pattern that made me stop using any everywhere."
description: "unknown is the type-safe alternative to any. Combined with type guards, it handles dynamic data without sacrificing type safety."
pubDate: 2024-03-21
tags: ["TypeScript"]
draft: false
---

`any` is the escape hatch in TypeScript. It disables type checking for a value and everything that flows from it. It spreads: once something is `any`, accessing its properties gives you more `any`. It is infectious, and once it gets into your codebase it is hard to contain.

The better alternative is `unknown`.

## What any does

```ts
const x: any = fetchSomething();
x.foo.bar.baz(); // TypeScript: fine
x.someMethod(x.notANumber * 2); // TypeScript: fine
// All of these compile, all of these could throw at runtime
```

With `any`, TypeScript stops checking. You get no autocomplete, no error detection, no type inference. You lose the benefits of TypeScript on that value and everything derived from it.

## What unknown does

```ts
const x: unknown = fetchSomething();
x.foo; // Error: Object is of type 'unknown'
x(); // Error: Object is of type 'unknown'
```

`unknown` says "I don't know what this is." Unlike `any`, TypeScript refuses to let you use an `unknown` value without first narrowing it to a known type. This forces you to handle the unknown-ness explicitly.

## Narrowing unknown

```ts
function process(value: unknown) {
  if (typeof value === "string") {
    // value is string here
    return value.toUpperCase();
  }
  if (typeof value === "number") {
    // value is number here
    return value.toFixed(2);
  }
  if (Array.isArray(value)) {
    // value is any[] here
    return value.length;
  }
  return null;
}
```

You can use any narrowing technique: `typeof`, `instanceof`, `in`, custom type guards.

## Parsing external data

The most common legitimate use of `unknown` is when handling data from outside the TypeScript type system — JSON responses, environment variables, event payloads:

```ts
async function fetchUser(id: number): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  const data: unknown = await res.json(); // res.json() returns any — annotate as unknown

  if (!isUser(data)) {
    throw new Error("Invalid user response from API");
  }

  return data; // TypeScript knows data is User
}

function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof (value as { id: unknown }).id === "number" &&
    "name" in value &&
    typeof (value as { name: unknown }).name === "string"
  );
}
```

The type guard validates the shape at runtime and communicates it to TypeScript. Once you've narrowed `unknown` to `User`, everything downstream gets full type safety.

## Zod for runtime validation

Writing type guards manually is tedious for complex types. Zod makes it concise:

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.number(),
  name: z.string(),
  email: z.string().email(),
});

type User = z.infer<typeof UserSchema>; // derives the TypeScript type from the schema

async function fetchUser(id: number): Promise<User> {
  const res = await fetch(`/api/users/${id}`);
  const raw: unknown = await res.json();
  return UserSchema.parse(raw); // throws if invalid, returns User if valid
}
```

The schema is the single source of truth for both runtime validation and the TypeScript type.

## Error handling with unknown

TypeScript 4.0+ types catch variables as `unknown` when `useUnknownInCatchVariables` is enabled (which strict mode turns on):

```ts
try {
  doSomething();
} catch (err: unknown) {
  // err is unknown — must narrow before use
  if (err instanceof Error) {
    console.error(err.message);
  } else if (typeof err === "string") {
    console.error(err);
  } else {
    console.error("Unknown error:", JSON.stringify(err));
  }
}
```

This is correct behavior. JavaScript allows throwing any value, not just `Error` instances. Typing catch variables as `unknown` forces you to handle all possibilities.

## When to use any

`any` still has legitimate uses:
- Migration: when converting JavaScript to TypeScript incrementally, `any` is a stepping stone
- Escape hatches: when TypeScript's type system cannot express something correctly and the cast would be more confusing than `any`
- Third-party code without type definitions (though `@types` packages usually exist)

Use `// @ts-ignore` or `// @ts-expect-error` for per-line suppressions rather than sprinkling `any` throughout the code.

## The pattern that replaces any

```ts
// Instead of this:
function processApiResponse(data: any) {
  return data.user.name;
}

// Write this:
function processApiResponse(data: unknown): string {
  if (
    typeof data === "object" &&
    data !== null &&
    "user" in data &&
    typeof (data as { user: unknown }).user === "object"
  ) {
    // narrow further...
  }
  throw new Error("Unexpected response shape");
}

// Or even better, use Zod and validate at the boundary:
const schema = z.object({ user: z.object({ name: z.string() }) });
function processApiResponse(data: unknown): string {
  return schema.parse(data).user.name;
}
```

`unknown` forces you to be explicit about what you expect. `any` lets you ignore the uncertainty. The code is more work to write, but the bugs it prevents are worth it.

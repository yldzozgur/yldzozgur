---
title: "interface vs type alias: the actual differences after years of use either."
description: "interface and type alias overlap almost completely. The real differences are declaration merging and expressiveness for complex types."
pubDate: 2024-02-26
tags: ["TypeScript"]
draft: false
---

One of the most common TypeScript questions is whether to use `interface` or `type`. The answer depends on understanding what they can and cannot do. They overlap significantly, but the differences matter in specific situations.

## Where they behave the same

Both can describe object shapes:

```ts
interface User {
  id: number;
  name: string;
}

type User = {
  id: number;
  name: string;
};
```

Both can extend:

```ts
interface Admin extends User {
  permissions: string[];
}

type Admin = User & { permissions: string[] };
```

Both work in generic types, function parameters, return types, and all the places you use types day-to-day.

## What only `type` can do

**Union and intersection types:**

```ts
type Status = "pending" | "active" | "inactive"; // interface can't do this
type NumberOrString = number | string; // interface can't do this
```

Interfaces describe object shapes. Union types are not object shapes. If you need a union, you must use `type`.

**Mapped types:**

```ts
type Readonly<T> = { readonly [K in keyof T]: T[K] };
type Optional<T> = { [K in keyof T]?: T[K] };
```

These cannot be expressed with interface.

**Conditional types:**

```ts
type IsArray<T> = T extends any[] ? true : false;
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;
```

**Template literal types:**

```ts
type EventName = `on${Capitalize<string>}`;
```

## What only `interface` can do

**Declaration merging:**

```ts
interface User {
  name: string;
}

interface User {
  email: string;
}

// Result: User has both name and email
const user: User = { name: "Alice", email: "alice@example.com" };
```

When you declare an interface with the same name twice, TypeScript merges the declarations. This is how you augment third-party types without modifying the source:

```ts
// Extend Express's Request type in a .d.ts file
declare global {
  namespace Express {
    interface Request {
      user?: AuthenticatedUser;
    }
  }
}
```

Type aliases cannot be merged. Declaring the same `type` twice is an error.

**Implement with classes:**

```ts
interface Serializable {
  serialize(): string;
  deserialize(data: string): this;
}

class Config implements Serializable {
  serialize() { return JSON.stringify(this); }
  deserialize(data: string) { return Object.assign(this, JSON.parse(data)); }
}
```

You can implement a type alias with a class too, but `interface` is the idiomatic choice for this pattern.

## Performance consideration

For large and complex types, interfaces have historically been faster to type-check. The TypeScript team has documented this: interfaces create a named type that can be cached, while type aliases with intersections may be re-evaluated. For most applications this does not matter, but in large monorepos with thousands of types it can.

## The practical choice

Different teams have different conventions. Here is a practical approach:

**Use `interface` for:**
- Object shapes that represent entities (User, Post, Order)
- Public API contracts for libraries (where declaration merging lets consumers extend them)
- Anything a class will implement

**Use `type` for:**
- Unions and intersections
- Mapped and conditional types
- Tuples
- Aliases for primitives or utility type compositions

```ts
// interface — entity/contract
interface UserRepository {
  findById(id: UserId): Promise<User | null>;
  create(data: CreateUserInput): Promise<User>;
  delete(id: UserId): Promise<void>;
}

// type — union
type SortDirection = "asc" | "desc";

// type — composition
type CreateUserInput = Omit<User, "id" | "createdAt" | "updatedAt">;

// type — conditional
type Awaited<T> = T extends Promise<infer U> ? U : T;
```

The important thing is to be consistent within a codebase and understand the cases where only one option works. Most style debates about `interface` vs `type` are about the 90% where they are interchangeable, and the answer there is: pick one and be consistent.

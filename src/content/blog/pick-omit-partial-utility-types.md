---
title: "Pick, Omit, Partial: 3 utility types that cover 80% of cases."
description: "TypeScript's built-in utility types let you transform existing types without rewriting them. Pick, Omit, and Partial cover most daily needs."
pubDate: 2024-02-15
tags: ["TypeScript"]
draft: false
---

TypeScript ships with a set of built-in utility types that transform existing types. Instead of defining every variation of a type from scratch, you derive what you need from what you already have. Three utility types cover the vast majority of everyday use: `Partial`, `Pick`, and `Omit`.

## The base type

```ts
interface User {
  id: number;
  name: string;
  email: string;
  password: string;
  createdAt: Date;
  updatedAt: Date;
}
```

This is the full user shape. Most places in your code need a subset or a modified version of this.

## Partial: all fields become optional

```ts
type UserUpdate = Partial<User>;
// equivalent to:
// {
//   id?: number;
//   name?: string;
//   email?: string;
//   password?: string;
//   createdAt?: Date;
//   updatedAt?: Date;
// }
```

`Partial<T>` takes every property in `T` and makes it optional. This is exactly what you need for update operations where the caller provides only the fields they want to change.

```ts
async function updateUser(id: number, changes: Partial<User>): Promise<User> {
  return db.update(id, changes);
}

updateUser(1, { name: "Alice" }); // Only updating name — valid
updateUser(1, { name: "Alice", email: "alice@example.com" }); // Updating two fields — valid
updateUser(1, {}); // No changes — also valid
```

Without `Partial`, you would have to define a separate `UserUpdateInput` type with every field marked `?`, and keep it in sync with `User` manually.

## Pick: select specific fields

`Pick<T, K>` creates a type with only the specified keys from `T`:

```ts
type PublicUser = Pick<User, "id" | "name" | "email">;
// {
//   id: number;
//   name: string;
//   email: string;
// }
```

Use `Pick` when you need a subset of an object — a safe version of a type that omits sensitive or irrelevant fields.

```ts
function formatUserDisplay(user: Pick<User, "id" | "name">): string {
  return `[${user.id}] ${user.name}`;
}
```

By typing the parameter as `Pick<User, "id" | "name">`, you communicate that the function only needs those two fields. You can pass a full `User` object and it works, but you can also pass any object with `id` and `name`.

## Omit: exclude specific fields

`Omit<T, K>` is the complement of `Pick`. It creates a type with all fields of `T` except the specified ones:

```ts
type UserWithoutPassword = Omit<User, "password">;
// {
//   id: number;
//   name: string;
//   email: string;
//   createdAt: Date;
//   updatedAt: Date;
// }
```

Use `Omit` when there are more fields to keep than to exclude. Omitting `password` from the `User` type is cleaner than picking the remaining five fields.

```ts
type CreateUserInput = Omit<User, "id" | "createdAt" | "updatedAt">;
// Fields the caller provides — server generates the rest
```

This pattern is common for create operations. The client provides the user data, but the server generates `id`, `createdAt`, and `updatedAt`.

## Combining utility types

Utility types compose:

```ts
// A partial update input that also omits server-managed fields
type UpdateUserInput = Partial<Omit<User, "id" | "createdAt" | "updatedAt">>;
// All of: name, email, password — all optional
```

```ts
// Only the public fields, all optional (for filters/search)
type UserFilter = Partial<Pick<User, "name" | "email">>;
```

## Required: the opposite of Partial

`Required<T>` makes all optional fields required:

```ts
interface Config {
  host?: string;
  port?: number;
  debug?: boolean;
}

type FinalConfig = Required<Config>;
// { host: string; port: number; debug: boolean }
```

Useful when you have a config type with defaults that produces a fully populated object — the output type should be `Required<Config>`.

## Readonly: prevent mutation

`Readonly<T>` makes all fields readonly:

```ts
type ImmutableUser = Readonly<User>;

const user: ImmutableUser = { id: 1, name: "Alice", ... };
user.name = "Bob"; // Error: Cannot assign to 'name' because it is a read-only property
```

## Record: typed key-value maps

`Record<K, V>` creates an object type with keys `K` and values `V`:

```ts
type StatusLabels = Record<"pending" | "active" | "inactive", string>;
// { pending: string; active: string; inactive: string }

const labels: StatusLabels = {
  pending: "Awaiting approval",
  active: "Active",
  inactive: "Deactivated",
};
```

If you add a new status to the key union, TypeScript requires you to add a label for it.

## Why these matter

The core benefit is keeping types in sync automatically. If you add a field to `User`, `Partial<User>`, `Pick<User, ...>`, and `Omit<User, ...>` all update automatically. You define the shape once and derive everything else from it.

Without utility types, you define variations manually and keep them in sync by hand. That is not a TypeScript problem — that is a code maintenance problem that TypeScript solves.

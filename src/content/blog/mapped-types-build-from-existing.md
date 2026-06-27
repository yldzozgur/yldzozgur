---
title: "Mapped types: building a new type from an existing one, automatically."
description: "Mapped types iterate over the keys of a type and transform them. They are the foundation of most TypeScript utility types."
pubDate: 2024-03-14
tags: ["TypeScript"]
draft: false
---

Utility types like `Partial`, `Readonly`, and `Record` are convenient, but they are built from a more primitive feature: mapped types. Understanding mapped types lets you build your own transformations and understand what the built-in utilities actually do.

## The basic syntax

```ts
type Mapped = {
  [K in keyof SourceType]: TransformedType;
};
```

`keyof SourceType` produces a union of the property names of `SourceType`. `[K in ...]` iterates over that union. For each key `K`, you define what the value type should be.

## Rebuilding Partial

```ts
type MyPartial<T> = {
  [K in keyof T]?: T[K];
};
```

For each key `K` in `T`, create an optional (`?`) property with the same value type (`T[K]`). `T[K]` is an indexed access type — it gets the type of property `K` on `T`.

```ts
interface User {
  name: string;
  age: number;
}

type PartialUser = MyPartial<User>;
// { name?: string; age?: number }
```

## Rebuilding Readonly

```ts
type MyReadonly<T> = {
  readonly [K in keyof T]: T[K];
};
```

Add `readonly` modifier to every property. The value types stay the same.

## Rebuilding Record

```ts
type MyRecord<K extends keyof any, V> = {
  [P in K]: V;
};
```

Instead of iterating over an existing type's keys, iterate over a provided key union `K`. All keys get the same value type `V`.

```ts
type Counts = MyRecord<"a" | "b" | "c", number>;
// { a: number; b: number; c: number }
```

## Transforming value types

You are not limited to `T[K]` for values. Apply any transformation:

```ts
// Wrap all values in Promise
type Promisified<T> = {
  [K in keyof T]: Promise<T[K]>;
};

// Wrap all values in arrays
type Arrayified<T> = {
  [K in keyof T]: T[K][];
};

interface Config {
  host: string;
  port: number;
}

type AsyncConfig = Promisified<Config>;
// { host: Promise<string>; port: Promise<number> }
```

## Filtering keys with conditional types

Combine mapped types with conditional types to filter keys:

```ts
// Keep only keys whose values are strings
type StringKeys<T> = {
  [K in keyof T]: T[K] extends string ? K : never;
}[keyof T];

interface Mixed {
  name: string;
  age: number;
  email: string;
  active: boolean;
}

type StringFields = StringKeys<Mixed>;
// "name" | "email"
```

The `[keyof T]` at the end indexes into the mapped type to get all value types, which are either the key name or `never`. Unions with `never` collapse, leaving only the real key names.

## Key remapping with as

TypeScript 4.1 added key remapping, letting you change the key names as well as the values:

```ts
// Prefix all keys with "get"
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

interface User {
  name: string;
  age: number;
}

type UserGetters = Getters<User>;
// { getName: () => string; getAge: () => number }
```

`as` followed by a template literal type renames each key. `Capitalize<string & K>` capitalizes the key name (the `string &` is needed because `K` is `string | number | symbol`, not just `string`).

## Removing optional modifier

Use `-?` to remove optionality:

```ts
type Required<T> = {
  [K in keyof T]-?: T[K];
};
```

The `-` prefix on `?` removes the modifier. Similarly, `-readonly` removes readonly:

```ts
type Mutable<T> = {
  -readonly [K in keyof T]: T[K];
};

type MutableUser = Mutable<Readonly<User>>;
// User properties are writable again
```

## A real example: form state

```ts
interface FormValues {
  name: string;
  email: string;
  age: number;
}

// All values as strings (form inputs are strings)
type FormInputs = {
  [K in keyof FormValues]: string;
};

// Track which fields have been touched
type FormTouched = {
  [K in keyof FormValues]: boolean;
};

// Track validation errors
type FormErrors = {
  [K in keyof FormValues]?: string;
};
```

All three types derive their keys from `FormValues`. When you add a field to `FormValues`, all three types automatically include it.

Mapped types turn type definitions from static declarations into derived transformations. Instead of maintaining five related types by hand, you maintain one source of truth and derive the rest.

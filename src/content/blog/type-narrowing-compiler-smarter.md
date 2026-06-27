---
title: "Type narrowing: how the compiler gets smarter as your code runs."
description: "TypeScript tracks which types are possible at each point in your code. Understanding narrowing lets you write more precise types and fewer casts."
pubDate: 2024-02-22
tags: ["TypeScript"]
draft: false
---

TypeScript does not just check types at function boundaries. It tracks what is possible at every point inside your code. When you write an if statement, TypeScript knows that one branch can only be reached with certain types. This is narrowing.

## The basic case

```ts
function format(value: string | number): string {
  // Here, TypeScript knows: value is string | number
  if (typeof value === "string") {
    // Here, TypeScript knows: value is string
    return value.toUpperCase();
  }
  // Here, TypeScript knows: value is number (string is eliminated)
  return value.toFixed(2);
}
```

After the `typeof` check, TypeScript eliminates `number` from the possible types inside the if block. After the block exits, `string` is eliminated because the only way to reach that point is if `typeof value === "string"` was false.

## Narrowing with typeof

`typeof` narrows to primitive types:

```ts
function process(x: string | number | boolean | null) {
  if (typeof x === "string") { /* x: string */ }
  if (typeof x === "number") { /* x: number */ }
  if (typeof x === "boolean") { /* x: boolean */ }
  // typeof null === "object" — typeof doesn't narrow null directly
}
```

## Narrowing with truthiness

```ts
function greet(name: string | null) {
  if (name) {
    // name is string (null is falsy and eliminated)
    return `Hello, ${name}`;
  }
  return "Hello, stranger";
}
```

Truthiness narrows away `null`, `undefined`, `0`, `""`, `false`, and `NaN`. Be careful: if `""` is a valid value you want to preserve, use `!= null` instead of a truthy check.

## Narrowing with instanceof

```ts
function handleError(err: unknown) {
  if (err instanceof Error) {
    // err is Error
    console.error(err.message);
  } else {
    console.error(String(err));
  }
}
```

`instanceof` narrowing works with class instances.

## Narrowing with in

```ts
type Dog = { kind: "dog"; bark(): void };
type Cat = { kind: "cat"; meow(): void };
type Animal = Dog | Cat;

function makeNoise(animal: Animal) {
  if ("bark" in animal) {
    animal.bark(); // animal is Dog
  } else {
    animal.meow(); // animal is Cat
  }
}
```

`in` checks whether a property exists on an object. TypeScript narrows to the union members that could have that property.

## Discriminated union narrowing

The most reliable narrowing uses a discriminant field:

```ts
type Result =
  | { status: "success"; data: string }
  | { status: "error"; message: string };

function handle(result: Result) {
  switch (result.status) {
    case "success":
      console.log(result.data); // result is { status: "success"; data: string }
      break;
    case "error":
      console.error(result.message); // result is { status: "error"; message: string }
      break;
  }
}
```

TypeScript narrows the entire object type based on the value of the discriminant field.

## Type guards

You can define custom narrowing functions with type predicates:

```ts
function isString(value: unknown): value is string {
  return typeof value === "string";
}

function process(value: unknown) {
  if (isString(value)) {
    // value is string
    value.toUpperCase();
  }
}
```

The `value is string` return type is a type predicate. When the function returns `true`, TypeScript narrows the argument to `string` at the call site.

A more complex guard:

```ts
interface User {
  id: number;
  name: string;
  email: string;
}

function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "name" in value &&
    "email" in value
  );
}

const raw: unknown = JSON.parse(response);
if (isUser(raw)) {
  raw.name; // TypeScript knows this is a User
}
```

## Assertion functions

An assertion function narrows unconditionally and throws if the assertion fails:

```ts
function assertIsString(value: unknown): asserts value is string {
  if (typeof value !== "string") {
    throw new TypeError(`Expected string, got ${typeof value}`);
  }
}

function process(value: unknown) {
  assertIsString(value);
  // From here on, value is string
  value.toUpperCase();
}
```

After calling an assertion function, TypeScript assumes the assertion holds. If it throws, the code after it is unreachable anyway.

## Narrowing null and undefined

```ts
function getLength(str: string | null | undefined): number {
  if (str == null) {
    // str is null | undefined (loose equality catches both)
    return 0;
  }
  // str is string
  return str.length;
}
```

`== null` is a rare case where loose equality is actually useful: it catches both `null` and `undefined` in one check.

## The control flow model

TypeScript builds a control flow graph of your function. Each branch, loop, and return narrows the set of possible types. After an if block that returns, TypeScript knows the remaining code executes only when the condition was false.

This is why early returns narrow cleanly:

```ts
function formatName(name: string | null): string {
  if (!name) return "Anonymous";
  // TypeScript knows name is string from here
  return name.charAt(0).toUpperCase() + name.slice(1);
}
```

Narrowing is one of the features that makes TypeScript productive rather than just correct. Once you internalize it, you write fewer type casts and let the compiler track types through your logic.

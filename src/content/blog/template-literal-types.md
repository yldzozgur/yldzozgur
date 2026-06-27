---
title: "Template literal types: string manipulation before your code runs."
description: "Template literal types let TypeScript reason about string values at the type level. They enable precise typing of string unions and event names."
pubDate: 2024-03-18
tags: ["TypeScript"]
draft: false
---

TypeScript 4.1 added template literal types, which let you construct new string types by combining existing string types using template syntax. They run at the type level — before your code executes.

## Basic syntax

```ts
type Greeting = `Hello, ${string}`;

const a: Greeting = "Hello, world"; // OK
const b: Greeting = "Hello, Alice"; // OK
const c: Greeting = "Hi there"; // Error: does not match pattern
```

Inside backticks, `${...}` can be any type. When it is a string literal union, the result is the cross-product of all combinations.

## String literal unions

```ts
type Color = "red" | "blue" | "green";
type Size = "sm" | "md" | "lg";

type ClassVariant = `${Color}-${Size}`;
// "red-sm" | "red-md" | "red-lg" | "blue-sm" | "blue-md" | "blue-lg" | "green-sm" | "green-md" | "green-lg"
```

TypeScript expands the union automatically. Every combination is a valid type.

## Event names

A common use case is typed event systems:

```ts
type Entity = "user" | "post" | "comment";
type Action = "created" | "updated" | "deleted";

type AppEvent = `${Entity}:${Action}`;
// "user:created" | "user:updated" | "user:deleted" |
// "post:created" | ... | "comment:deleted"

function on(event: AppEvent, handler: () => void) { ... }

on("user:created", () => {}); // OK
on("user:banned", () => {}); // Error: not a valid AppEvent
```

## Intrinsic string manipulation types

TypeScript ships with built-in types for common string operations:

```ts
type Upper = Uppercase<"hello">; // "HELLO"
type Lower = Lowercase<"HELLO">; // "hello"
type Cap = Capitalize<"hello">; // "Hello"
type Uncap = Uncapitalize<"Hello">; // "hello"
```

These work with unions too:

```ts
type Events = "click" | "focus" | "blur";
type HandlerNames = `on${Capitalize<Events>}`;
// "onClick" | "onFocus" | "onBlur"
```

## Extracting substrings with infer

Combine template literals with conditional types and `infer` to extract parts of strings:

```ts
type ExtractRouteParams<T extends string> =
  T extends `${infer _Start}:${infer Param}/${infer Rest}`
    ? Param | ExtractRouteParams<`/${Rest}`>
    : T extends `${infer _Start}:${infer Param}`
    ? Param
    : never;

type Params = ExtractRouteParams<"/users/:userId/posts/:postId">;
// "userId" | "postId"
```

This recursively extracts all `:param` segments from a route string at the type level.

## Typed CSS class builder

```ts
type SpacingSize = 0 | 1 | 2 | 4 | 8 | 16;
type SpacingProp = "p" | "px" | "py" | "m" | "mx" | "my";

type SpacingClass = `${SpacingProp}-${SpacingSize}`;
// "p-0" | "p-1" | "p-2" | ... | "my-16"

function cn(...classes: (SpacingClass | string)[]): string {
  return classes.join(" ");
}
```

## API endpoint typing

```ts
type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";
type ApiVersion = "v1" | "v2";

type Endpoint = `/${ApiVersion}/${string}`;

interface RouteConfig {
  method: HttpMethod;
  path: Endpoint;
  handler: (req: Request, res: Response) => void;
}

const routes: RouteConfig[] = [
  { method: "GET", path: "/v1/users", handler: listUsers },
  { method: "POST", path: "/v2/users", handler: createUser },
  { method: "GET", path: "/users", handler: listUsers }, // Error: missing version prefix
];
```

## Mapped types with template literals

Key remapping in mapped types uses template literal syntax:

```ts
type Setters<T> = {
  [K in keyof T as `set${Capitalize<string & K>}`]: (value: T[K]) => void;
};

interface State {
  count: number;
  name: string;
}

type StateSetters = Setters<State>;
// { setCount: (value: number) => void; setName: (value: string) => void }
```

## Discriminated union from strings

```ts
type PropEventSource<T> = {
  on<K extends string & keyof T>(
    eventName: `${K}Changed`,
    callback: (newValue: T[K]) => void
  ): void;
};

declare function makeWatchedObject<T>(obj: T): T & PropEventSource<T>;

const user = makeWatchedObject({ name: "Alice", age: 30 });

user.on("nameChanged", (newName) => {
  // newName is string — TypeScript inferred T[K] where K = "name"
  console.log(newName.toUpperCase());
});

user.on("ageChanged", (newAge) => {
  // newAge is number
  console.log(newAge.toFixed(0));
});

user.on("roleChanged", handler); // Error: "roleChanged" is not a valid event
```

Template literal types move string manipulation from runtime to compile time. When the set of valid strings is finite and derivable, TypeScript can check it. Typos become compile errors instead of runtime bugs.

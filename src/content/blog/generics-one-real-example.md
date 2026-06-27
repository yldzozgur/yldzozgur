---
title: "Generics without the abstract nonsense. One real example."
description: "Generics let functions and types work with any type while preserving type information. One practical example makes them concrete."
pubDate: 2024-02-08
tags: ["TypeScript"]
draft: false
---

Most explanations of generics start with containers — a `Box<T>` or a `Stack<T>`. These examples are pedagogically correct but too abstract. Let's start with a problem that actually appears in real code.

## The problem without generics

You have a function that fetches data from an API and returns it:

```ts
async function fetchData(url: string): Promise<any> {
  const res = await fetch(url);
  return res.json();
}

const user = await fetchData("/api/user/1");
user.name; // TypeScript thinks user is 'any' — no type information
```

Using `any` loses all type safety after the call. TypeScript cannot help you if you access `user.naem` (typo). The whole point of TypeScript is gone.

You could overload the function for each return type:

```ts
async function fetchUser(url: string): Promise<User> { ... }
async function fetchPost(url: string): Promise<Post> { ... }
```

But now you have duplicate logic. Every change to the fetch logic must be made in every overload.

## Generics solve this

```ts
async function fetchData<T>(url: string): Promise<T> {
  const res = await fetch(url);
  return res.json() as T;
}

const user = await fetchData<User>("/api/user/1");
user.name; // TypeScript knows this is a User — full type information
user.naem; // Error: Property 'naem' does not exist on type 'User'
```

`T` is a type parameter. When you call `fetchData<User>`, you are telling TypeScript "use `User` as the type for `T` throughout this call." The function stays generic, but each call site has full type information.

## Generic functions: the syntax

```ts
function identity<T>(value: T): T {
  return value;
}

identity<string>("hello"); // returns string
identity<number>(42); // returns number
```

The `<T>` after the function name declares the type parameter. `T` is a placeholder that TypeScript fills in at each call site.

TypeScript can usually infer the type parameter from the arguments, so you often don't need to write it explicitly:

```ts
identity("hello"); // TypeScript infers T = string
identity(42); // TypeScript infers T = number
```

## A real-world example: a typed wrapper

Here is a generic that appears in almost every project — a typed wrapper for `localStorage`:

```ts
function getStorageItem<T>(key: string): T | null {
  const raw = localStorage.getItem(key);
  if (raw === null) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function setStorageItem<T>(key: string, value: T): void {
  localStorage.setItem(key, JSON.stringify(value));
}

// Usage
setStorageItem<UserPreferences>("prefs", { theme: "dark", lang: "en" });
const prefs = getStorageItem<UserPreferences>("prefs");
// prefs is UserPreferences | null — TypeScript knows the shape
```

Without generics this would either use `any` (unsafe) or require a separate function for each type stored.

## Generic constraints

Sometimes you need `T` to have certain properties. Use `extends` to constrain:

```ts
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

const user = { name: "Alice", age: 30 };
getProperty(user, "name"); // string
getProperty(user, "age"); // number
getProperty(user, "email"); // Error: "email" doesn't exist on this object
```

`K extends keyof T` means "K must be one of the keys of T." TypeScript also knows the return type is `T[K]` — the type of the value at that key. If you access `name`, the return type is `string`. If you access `age`, it is `number`.

## Generic interfaces and types

```ts
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
};

async function getUsers(): Promise<ApiResponse<PaginatedResponse<User>>> {
  const res = await fetch("/api/users");
  return res.json();
}

const response = await getUsers();
response.data.items[0].name; // TypeScript knows this is a User
```

The type composition is explicit. At any level of nesting, TypeScript knows what type to expect.

## Default type parameters

```ts
interface Container<T = string> {
  value: T;
  label: string;
}

const c1: Container = { value: "hello", label: "text" }; // T defaults to string
const c2: Container<number> = { value: 42, label: "count" };
```

Default type parameters let consumers omit the type parameter when the default is appropriate.

The pattern to internalize: generics preserve type information through transformations. Without them, information is lost at function boundaries. With them, TypeScript can track types through the full call chain.

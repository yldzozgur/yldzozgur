---
title: "TypeScript strict mode turns on 7 flags. Here's what each one catches."
description: "strict: true in tsconfig is not one setting. It enables 7 independent checks. Understanding each one helps you know what you're getting."
pubDate: 2024-02-29
tags: ["TypeScript"]
draft: false
---

`"strict": true` in your `tsconfig.json` is a shorthand. It enables seven separate compiler flags. Knowing what each one does helps you understand the errors you see and decide what to turn on in a migration.

## The seven flags

The flags enabled by `strict: true`:

1. `strictNullChecks`
2. `noImplicitAny`
3. `strictFunctionTypes`
4. `strictBindCallApply`
5. `strictPropertyInitialization`
6. `noImplicitThis`
7. `useUnknownInCatchVariables`

Let's look at each.

## 1. strictNullChecks

Without this, `null` and `undefined` are assignable to every type:

```ts
// Without strictNullChecks
let name: string = null; // allowed
name.toUpperCase(); // runtime error

// With strictNullChecks
let name: string = null; // Error: Type 'null' is not assignable to type 'string'
let maybeName: string | null = null; // OK — explicitly allows null
```

This is the most impactful flag. It forces you to handle null and undefined explicitly and eliminates a large class of "cannot read property of null" runtime errors.

## 2. noImplicitAny

Without this, TypeScript infers `any` when it cannot determine the type:

```ts
// Without noImplicitAny
function process(data) { // data is implicitly 'any'
  data.something(); // no error
}

// With noImplicitAny
function process(data) { // Error: Parameter 'data' implicitly has an 'any' type
}
function process(data: unknown) { // OK — explicit
}
```

This forces you to annotate parameters where TypeScript cannot infer the type. It prevents `any` from silently spreading through your codebase.

## 3. strictFunctionTypes

This enables stricter checking of function parameter types using contravariance:

```ts
type StringHandler = (s: string) => void;
type Handler = (s: string | number) => void;

// Without strictFunctionTypes: this compiles
const h: StringHandler = (s: string | number) => console.log(s);

// With strictFunctionTypes: Error
// A handler that accepts string | number is not a valid StringHandler
// because callers of StringHandler will only pass strings,
// but the handler advertises it accepts numbers too
```

This catches subtle function type compatibility bugs, particularly in callback-heavy code.

## 4. strictBindCallApply

Checks that `bind`, `call`, and `apply` are called with the correct argument types:

```ts
function add(a: number, b: number): number {
  return a + b;
}

// Without strictBindCallApply: no error
add.call(null, "hello", "world"); // runtime error — wrong types

// With strictBindCallApply: Error
// Argument of type 'string' is not assignable to parameter of type 'number'
```

Previously `bind`, `call`, and `apply` returned `any`, which bypassed type checking entirely.

## 5. strictPropertyInitialization

Requires that class properties are initialized in the constructor:

```ts
class User {
  name: string; // Error: Property 'name' has no initializer and is not definitely assigned in the constructor

  // Fix 1: initialize in constructor
  constructor(name: string) {
    this.name = name;
  }
}

class Config {
  // Fix 2: use definite assignment assertion if you know it will be initialized elsewhere
  name!: string;
}
```

This catches a common pattern where class properties are used before initialization.

## 6. noImplicitThis

Flags `this` when its type cannot be determined:

```ts
const counter = {
  count: 0,
  increment: function() {
    this.count++; // Without noImplicitThis: this is 'any'
  }
};

// With noImplicitThis, you may need to annotate 'this':
function increment(this: { count: number }) {
  this.count++;
}
```

This mostly surfaces in standalone functions used as callbacks where `this` binding is unclear.

## 7. useUnknownInCatchVariables (TypeScript 4.4+)

Before TypeScript 4.0, catch variables were always typed as `any`. With this flag, they become `unknown`:

```ts
try {
  doSomething();
} catch (err) {
  // Without flag: err is 'any' — you can call anything on it
  // With flag: err is 'unknown' — must narrow before use

  if (err instanceof Error) {
    console.error(err.message); // OK
  } else {
    console.error(String(err));
  }
}
```

This is the correct behavior. Thrown values can be anything — not every throw is an Error object.

## Turning on strict incrementally

If you're adding TypeScript to an existing JavaScript project, turning on all strict flags at once can produce thousands of errors. You can enable them one at a time:

```json
{
  "compilerOptions": {
    "strictNullChecks": true,
    "noImplicitAny": true
  }
}
```

Start with `noImplicitAny` and `strictNullChecks`. These two catch the most bugs. Add the others as you work through the codebase.

There is also `// @ts-nocheck` for files you want to exclude temporarily, and `// @ts-ignore` for specific lines. Use these as stepping stones, not permanent solutions.

The goal of strict mode is not to make TypeScript harder to use. It is to make the type information accurate enough that TypeScript can actually catch bugs instead of just providing autocomplete.
